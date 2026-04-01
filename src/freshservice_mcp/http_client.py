"""Freshservice MCP — Shared HTTP client utilities."""
import re
import base64
import json
import time
import httpx
from typing import Optional, Dict, Any

from .auth import forwarded_token_var
from .cache import cache_get, cache_set
from .config import FRESHSERVICE_DOMAIN, FRESHSERVICE_APIKEY
from .telemetry import API_REQUESTS, API_DURATION, _path_root, trace_span


def _auth_header() -> str:
    """Return the Authorization header value.

    Uses the per-user Bearer token forwarded by the MCP gateway when
    available (HTTP transports behind ContextForge).  Falls back to
    Basic Auth with the API key (stdio / local dev).
    """
    token = forwarded_token_var.get()
    if token:
        return f"Bearer {token}"
    return _apikey_auth_header()


def _apikey_auth_header() -> str:
    """Return Basic Auth header using the configured API key.

    Always uses the API key regardless of whether an OAuth token is
    available.  Required for Freshservice endpoints that do not support
    OAuth (e.g. ``/api/v2/pm/`` Project Management NewGen).
    """
    return f"Basic {base64.b64encode(f'{FRESHSERVICE_APIKEY}:X'.encode()).decode()}"


def get_auth_headers() -> Dict[str, str]:
    """Return Basic-auth + JSON content-type headers (for POST/PUT)."""
    return {
        "Authorization": _auth_header(),
        "Content-Type": "application/json",
    }


def get_auth_headers_readonly() -> Dict[str, str]:
    """Return Basic-auth headers only (for GET/DELETE).

    Some Freshservice endpoints (e.g. status/pages) reject GET requests
    that include Content-Type: application/json.
    """
    return {"Authorization": _auth_header()}


def get_apikey_headers() -> Dict[str, str]:
    """Return API-key auth + JSON content-type headers.

    Forces Basic Auth with the API key, bypassing any per-user OAuth
    token.  Use for endpoints that do not support OAuth (e.g. PM NewGen).
    """
    return {
        "Authorization": _apikey_auth_header(),
        "Content-Type": "application/json",
    }


def get_apikey_headers_readonly() -> Dict[str, str]:
    """Return API-key auth headers only (no Content-Type).

    Forces Basic Auth with the API key, bypassing any per-user OAuth
    token.  Use for endpoints that do not support OAuth (e.g. PM NewGen).
    """
    return {"Authorization": _apikey_auth_header()}


def parse_link_header(link_header: str) -> Dict[str, Optional[int]]:
    """Parse the HTTP Link header to extract pagination page numbers."""
    pagination: Dict[str, Optional[int]] = {"next": None, "prev": None}
    if not link_header:
        return pagination
    for link in link_header.split(","):
        match = re.search(r'<(.+?)>;\s*rel="(.+?)"', link)
        if match:
            url, rel = match.groups()
            page_match = re.search(r"page=(\d+)", url)
            if page_match:
                pagination[rel] = int(page_match.group(1))
    return pagination


def api_url(path: str) -> str:
    """Build a full Freshservice API v2 URL."""
    return f"https://{FRESHSERVICE_DOMAIN}/api/v2/{path.lstrip('/')}"


async def api_get(path: str, params: Optional[Dict[str, Any]] = None,
                  headers: Optional[Dict[str, str]] = None) -> httpx.Response:
    """Perform an authenticated GET request.

    *headers* overrides the default auth-only headers.  Pass
    ``get_auth_headers()`` for endpoints that require Content-Type
    (e.g. ``/api/v2/pm/`` NewGen endpoints).
    """
    root = _path_root(path)
    start = time.monotonic()
    async with trace_span("api.get", {"http.method": "GET", "http.path_root": root}):
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                api_url(path),
                headers=headers or get_auth_headers_readonly(),
                params=params,
            )
    elapsed = time.monotonic() - start
    API_REQUESTS.labels(method="GET", path_root=root, status_code=resp.status_code).inc()
    API_DURATION.labels(method="GET", path_root=root).observe(elapsed)
    return resp


async def cached_api_get(path: str, params: Optional[Dict[str, Any]] = None,
                         headers: Optional[Dict[str, str]] = None) -> httpx.Response:
    """Like ``api_get`` but with transparent read cache.

    Checks the cache first.  On a miss, performs the real HTTP request,
    caches the response body (if 2xx), and returns it.  The caller gets
    a real ``httpx.Response`` in all cases.
    """
    cached = await cache_get(path, params)
    if cached is not None:
        return httpx.Response(
            status_code=200,
            json=json.loads(cached),
            request=httpx.Request("GET", api_url(path)),
        )

    resp = await api_get(path, params=params, headers=headers)
    if resp.is_success:
        await cache_set(path, resp.text, params)
    return resp


async def api_post(path: str, json: Optional[Any] = None,
                   headers: Optional[Dict[str, str]] = None) -> httpx.Response:
    """Perform an authenticated POST request."""
    root = _path_root(path)
    start = time.monotonic()
    async with trace_span("api.post", {"http.method": "POST", "http.path_root": root}):
        async with httpx.AsyncClient() as client:
            resp = await client.post(api_url(path), headers=headers or get_auth_headers(), json=json)
    elapsed = time.monotonic() - start
    API_REQUESTS.labels(method="POST", path_root=root, status_code=resp.status_code).inc()
    API_DURATION.labels(method="POST", path_root=root).observe(elapsed)
    return resp


async def api_put(path: str, json: Optional[Dict[str, Any]] = None,
                  headers: Optional[Dict[str, str]] = None) -> httpx.Response:
    """Perform an authenticated PUT request."""
    root = _path_root(path)
    start = time.monotonic()
    async with trace_span("api.put", {"http.method": "PUT", "http.path_root": root}):
        async with httpx.AsyncClient() as client:
            resp = await client.put(api_url(path), headers=headers or get_auth_headers(), json=json)
    elapsed = time.monotonic() - start
    API_REQUESTS.labels(method="PUT", path_root=root, status_code=resp.status_code).inc()
    API_DURATION.labels(method="PUT", path_root=root).observe(elapsed)
    return resp


async def api_delete(path: str,
                     headers: Optional[Dict[str, str]] = None) -> httpx.Response:
    """Perform an authenticated DELETE request."""
    root = _path_root(path)
    start = time.monotonic()
    async with trace_span("api.delete", {"http.method": "DELETE", "http.path_root": root}):
        async with httpx.AsyncClient() as client:
            resp = await client.delete(
                api_url(path),
                headers=headers or get_auth_headers_readonly(),
            )
    elapsed = time.monotonic() - start
    API_REQUESTS.labels(method="DELETE", path_root=root, status_code=resp.status_code).inc()
    API_DURATION.labels(method="DELETE", path_root=root).observe(elapsed)
    return resp


def handle_error(e: Exception, action: str = "request") -> Dict[str, Any]:
    """Standardised error response builder."""
    if isinstance(e, httpx.HTTPStatusError):
        try:
            details = e.response.json()
        except Exception:
            details = e.response.text
        return {"success": False, "error": f"Failed to {action}: {e}", "details": details}
    return {"success": False, "error": f"Unexpected error during {action}: {e}"}
