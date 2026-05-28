"""Tests for freshservice_mcp.server module."""
import os
import pytest
from unittest.mock import patch, MagicMock

from freshservice_mcp.server import _resolve_scopes, _resolve_transport, VALID_TRANSPORTS


class TestResolveTransport:
    def test_explicit_transport(self):
        assert _resolve_transport("sse") == "sse"
        assert _resolve_transport("stdio") == "stdio"
        assert _resolve_transport("streamable-http") == "streamable-http"

    def test_env_var_fallback(self):
        with patch.dict(os.environ, {"MCP_TRANSPORT": "sse"}):
            assert _resolve_transport(None) == "sse"

    def test_default_is_stdio(self):
        with patch.dict(os.environ, {"MCP_TRANSPORT": ""}, clear=False):
            os.environ.pop("MCP_TRANSPORT", None)
            assert _resolve_transport(None) == "stdio"

    def test_invalid_transport_exits(self):
        with pytest.raises(SystemExit):
            _resolve_transport("invalid")


class TestResolveScopes:
    def test_explicit_scopes(self):
        scopes = _resolve_scopes(["tickets", "changes"])
        assert "tickets" in scopes
        assert "changes" in scopes

    def test_env_var_scopes(self):
        with patch.dict(os.environ, {"FRESHSERVICE_SCOPES": "tickets,agents"}):
            scopes = _resolve_scopes(None)
            assert "tickets" in scopes
            assert "agents" in scopes

    def test_default_all_scopes(self):
        with patch.dict(os.environ, {"FRESHSERVICE_SCOPES": ""}):
            scopes = _resolve_scopes(None)
            assert len(scopes) > 5  # All scopes loaded


class TestValidTransports:
    def test_valid_transports_defined(self):
        assert "stdio" in VALID_TRANSPORTS
        assert "sse" in VALID_TRANSPORTS
        assert "streamable-http" in VALID_TRANSPORTS
