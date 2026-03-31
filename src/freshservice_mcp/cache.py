"""Freshservice MCP — Tiered read cache (Redis + in-memory fallback).

Cache tiers:
  - **Reference** (shared): agents, departments, groups, locations,
    categories, form fields — identical for all users, long TTL.
  - **Operational** (per-user): tickets, changes, assets, problems —
    keyed by user identity, short TTL.
  - **Write**: POST/PUT/DELETE — never cached.

Configuration (env vars):
  REDIS_URL          — Redis connection string (e.g. redis://:pass@host:6379/0).
                       When unset, falls back to in-memory TTL cache.
  CACHE_TTL_REFERENCE  — TTL for reference data in seconds (default: 43200 = 12h).
  CACHE_TTL_OPERATIONAL — TTL for operational data in seconds (default: 300 = 5min).
"""

import hashlib
import json
import logging
import os
import time
from typing import Any, Optional

from .auth import forwarded_token_var
from .telemetry import CACHE_OPS, CACHE_ENTRIES, REDIS_CONNECTED

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
_REDIS_URL_RAW: str = os.getenv("REDIS_URL", "")
_REDIS_PASSWORD: str = os.getenv("REDIS_PASSWORD", "")
TTL_REFERENCE: int = int(os.getenv("CACHE_TTL_REFERENCE", "43200"))
TTL_OPERATIONAL: int = int(os.getenv("CACHE_TTL_OPERATIONAL", "300"))


def _build_redis_url() -> str:
    """Merge REDIS_PASSWORD into REDIS_URL if both are set."""
    url = _REDIS_URL_RAW
    if not url or not _REDIS_PASSWORD:
        return url
    from urllib.parse import quote_plus, urlparse, urlunparse
    parsed = urlparse(url)
    if not parsed.password:
        netloc = f":{quote_plus(_REDIS_PASSWORD)}@{parsed.hostname}"
        if parsed.port:
            netloc += f":{parsed.port}"
        return urlunparse(parsed._replace(netloc=netloc))
    return url


REDIS_URL: str = _build_redis_url()

# ---------------------------------------------------------------------------
# Path classification
# ---------------------------------------------------------------------------
# API paths that return reference data (shared across all users).
_REFERENCE_PATHS: set[str] = {
    "agents",
    "groups",
    "departments",
    "locations",
    "ticket_form_fields",
    "change_form_fields",
    "agent_fields",
    "requester_fields",
    "roles",
    "products",
    "vendors",
    "software",
}

# Prefixes that indicate reference sub-resources.
_REFERENCE_PREFIXES: tuple[str, ...] = (
    "catalog/",
    "solutions/categories",
)


def _is_reference_path(path: str) -> bool:
    """Return True if *path* targets reference/shared data."""
    normalized = path.strip("/")
    if normalized in _REFERENCE_PATHS:
        return True
    return any(normalized.startswith(p) for p in _REFERENCE_PREFIXES)


def _user_id() -> str:
    """Extract a stable user identifier from the forwarded OAuth token.

    Falls back to ``"apikey"`` when no per-user token is present (local
    dev / API-key mode).
    """
    import base64
    token = forwarded_token_var.get()
    if not token:
        return "apikey"
    try:
        payload_b64 = token.split(".")[1]
        padding = 4 - len(payload_b64) % 4
        if padding != 4:
            payload_b64 += "=" * padding
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        return (
            payload.get("oid")  # Azure AD object ID (stable)
            or payload.get("sub")
            or payload.get("email")
            or payload.get("preferred_username")
            or "unknown"
        )
    except Exception:
        # Token is opaque or malformed — hash it for uniqueness.
        return hashlib.sha256(token.encode()).hexdigest()[:16]


def _cache_key(path: str, params: Optional[dict] = None) -> str:
    """Build the cache key for a GET request."""
    args_hash = hashlib.sha256(
        json.dumps(params or {}, sort_keys=True).encode()
    ).hexdigest()[:16]

    if _is_reference_path(path):
        return f"fs:ref:{path}:{args_hash}"
    return f"fs:op:{_user_id()}:{path}:{args_hash}"


def _ttl_for(path: str) -> int:
    """Return the TTL in seconds based on path classification."""
    return TTL_REFERENCE if _is_reference_path(path) else TTL_OPERATIONAL


