"""Tests for freshservice_mcp.auth module."""
import pytest
from unittest.mock import AsyncMock, MagicMock

from starlette.testclient import TestClient
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route

from freshservice_mcp.auth import ForwardedAuthMiddleware, forwarded_auth_var


def _make_app():
    """Create a test app that returns the forwarded auth value."""

    async def view(request):
        return JSONResponse({"forwarded": forwarded_auth_var.get()})

    app = Starlette(routes=[Route("/test", view)])
    return ForwardedAuthMiddleware(app)


class TestForwardedAuthMiddleware:
    def test_bearer_token_forwarded(self):
        app = _make_app()
        client = TestClient(app)
        resp = client.get("/test", headers={"Authorization": "Bearer mytoken123"})
        assert resp.status_code == 200
        assert resp.json()["forwarded"] == "Bearer mytoken123"

    def test_basic_auth_forwarded(self):
        app = _make_app()
        client = TestClient(app)
        resp = client.get("/test", headers={"Authorization": "Basic dXNlcjpwYXNz"})
        assert resp.status_code == 200
        assert resp.json()["forwarded"] == "Basic dXNlcjpwYXNz"

    def test_no_auth_header(self):
        app = _make_app()
        client = TestClient(app)
        resp = client.get("/test")
        assert resp.status_code == 200
        assert resp.json()["forwarded"] is None

    def test_empty_auth_header(self):
        app = _make_app()
        client = TestClient(app)
        resp = client.get("/test", headers={"Authorization": ""})
        assert resp.status_code == 200
        assert resp.json()["forwarded"] is None
