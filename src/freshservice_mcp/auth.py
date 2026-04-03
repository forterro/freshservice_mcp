"""Per-request auth token forwarding via contextvars.

When running behind an MCP gateway (e.g. ContextForge), the gateway
authenticates the end-user and forwards their credentials in the
``Authorization`` header of each HTTP request to this backend MCP
server. Both Bearer (OAuth) and Basic (API key) schemes are supported.

This module provides:

- ``forwarded_auth_var`` — a contextvars.ContextVar that holds the
  full Authorization header value extracted from the current request
  (or ``None``).
- ``ForwardedAuthMiddleware`` — ASGI middleware that extracts the
  header and sets the contextvar for each request.

The HTTP client (``http_client.py``) reads ``forwarded_auth_var`` to
decide between forwarded auth (per-user Bearer or Basic from gateway)
and fallback Basic auth (API key from env for local dev / stdio).
"""

import contextvars
from starlette.types import ASGIApp, Receive, Scope, Send
from starlette.requests import Request

from .telemetry import AUTH_MODE

forwarded_auth_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "forwarded_auth", default=None
)

# Backward-compatible alias
forwarded_token_var = forwarded_auth_var


class ForwardedAuthMiddleware:
    """Extract Authorization header from incoming requests into a contextvar.

    Supports both Bearer (OAuth) and Basic (API key) schemes forwarded
    by the MCP gateway.  This allows tool handlers (via ``http_client.py``)
    to transparently use the per-user credentials without any changes to
    tool code.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            request = Request(scope)
            auth = request.headers.get("authorization", "")
            auth_lower = auth.lower()
            forwarded: str | None = None
            if auth_lower.startswith("bearer "):
                forwarded = auth  # full header value: "Bearer <token>"
            elif auth_lower.startswith("basic "):
                forwarded = auth  # full header value: "Basic <b64>"
            # Count auth mode only for MCP traffic (skip infra endpoints)
            path = request.url.path
            if path not in ("/healthz", "/metrics"):
                if forwarded and auth_lower.startswith("bearer "):
                    AUTH_MODE.labels(mode="bearer").inc()
                elif forwarded and auth_lower.startswith("basic "):
                    AUTH_MODE.labels(mode="basic_forwarded").inc()
                else:
                    AUTH_MODE.labels(mode="apikey").inc()
            ctx_token = forwarded_auth_var.set(forwarded)
            try:
                await self.app(scope, receive, send)
            finally:
                forwarded_auth_var.reset(ctx_token)
        else:
            await self.app(scope, receive, send)
