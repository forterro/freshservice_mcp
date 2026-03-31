"""Per-request OAuth token forwarding via contextvars.

When running behind an MCP gateway (e.g. ContextForge), the gateway
authenticates the end-user and forwards their per-user OAuth Bearer
token in the ``Authorization`` header of each HTTP request to this
backend MCP server.

This module provides:

- ``forwarded_token_var`` — a contextvars.ContextVar that holds the
  Bearer token extracted from the current request (or ``None``).
- ``ForwardedAuthMiddleware`` — ASGI middleware that extracts the
  token and sets the contextvar for each request.

The HTTP client (``http_client.py``) reads ``forwarded_token_var`` to
decide between Bearer auth (per-user OAuth) and Basic auth (API key
fallback for local dev / stdio).
"""

import contextvars
from starlette.types import ASGIApp, Receive, Scope, Send
from starlette.requests import Request

from .telemetry import AUTH_MODE

forwarded_token_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "forwarded_token", default=None
)


class ForwardedAuthMiddleware:
    """Extract Bearer token from incoming requests into a contextvar.

    This allows tool handlers (via ``http_client.py``) to transparently
    use the per-user token without any changes to tool code.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            request = Request(scope)
            auth = request.headers.get("authorization", "")
            token = auth[7:] if auth.lower().startswith("bearer ") else None
            # Count auth mode only for MCP traffic (skip infra endpoints)
            path = request.url.path
            if path not in ("/healthz", "/metrics"):
                if token:
                    AUTH_MODE.labels(mode="bearer").inc()
                else:
                    AUTH_MODE.labels(mode="apikey").inc()
            ctx_token = forwarded_token_var.set(token)
            try:
                await self.app(scope, receive, send)
            finally:
                forwarded_token_var.reset(ctx_token)
        else:
            await self.app(scope, receive, send)
