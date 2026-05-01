"""Functional tests for cache module — verifies TTL, tier routing, invalidation, key building.

Tests cover:
- Path classification (reference vs operational)
- Cache key construction with user identity isolation
- In-memory cache: get/set/TTL expiry/eviction
- Invalidation: specific path, full flush
- Redis backend behavior (mocked)
- User ID extraction from JWT/Basic/absent auth
"""
import json
import time
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from freshservice_mcp import cache

MOD = "freshservice_mcp.cache"


# ═══════════════════════════════════════════════════════════════════════════
# Path classification
# ═══════════════════════════════════════════════════════════════════════════


class TestPathClassification:
    """_is_reference_path determines cache tier and TTL."""

    @pytest.mark.parametrize("path", [
        "agents", "groups", "departments", "locations",
        "ticket_form_fields", "change_form_fields",
        "agent_fields", "requester_fields", "roles", "products", "vendors",
    ])
    def test_reference_paths(self, path):
        assert cache._is_reference_path(path) is True

    @pytest.mark.parametrize("path", [
        "catalog/items/123", "solutions/categories/5",
    ])
    def test_reference_prefixes(self, path):
        assert cache._is_reference_path(path) is True

    @pytest.mark.parametrize("path", [
        "tickets", "tickets/42", "changes", "assets/5/components",
        "problems/10", "releases",
    ])
    def test_operational_paths(self, path):
        assert cache._is_reference_path(path) is False

    def test_ttl_reference(self):
        assert cache._ttl_for("agents") == cache.TTL_REFERENCE

    def test_ttl_operational(self):
        assert cache._ttl_for("tickets") == cache.TTL_OPERATIONAL


# ═══════════════════════════════════════════════════════════════════════════
# User ID extraction
# ═══════════════════════════════════════════════════════════════════════════


class TestUserIdExtraction:
    """_user_id extracts identity from forwarded auth header for cache isolation."""

    def test_no_auth_returns_apikey(self):
        with patch(f"{MOD}.forwarded_token_var") as mock_var:
            mock_var.get.return_value = None
            assert cache._user_id() == "apikey"

    def test_basic_auth_hashed(self):
        with patch(f"{MOD}.forwarded_token_var") as mock_var:
            mock_var.get.return_value = "Basic dXNlcjpwYXNz"
            uid = cache._user_id()
            assert uid.startswith("basic_")
            assert len(uid) > 10  # hash truncated to 16 chars

    def test_bearer_jwt_extracts_oid(self):
        """Should extract Azure AD 'oid' claim from JWT."""
        import base64
        payload = {"oid": "abc-123", "email": "user@test.com"}
        payload_b64 = base64.urlsafe_b64encode(
            json.dumps(payload).encode()
        ).rstrip(b"=").decode()
        token = f"header.{payload_b64}.signature"
        with patch(f"{MOD}.forwarded_token_var") as mock_var:
            mock_var.get.return_value = f"Bearer {token}"
            assert cache._user_id() == "abc-123"

    def test_bearer_jwt_falls_back_to_sub(self):
        import base64
        payload = {"sub": "user-sub-id"}
        payload_b64 = base64.urlsafe_b64encode(
            json.dumps(payload).encode()
        ).rstrip(b"=").decode()
        token = f"h.{payload_b64}.s"
        with patch(f"{MOD}.forwarded_token_var") as mock_var:
            mock_var.get.return_value = f"Bearer {token}"
            assert cache._user_id() == "user-sub-id"

    def test_opaque_token_hashed(self):
        """Non-JWT token should be hashed for uniqueness."""
        with patch(f"{MOD}.forwarded_token_var") as mock_var:
            mock_var.get.return_value = "Bearer opaque-token-no-dots"
            uid = cache._user_id()
            # Opaque token can't be split into JWT parts → hash
            assert len(uid) == 16


# ═══════════════════════════════════════════════════════════════════════════
# Cache key construction
# ═══════════════════════════════════════════════════════════════════════════


class TestCacheKey:
    """Verify keys include correct prefix and user isolation."""

    def test_reference_key_no_user(self):
        """Reference keys should NOT include user identity."""
        key = cache._cache_key("agents", {"page": 1})
        assert key.startswith("fs:ref:agents:")
        assert "op:" not in key

    def test_operational_key_includes_user(self):
        """Operational keys must be scoped to the current user."""
        with patch(f"{MOD}.forwarded_token_var") as mock_var:
            mock_var.get.return_value = None  # → "apikey"
            key = cache._cache_key("tickets", {"page": 1})
            assert key.startswith("fs:op:apikey:tickets:")

    def test_different_params_different_keys(self):
        key1 = cache._cache_key("agents", {"page": 1})
        key2 = cache._cache_key("agents", {"page": 2})
        assert key1 != key2

    def test_same_params_same_key(self):
        key1 = cache._cache_key("agents", {"page": 1, "per_page": 30})
        key2 = cache._cache_key("agents", {"per_page": 30, "page": 1})
        # sort_keys=True ensures stable ordering
        assert key1 == key2


