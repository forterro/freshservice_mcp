"""Functional tests for server.py — scope resolution, transport selection, lifecycle.

Tests cover:
- _resolve_scopes: CLI args, env var, defaults, invalid scope handling
- _resolve_transport: CLI, env, defaults, invalid transport
- These are the pure-logic functions that don't require starting the server.
"""
import os
import pytest
from unittest.mock import patch

from freshservice_mcp.server import _resolve_scopes, _resolve_transport
from freshservice_mcp.tools import SCOPE_REGISTRY


# ═══════════════════════════════════════════════════════════════════════════
# Scope resolution
# ═══════════════════════════════════════════════════════════════════════════


class TestResolveScopes:
    """Priority: CLI args > FRESHSERVICE_SCOPES env > all scopes."""

    def test_cli_args_take_priority(self):
        """When CLI scopes given, env should be ignored."""
        with patch.dict(os.environ, {"FRESHSERVICE_SCOPES": "tickets"}):
            scopes = _resolve_scopes(["changes", "assets"])
            assert scopes == ["changes", "assets"]

    def test_env_var_used_when_no_cli(self):
        with patch.dict(os.environ, {"FRESHSERVICE_SCOPES": "tickets,changes"}):
            scopes = _resolve_scopes(None)
            assert scopes == ["tickets", "changes"]

    def test_all_scopes_when_nothing_specified(self):
        with patch.dict(os.environ, {"FRESHSERVICE_SCOPES": ""}):
            scopes = _resolve_scopes(None)
            assert set(scopes) == set(SCOPE_REGISTRY.keys())

    def test_invalid_scope_exits(self):
        with pytest.raises(SystemExit):
            _resolve_scopes(["nonexistent_scope"])

    def test_mixed_valid_invalid_exits(self):
        with pytest.raises(SystemExit):
            _resolve_scopes(["tickets", "bogus"])

    def test_empty_env_var_returns_all(self):
        """Empty string env var should load all scopes."""
        with patch.dict(os.environ, {"FRESHSERVICE_SCOPES": "  "}):
            scopes = _resolve_scopes(None)
            assert len(scopes) == len(SCOPE_REGISTRY)

    def test_env_var_with_whitespace(self):
        """Should trim whitespace from scope names."""
        with patch.dict(os.environ, {"FRESHSERVICE_SCOPES": " tickets , changes "}):
            scopes = _resolve_scopes(None)
            assert scopes == ["tickets", "changes"]


# ═══════════════════════════════════════════════════════════════════════════
# Transport resolution
# ═══════════════════════════════════════════════════════════════════════════


class TestResolveTransport:
    """Priority: CLI > MCP_TRANSPORT env > stdio."""

    def test_cli_overrides_env(self):
        with patch.dict(os.environ, {"MCP_TRANSPORT": "sse"}):
            assert _resolve_transport("streamable-http") == "streamable-http"

    def test_env_used_when_no_cli(self):
        with patch.dict(os.environ, {"MCP_TRANSPORT": "sse"}):
            assert _resolve_transport(None) == "sse"

    def test_defaults_to_stdio(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("MCP_TRANSPORT", None)
            assert _resolve_transport(None) == "stdio"

    def test_invalid_transport_exits(self):
        with pytest.raises(SystemExit):
            _resolve_transport("websocket")

    def test_all_valid_transports(self):
        for t in ("stdio", "sse", "streamable-http"):
            assert _resolve_transport(t) == t
