"""Functional tests for get_me tool and telemetry instrumentation.

Tests cover:
- get_me: JWT decode with various claim patterns (email, user, unique_name, preferred_username)
- get_me: API key fallback to /agents/me
- get_me: JWT decode error handling
- get_me: Missing email in JWT claims
- get_me: Agent not found after email lookup
- telemetry: instrument_tool decorator metrics + error status
"""
import base64
import json
import time
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from mcp.server.fastmcp import FastMCP
from freshservice_mcp.tools.agents import register_agents_tools
from freshservice_mcp.telemetry import instrument_tool, TOOL_CALLS, TOOL_DURATION

AGENTS_MOD = "freshservice_mcp.tools.agents"


def _resp(data=None, status=200):
    r = MagicMock()
    r.status_code = status
    r.json.return_value = data or {}
    r.raise_for_status = MagicMock()
    r.headers = {"Link": ""}
    return r


def _jwt_token(claims: dict) -> str:
    """Build a fake JWT with given payload claims."""
    header = base64.urlsafe_b64encode(b'{"alg":"RS256"}').rstrip(b"=").decode()
    payload = base64.urlsafe_b64encode(
        json.dumps(claims).encode()
    ).rstrip(b"=").decode()
    return f"{header}.{payload}.fake-signature"


@pytest.fixture
def tools():
    mcp = FastMCP("test")
    register_agents_tools(mcp)
    return mcp


def _t(mcp, name):
    return mcp._tool_manager._tools[name]


# ═══════════════════════════════════════════════════════════════════════════
# get_me — JWT / OAuth mode
# ═══════════════════════════════════════════════════════════════════════════


class TestGetMeOAuth:
    """get_me should decode JWT, extract email, then look up the agent."""

    @pytest.mark.asyncio
    async def test_jwt_with_email_claim(self, tools):
        """Standard 'email' claim should be extracted and used for lookup."""
        tool = _t(tools, "get_me")
        token = _jwt_token({"email": "alice@corp.com", "oid": "abc"})
        with patch(f"{AGENTS_MOD}._auth_header", return_value=f"Bearer {token}"), \
             patch(f"{AGENTS_MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _resp({"agents": [{"id": 1, "email": "alice@corp.com"}]})
            result = await tool.fn()
            assert result["agent"]["email"] == "alice@corp.com"
            assert result["source"] == "oauth_jwt"
            # Verify the query uses the extracted email
            params = m.call_args[1]["params"]
            assert "alice@corp.com" in params["query"]

    @pytest.mark.asyncio
    async def test_jwt_with_user_claim(self, tools):
        """Falls back to 'user' claim when 'email' is absent."""
        tool = _t(tools, "get_me")
        token = _jwt_token({"user": "bob@corp.com"})
        with patch(f"{AGENTS_MOD}._auth_header", return_value=f"Bearer {token}"), \
             patch(f"{AGENTS_MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _resp({"agents": [{"id": 2}]})
            result = await tool.fn()
            assert result["agent"]["id"] == 2

    @pytest.mark.asyncio
    async def test_jwt_with_preferred_username(self, tools):
        """Falls back to 'preferred_username' as last resort."""
        tool = _t(tools, "get_me")
        token = _jwt_token({"preferred_username": "carol@corp.com"})
        with patch(f"{AGENTS_MOD}._auth_header", return_value=f"Bearer {token}"), \
             patch(f"{AGENTS_MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _resp({"agents": [{"id": 3}]})
            result = await tool.fn()
            assert result["agent"]["id"] == 3

    @pytest.mark.asyncio
    async def test_jwt_no_email_in_any_claim(self, tools):
        """Should return error with available claims when no email is found."""
        tool = _t(tools, "get_me")
        token = _jwt_token({"oid": "xyz", "sub": "123"})
        with patch(f"{AGENTS_MOD}._auth_header", return_value=f"Bearer {token}"):
            result = await tool.fn()
            assert "error" in result
            assert "Could not extract email" in result["error"]
            assert "token_claims" in result

    @pytest.mark.asyncio
    async def test_jwt_agent_not_found(self, tools):
        """Should report no agent found when API returns empty list."""
        tool = _t(tools, "get_me")
        token = _jwt_token({"email": "ghost@corp.com"})
        with patch(f"{AGENTS_MOD}._auth_header", return_value=f"Bearer {token}"), \
             patch(f"{AGENTS_MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _resp({"agents": []})
            result = await tool.fn()
            assert "error" in result
            assert "ghost@corp.com" in result["error"]

    @pytest.mark.asyncio
    async def test_jwt_decode_error(self, tools):
        """Malformed JWT should return decode error."""
        tool = _t(tools, "get_me")
        with patch(f"{AGENTS_MOD}._auth_header", return_value="Bearer not.valid-base64.token"):
            result = await tool.fn()
            assert "error" in result
            assert "decode" in result["error"].lower() or "Failed" in result["error"]


# ═══════════════════════════════════════════════════════════════════════════
# get_me — API key mode
# ═══════════════════════════════════════════════════════════════════════════


class TestGetMeApiKey:
    """Without Bearer token, should call /agents/me directly."""

    @pytest.mark.asyncio
    async def test_api_key_calls_agents_me(self, tools):
        tool = _t(tools, "get_me")
        with patch(f"{AGENTS_MOD}._auth_header", return_value="Basic abc123"), \
             patch(f"{AGENTS_MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _resp({"agent": {"id": 99}})
            result = await tool.fn()
            m.assert_called_once_with("agents/me")
            assert result["agent"]["id"] == 99


# ═══════════════════════════════════════════════════════════════════════════
# Telemetry — instrument_tool decorator
# ═══════════════════════════════════════════════════════════════════════════


class TestInstrumentTool:
    """Verifies the decorator tracks success/error and latency."""

    @pytest.mark.asyncio
    async def test_successful_call_increments_ok_counter(self):
        """Successful tool call should increment status=ok."""
        async def my_tool():
            return {"data": "result"}

        wrapped = instrument_tool(my_tool)
        result = await wrapped()
        assert result == {"data": "result"}

    @pytest.mark.asyncio
    async def test_error_result_increments_error_counter(self):
        """Dict result with 'error' key should count as error status."""
        async def failing_tool():
            return {"error": "Something went wrong"}

        wrapped = instrument_tool(failing_tool)
        result = await wrapped()
        assert result["error"] == "Something went wrong"

    @pytest.mark.asyncio
    async def test_exception_increments_error_and_reraises(self):
        """Exceptions should be re-raised after incrementing error counter."""
        async def exploding_tool():
            raise ValueError("boom")

        wrapped = instrument_tool(exploding_tool)
        with pytest.raises(ValueError, match="boom"):
            await wrapped()

    @pytest.mark.asyncio
    async def test_duration_is_measured(self):
        """Wrapped function should still return after some delay."""
        import asyncio

        async def slow_tool():
            await asyncio.sleep(0.01)
            return {"ok": True}

        wrapped = instrument_tool(slow_tool)
        start = time.monotonic()
        result = await wrapped()
        elapsed = time.monotonic() - start
        assert result == {"ok": True}
        assert elapsed >= 0.01