# ═══════════════════════════════════════════════════════════════════════════
# In-memory cache backend
# ═══════════════════════════════════════════════════════════════════════════


class TestMemoryCache:
    """Verify TTL expiry, eviction on max entries."""

    def setup_method(self):
        cache._mem_cache.clear()

    def test_set_and_get(self):
        cache._mem_set("k1", '{"x":1}', ttl=60)
        assert cache._mem_get("k1") == '{"x":1}'

    def test_expired_entry_returns_none(self):
        cache._mem_set("k2", "val", ttl=1)
        # Simulate time passing
        cache._mem_cache["k2"] = (time.time() - 1, "val")
        assert cache._mem_get("k2") is None
        # Entry is cleaned up
        assert "k2" not in cache._mem_cache

    def test_eviction_at_max_entries(self):
        """When at capacity, oldest entry should be evicted."""
        original_max = cache._MEM_MAX_ENTRIES
        try:
            cache._MEM_MAX_ENTRIES = 3
            cache._mem_set("a", "1", ttl=100)
            cache._mem_set("b", "2", ttl=200)
            cache._mem_set("c", "3", ttl=300)
            # At capacity — next set should evict earliest-expiring
            cache._mem_set("d", "4", ttl=400)
            assert len(cache._mem_cache) == 3
            assert cache._mem_get("d") == "4"
        finally:
            cache._MEM_MAX_ENTRIES = original_max

    def test_invalidate_specific(self):
        with patch(f"{MOD}._cache_key", return_value="test_key"):
            cache._mem_cache["test_key"] = (time.time() + 60, "val")
            removed = cache._mem_invalidate("some_path")
            assert removed == 1
            assert "test_key" not in cache._mem_cache

    def test_invalidate_all(self):
        cache._mem_set("x", "1", 60)
        cache._mem_set("y", "2", 60)
        removed = cache._mem_invalidate(None)
        assert removed == 2
        assert len(cache._mem_cache) == 0


# ═══════════════════════════════════════════════════════════════════════════
# Public API (cache_get / cache_set / cache_invalidate)
# ═══════════════════════════════════════════════════════════════════════════


class TestCachePublicAPI:
    """Verify the async public interface delegates to correct backend."""

    def setup_method(self):
        cache._mem_cache.clear()

    @pytest.mark.asyncio
    async def test_cache_set_and_get_memory(self):
        """Without Redis, should use in-memory backend."""
        with patch(f"{MOD}.REDIS_URL", ""):
            await cache.cache_set("agents", '{"agents":[]}', params={"page": 1})
            result = await cache.cache_get("agents", params={"page": 1})
            assert result == '{"agents":[]}'

    @pytest.mark.asyncio
    async def test_cache_get_miss(self):
        with patch(f"{MOD}.REDIS_URL", ""):
            result = await cache.cache_get("tickets", params={"page": 99})
            assert result is None

    @pytest.mark.asyncio
    async def test_cache_invalidate_flushes_all(self):
        with patch(f"{MOD}.REDIS_URL", ""):
            await cache.cache_set("agents", "data1")
            await cache.cache_set("tickets", "data2")
            removed = await cache.cache_invalidate(None)
            assert removed >= 2

    @pytest.mark.asyncio
    async def test_redis_backend_used_when_configured(self):
        """When REDIS_URL is set, should call Redis get/set."""
        with patch(f"{MOD}.REDIS_URL", "redis://localhost:6379"), \
             patch(f"{MOD}._redis_get", new_callable=AsyncMock) as rget, \
             patch(f"{MOD}._redis_set", new_callable=AsyncMock) as rset:
            rget.return_value = None
            await cache.cache_get("agents")
            rget.assert_called_once()

            await cache.cache_set("agents", "data")
            rset.assert_called_once()

    @pytest.mark.asyncio
    async def test_redis_invalidate_scans(self):
        """Full invalidate should scan for fs:* keys."""
        with patch(f"{MOD}.REDIS_URL", "redis://localhost:6379"), \
             patch(f"{MOD}._redis_invalidate", new_callable=AsyncMock) as rinv:
            rinv.return_value = 5
            count = await cache.cache_invalidate(None)
            assert count == 5
            rinv.assert_called_once_with(None)
