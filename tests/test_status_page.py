"""Tests for freshservice_mcp.tools.status_page module."""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from freshservice_mcp.tools.status_page import (
    _resolve_workspace_id,
    _resolve_status_page_id,
    _maint_prefix,
    _cached_workspace_id,
    _cached_status_page_id,
    _ERR_MAINT_IDS,
    _ERR_INCIDENT_IDS,
    _ERR_SUBSCRIBER_ID,
)


class TestMaintPrefix:
    def test_with_change_id(self):
        assert _maint_prefix(42, None) == "changes/42"

    def test_with_maintenance_window_id(self):
        assert _maint_prefix(None, 99) == "maintenance-windows/99"

    def test_change_id_takes_priority(self):
        assert _maint_prefix(42, 99) == "changes/42"

    def test_neither_returns_none(self):
        assert _maint_prefix(None, None) is None

    def test_zero_values(self):
        assert _maint_prefix(0, 0) is None


class TestResolveStatusPageId:
    @pytest.mark.asyncio
    async def test_explicit_id_returned(self):
        result = await _resolve_status_page_id(42)
        assert result == 42

    @pytest.mark.asyncio
    async def test_auto_discover(self):
        import freshservice_mcp.tools.status_page as sp
        sp._cached_status_page_id = None

        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"status_pages": [{"id": 7}]}

        with patch("freshservice_mcp.tools.status_page.api_get", new_callable=AsyncMock) as mock_get, \
             patch("freshservice_mcp.tools.status_page._resolve_workspace_id", new_callable=AsyncMock) as mock_ws:
            mock_ws.return_value = 1
            mock_get.return_value = mock_resp
            result = await _resolve_status_page_id(None)
            assert result == 7

    @pytest.mark.asyncio
    async def test_cached_value(self):
        import freshservice_mcp.tools.status_page as sp
        sp._cached_status_page_id = 99
        result = await _resolve_status_page_id(None)
        assert result == 99
        sp._cached_status_page_id = None


class TestResolveWorkspaceId:
    @pytest.mark.asyncio
    async def test_cached_value(self):
        import freshservice_mcp.tools.status_page as sp
        sp._cached_workspace_id = 42
        result = await _resolve_workspace_id()
        assert result == 42
        sp._cached_workspace_id = None

    @pytest.mark.asyncio
    async def test_api_call(self):
        import freshservice_mcp.tools.status_page as sp
        sp._cached_workspace_id = None

        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"workspaces": [{"id": 5}]}

        with patch("freshservice_mcp.tools.status_page.api_get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_resp
            result = await _resolve_workspace_id()
            assert result == 5
        sp._cached_workspace_id = None


class TestErrorConstants:
    def test_maint_ids_message(self):
        assert "change_id" in _ERR_MAINT_IDS
        assert "maintenance_id" in _ERR_MAINT_IDS

    def test_incident_ids_message(self):
        assert "ticket_id" in _ERR_INCIDENT_IDS
        assert "incident_id" in _ERR_INCIDENT_IDS

    def test_subscriber_id_message(self):
        assert "subscriber_id" in _ERR_SUBSCRIBER_ID