# ═══════════════════════════════════════════════════════════════════════════
# Backend: Redis
# ═══════════════════════════════════════════════════════════════════════════
_redis_client = None  # lazily initialised


async def _get_redis():
    """Return a shared ``redis.asyncio.Redis`` client (lazy init)."""
    global _redis_client
    if _redis_client is None:
        import redis.asyncio as aioredis
        _redis_client = aioredis.from_url(
            REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=2,
        )
    return _redis_client


async def _redis_get(key: str) -> Optional[str]:
    try:
        client = await _get_redis()
        val = await client.get(key)
        REDIS_CONNECTED.set(1)
        return val
    except Exception as exc:
        log.warning("Redis GET failed (key=%s): %s", key, exc)
        REDIS_CONNECTED.set(0)
        CACHE_OPS.labels(operation="error", tier="redis").inc()
        return None


async def _redis_set(key: str, value: str, ttl: int) -> None:
    try:
        client = await _get_redis()
        await client.set(key, value, ex=ttl)
        REDIS_CONNECTED.set(1)
    except Exception as exc:
        log.warning("Redis SET failed (key=%s): %s", key, exc)
        REDIS_CONNECTED.set(0)
        CACHE_OPS.labels(operation="error", tier="redis").inc()


# ═══════════════════════════════════════════════════════════════════════════
# Backend: In-memory (fallback when Redis is not configured)
# ═══════════════════════════════════════════════════════════════════════════
_mem_cache: dict[str, tuple[float, str]] = {}
_MEM_MAX_ENTRIES = 2048


def _mem_get(key: str) -> Optional[str]:
    entry = _mem_cache.get(key)
    if entry is None:
        return None
    expires_at, value = entry
    if time.time() > expires_at:
        _mem_cache.pop(key, None)
        return None
    return value


def _mem_set(key: str, value: str, ttl: int) -> None:
    # Evict oldest if at capacity.
    if len(_mem_cache) >= _MEM_MAX_ENTRIES:
        oldest_key = min(_mem_cache, key=lambda k: _mem_cache[k][0])
        _mem_cache.pop(oldest_key, None)
    _mem_cache[key] = (time.time() + ttl, value)


# ═══════════════════════════════════════════════════════════════════════════
# Public API
# ═══════════════════════════════════════════════════════════════════════════
async def cache_get(path: str, params: Optional[dict] = None) -> Optional[str]:
    """Return cached response body (JSON string) or None."""
    key = _cache_key(path, params)
    tier = "reference" if _is_reference_path(path) else "operational"
    if REDIS_URL:
        val = await _redis_get(key)
    else:
        val = _mem_get(key)
    if val is not None:
        CACHE_OPS.labels(operation="hit", tier=tier).inc()
    else:
        CACHE_OPS.labels(operation="miss", tier=tier).inc()
    return val


async def cache_set(path: str, body: str, params: Optional[dict] = None) -> None:
    """Store response body in cache with the appropriate TTL."""
    key = _cache_key(path, params)
    ttl = _ttl_for(path)
    tier = "reference" if _is_reference_path(path) else "operational"
    if REDIS_URL:
        await _redis_set(key, body, ttl)
    else:
        _mem_set(key, body, ttl)
        CACHE_ENTRIES.set(len(_mem_cache))
    CACHE_OPS.labels(operation="set", tier=tier).inc()


async def cache_invalidate(path: Optional[str] = None) -> int:
    """Invalidate cache entries.

    If *path* is given, remove that specific key (with no params).
    If ``None``, flush all ``fs:*`` keys.
    Returns the number of keys removed.
    """
    if REDIS_URL:
        try:
            client = await _get_redis()
            if path is None:
                keys = []
                async for key in client.scan_iter(match="fs:*", count=500):
                    keys.append(key)
                if keys:
                    return await client.delete(*keys)
                return 0
            else:
                return await client.delete(_cache_key(path))
        except Exception as exc:
            log.warning("Redis invalidate failed: %s", exc)
            return 0
    else:
        if path is None:
            count = len(_mem_cache)
            _mem_cache.clear()
            return count
        key = _cache_key(path)
        return 1 if _mem_cache.pop(key, None) is not None else 0
