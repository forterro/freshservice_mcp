"""Functional tests for status_page.py — maintenance windows, incidents, subscribers.

Covers the big uncovered sections:
- manage_maintenance_window: create with change_id + impacted_services auto-publish
- manage_status_page: incident CRUD, subscriber CRUD, maintenance CRUD/updates
- Helper functions: _resolve_workspace_id, _resolve_status_page_id, _maint_prefix
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
from mcp.server.fastmcp import FastMCP

from freshservice_mcp.tools.status_page import register_status_page_tools

MOD = "freshservice_mcp.tools.status_page"


def _resp(data=None, status=200):
    r = MagicMock()
    r.status_code = status
    r.json.return_value = data or {}
    r.raise_for_status = MagicMock()
    r.headers = {"Link": ""}
    return r


def _raise(*a, **kw):
    raise Exception("API error")


def _http_error(status=422, body="Validation Error"):
    resp = MagicMock(status_code=status, text=body)
    resp.json.return_value = {"error": body}
    return httpx.HTTPStatusError("err", request=MagicMock(), response=resp)


@pytest.fixture(autouse=True)
def reset_caches():
    """Reset module-level caches before each test."""
    import freshservice_mcp.tools.status_page as sp_mod
    sp_mod._cached_workspace_id = None
    sp_mod._cached_status_page_id = None
    yield


@pytest.fixture
def tools():
    mcp = FastMCP("test")
    register_status_page_tools(mcp)
    return mcp


def _t(mcp, name):
    return mcp._tool_manager._tools[name]


# ═══════════════════════════════════════════════════════════════════════════
# Helper functions
# ═══════════════════════════════════════════════════════════════════════════


class TestMaintPrefix:
    def test_change_id_takes_priority(self):
        from freshservice_mcp.tools.status_page import _maint_prefix
        assert _maint_prefix(10, 20) == "changes/10"

    def test_maintenance_window_id_fallback(self):
        from freshservice_mcp.tools.status_page import _maint_prefix
        assert _maint_prefix(None, 20) == "maintenance-windows/20"

    def test_none_when_both_absent(self):
        from freshservice_mcp.tools.status_page import _maint_prefix
        assert _maint_prefix(None, None) is None


class TestResolveWorkspaceId:
    @pytest.mark.asyncio
    async def test_resolves_from_api(self):
        from freshservice_mcp.tools.status_page import _resolve_workspace_id
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _resp({"workspaces": [{"id": 42}]})
            result = await _resolve_workspace_id()
            assert result == 42

    @pytest.mark.asyncio
    async def test_returns_none_on_error(self):
        from freshservice_mcp.tools.status_page import _resolve_workspace_id
        with patch(f"{MOD}.api_get", new_callable=AsyncMock, side_effect=_raise):
            result = await _resolve_workspace_id()
            assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_empty(self):
        from freshservice_mcp.tools.status_page import _resolve_workspace_id
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _resp({"workspaces": []})
            result = await _resolve_workspace_id()
            assert result is None


class TestResolveStatusPageId:
    @pytest.mark.asyncio
    async def test_explicit_id_returned(self):
        from freshservice_mcp.tools.status_page import _resolve_status_page_id
        result = await _resolve_status_page_id(explicit_id=99)
        assert result == 99

    @pytest.mark.asyncio
    async def test_auto_discovers(self):
        from freshservice_mcp.tools.status_page import _resolve_status_page_id
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            # First call: workspaces, second: status/pages
            m.side_effect = [
                _resp({"workspaces": [{"id": 1}]}),
                _resp({"status_pages": [{"id": 77}]}),
            ]
            result = await _resolve_status_page_id()
            assert result == 77


# ═══════════════════════════════════════════════════════════════════════════
# manage_maintenance_window — the big complex tool
# ═══════════════════════════════════════════════════════════════════════════


class TestMaintenanceWindowList:
    @pytest.mark.asyncio
    async def test_list(self, tools):
        tool = _t(tools, "manage_maintenance_window")
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _resp({"maintenance_windows": []})
            result = await tool.fn(action="list")
            m.assert_called_once()
            assert "maintenance_windows" in result

    @pytest.mark.asyncio
    async def test_list_error(self, tools):
        tool = _t(tools, "manage_maintenance_window")
        with patch(f"{MOD}.api_get", new_callable=AsyncMock, side_effect=_raise):
            result = await tool.fn(action="list")
            assert "error" in result


class TestMaintenanceWindowGet:
    @pytest.mark.asyncio
    async def test_get(self, tools):
        tool = _t(tools, "manage_maintenance_window")
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _resp({"maintenance_window": {"id": 5}})
            result = await tool.fn(action="get", maintenance_window_id=5)
            m.assert_called_once_with("maintenance_windows/5")

    @pytest.mark.asyncio
    async def test_get_requires_id(self, tools):
        tool = _t(tools, "manage_maintenance_window")
        result = await tool.fn(action="get")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_get_error(self, tools):
        tool = _t(tools, "manage_maintenance_window")
        with patch(f"{MOD}.api_get", new_callable=AsyncMock, side_effect=_raise):
            result = await tool.fn(action="get", maintenance_window_id=1)
            assert "error" in result


class TestMaintenanceWindowCreate:
    @pytest.mark.asyncio
    async def test_create_simple(self, tools):
        """Create without change_id or impacted_services."""
        tool = _t(tools, "manage_maintenance_window")
        with patch(f"{MOD}.api_post", new_callable=AsyncMock) as mp, \
             patch(f"{MOD}.api_get", new_callable=AsyncMock) as mg:
            mg.return_value = _resp({"workspaces": [{"id": 1}]})
            mp.return_value = _resp({"maintenance_window": {"id": 10}}, 201)
            result = await tool.fn(
                action="create", name="MW1",
                start_time="2025-01-01T00:00:00Z",
                end_time="2025-01-01T06:00:00Z",
            )
            assert result["success"] is True
            assert result["maintenance_window"]["id"] == 10
            # Should suggest next step to publish on status page
            assert "next_steps" in result

    @pytest.mark.asyncio
    async def test_create_requires_name(self, tools):
        tool = _t(tools, "manage_maintenance_window")
        result = await tool.fn(action="create", start_time="x", end_time="y")
        assert "error" in result
        assert "name" in result["error"]

    @pytest.mark.asyncio
    async def test_create_requires_times(self, tools):
        tool = _t(tools, "manage_maintenance_window")
        result = await tool.fn(action="create", name="MW")
        assert "error" in result
        assert "start_time" in result["error"]

    @pytest.mark.asyncio
    async def test_create_with_change_id_success(self, tools):
        """Create MW + auto-associate with change."""
        tool = _t(tools, "manage_maintenance_window")
        with patch(f"{MOD}.api_post", new_callable=AsyncMock) as mp, \
             patch(f"{MOD}.api_put", new_callable=AsyncMock) as mput, \
             patch(f"{MOD}.api_get", new_callable=AsyncMock) as mg:
            mg.return_value = _resp({"workspaces": [{"id": 1}]})
            mp.return_value = _resp({"maintenance_window": {"id": 10}}, 201)
            # Simulate successful association
            mput.return_value = _resp({
                "change": {"id": 5, "maintenance_window": {"id": 10}}
            })
            result = await tool.fn(
                action="create", name="MW1", change_id=5,
                start_time="2025-01-01T00:00:00Z",
                end_time="2025-01-01T06:00:00Z",
            )
            assert result["success"] is True
            assert result["change_association"]["associated"] is True

    @pytest.mark.asyncio
    async def test_create_with_change_id_http_error(self, tools):
        """Association fails with HTTP error — should report it."""
        tool = _t(tools, "manage_maintenance_window")
        with patch(f"{MOD}.api_post", new_callable=AsyncMock) as mp, \
             patch(f"{MOD}.api_put", new_callable=AsyncMock) as mput, \
             patch(f"{MOD}.api_get", new_callable=AsyncMock) as mg:
            mg.return_value = _resp({"workspaces": [{"id": 1}]})
            mp.return_value = _resp({"maintenance_window": {"id": 10}}, 201)
            mput.side_effect = _http_error(422, "Invalid change")
            result = await tool.fn(
                action="create", name="MW1", change_id=5,
                start_time="2025-01-01T00:00:00Z",
                end_time="2025-01-01T06:00:00Z",
            )
            # MW created but association failed
            assert result["success"] is True
            assert result["change_association"]["associated"] is False
            assert "error" in result["change_association"]

    @pytest.mark.asyncio
    async def test_create_with_change_id_generic_error(self, tools):
        """Association fails with generic exception."""
        tool = _t(tools, "manage_maintenance_window")
        with patch(f"{MOD}.api_post", new_callable=AsyncMock) as mp, \
             patch(f"{MOD}.api_put", new_callable=AsyncMock) as mput, \
             patch(f"{MOD}.api_get", new_callable=AsyncMock) as mg:
            mg.return_value = _resp({"workspaces": [{"id": 1}]})
            mp.return_value = _resp({"maintenance_window": {"id": 10}}, 201)
            mput.side_effect = Exception("Connection timeout")
            result = await tool.fn(
                action="create", name="MW1", change_id=5,
                start_time="2025-01-01T00:00:00Z",
                end_time="2025-01-01T06:00:00Z",
            )
            assert result["success"] is True
            assert result["change_association"]["associated"] is False

    @pytest.mark.asyncio
    async def test_create_with_impacted_services(self, tools):
        """Create MW + auto-publish on status page."""
        tool = _t(tools, "manage_maintenance_window")
        with patch(f"{MOD}.api_post", new_callable=AsyncMock) as mp, \
             patch(f"{MOD}.api_get", new_callable=AsyncMock) as mg:
            # _resolve_workspace_id caches after first call, so
            # _resolve_status_page_id only needs status/pages
            mg.side_effect = [
                _resp({"workspaces": [{"id": 1}]}),  # workspace resolution (create)
                _resp({"status_pages": [{"id": 77}]}),  # status page resolve
            ]
            # First post: create MW; second post: publish on status page
            mp.side_effect = [
                _resp({"maintenance_window": {"id": 10}}, 201),
                _resp({"maintenance": {"id": 99}}, 201),
            ]
            result = await tool.fn(
                action="create", name="MW1",
                start_time="2025-01-01T00:00:00Z",
                end_time="2025-01-01T06:00:00Z",
                impacted_services=[{"id": 1, "status": 5}],
            )
            assert result["success"] is True
            assert result["status_page"]["published"] is True

    @pytest.mark.asyncio
    async def test_create_with_impacted_services_no_status_page(self, tools):
        """Auto-publish fails when no status page found."""
        tool = _t(tools, "manage_maintenance_window")
        with patch(f"{MOD}.api_post", new_callable=AsyncMock) as mp, \
             patch(f"{MOD}.api_get", new_callable=AsyncMock) as mg:
            mg.side_effect = [
                _resp({"workspaces": [{"id": 1}]}),  # workspace
                _resp({"status_pages": []}),  # no pages
            ]
            mp.return_value = _resp({"maintenance_window": {"id": 10}}, 201)
            result = await tool.fn(
                action="create", name="MW1",
                start_time="2025-01-01T00:00:00Z",
                end_time="2025-01-01T06:00:00Z",
                impacted_services=[{"id": 1, "status": 5}],
            )
            assert result["success"] is True
            assert result["status_page"]["published"] is False
            assert "error" in result["status_page"]

    @pytest.mark.asyncio
    async def test_create_with_impacted_services_http_error(self, tools):
        """Auto-publish HTTP error is captured."""
        tool = _t(tools, "manage_maintenance_window")
        with patch(f"{MOD}.api_post", new_callable=AsyncMock) as mp, \
             patch(f"{MOD}.api_get", new_callable=AsyncMock) as mg:
            mg.side_effect = [
                _resp({"workspaces": [{"id": 1}]}),
                _resp({"status_pages": [{"id": 77}]}),
            ]
            mp.side_effect = [
                _resp({"maintenance_window": {"id": 10}}, 201),
                _http_error(500, "Server Error"),
            ]
            result = await tool.fn(
                action="create", name="MW1",
                start_time="2025-01-01T00:00:00Z",
                end_time="2025-01-01T06:00:00Z",
                impacted_services=[{"id": 1, "status": 5}],
            )
            assert result["success"] is True
            assert result["status_page"]["published"] is False
            assert "error" in result["status_page"]

    @pytest.mark.asyncio
    async def test_create_api_failure(self, tools):
        """MW creation itself fails."""
        tool = _t(tools, "manage_maintenance_window")
        with patch(f"{MOD}.api_post", new_callable=AsyncMock, side_effect=_raise), \
             patch(f"{MOD}.api_get", new_callable=AsyncMock) as mg:
            mg.return_value = _resp({"workspaces": [{"id": 1}]})
            result = await tool.fn(
                action="create", name="MW1",
                start_time="2025-01-01T00:00:00Z",
                end_time="2025-01-01T06:00:00Z",
            )
            assert "error" in result

    @pytest.mark.asyncio
    async def test_create_verification_mismatch(self, tools):
        """Change association PUT returns 200 but ID doesn't match."""
        tool = _t(tools, "manage_maintenance_window")
        with patch(f"{MOD}.api_post", new_callable=AsyncMock) as mp, \
             patch(f"{MOD}.api_put", new_callable=AsyncMock) as mput, \
             patch(f"{MOD}.api_get", new_callable=AsyncMock) as mg:
            mg.return_value = _resp({"workspaces": [{"id": 1}]})
            mp.return_value = _resp({"maintenance_window": {"id": 10}}, 201)
            mput.return_value = _resp({
                "change": {"id": 5, "maintenance_window": {"id": 999}, "change_window_id": 777}
            })
            result = await tool.fn(
                action="create", name="MW", change_id=5,
                start_time="2025-01-01T00:00:00Z",
                end_time="2025-01-01T06:00:00Z",
            )
            assert result["change_association"]["associated"] is False
            assert "error" in result["change_association"]
            assert "999" in result["change_association"]["error"]


class TestMaintenanceWindowUpdate:
    @pytest.mark.asyncio
    async def test_update(self, tools):
        tool = _t(tools, "manage_maintenance_window")
        with patch(f"{MOD}.api_put", new_callable=AsyncMock) as m:
            m.return_value = _resp({"maintenance_window": {"id": 5}})
            result = await tool.fn(action="update", maintenance_window_id=5, name="New")
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_update_requires_id(self, tools):
        tool = _t(tools, "manage_maintenance_window")
        result = await tool.fn(action="update", name="X")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_update_error(self, tools):
        tool = _t(tools, "manage_maintenance_window")
        with patch(f"{MOD}.api_put", new_callable=AsyncMock, side_effect=_raise):
            result = await tool.fn(action="update", maintenance_window_id=5)
            assert "error" in result


class TestMaintenanceWindowDelete:
    @pytest.mark.asyncio
    async def test_delete(self, tools):
        tool = _t(tools, "manage_maintenance_window")
        with patch(f"{MOD}.api_delete", new_callable=AsyncMock) as m:
            m.return_value = _resp(status=204)
            result = await tool.fn(action="delete", maintenance_window_id=5)
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_delete_requires_id(self, tools):
        tool = _t(tools, "manage_maintenance_window")
        result = await tool.fn(action="delete")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_delete_error(self, tools):
        tool = _t(tools, "manage_maintenance_window")
        with patch(f"{MOD}.api_delete", new_callable=AsyncMock, side_effect=_raise):
            result = await tool.fn(action="delete", maintenance_window_id=5)
            assert "error" in result


# ═══════════════════════════════════════════════════════════════════════════
# manage_status_page — incidents, subscribers, maintenance actions
# ═══════════════════════════════════════════════════════════════════════════


@pytest.fixture
def sp_tool(tools):
    """Shortcut to get the manage_status_page tool with auto-resolved status page."""
    return _t(tools, "manage_status_page")


class TestStatusPageIncidents:
    """Incident CRUD and updates — lines 450-590."""

    @pytest.mark.asyncio
    async def test_list_incidents(self, sp_tool):
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.side_effect = [
                _resp({"workspaces": [{"id": 1}]}),
                _resp({"status_pages": [{"id": 77}]}),
                _resp({"incidents": []}),
            ]
            result = await sp_tool.fn(action="list_incidents")
            assert "incidents" in result

    @pytest.mark.asyncio
    async def test_create_incident(self, sp_tool):
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as mg, \
             patch(f"{MOD}.api_post", new_callable=AsyncMock) as mp:
            mg.side_effect = [
                _resp({"workspaces": [{"id": 1}]}),
                _resp({"status_pages": [{"id": 77}]}),
            ]
            mp.return_value = _resp({"incident": {"id": 1}}, 201)
            result = await sp_tool.fn(
                action="create_incident", ticket_id=100, title="Outage",
                impacted_services=[{"id": 1, "status": 30}],
            )
            assert result["success"] is True
            # Verify endpoint includes ticket_id
            call_url = mp.call_args[0][0]
            assert "tickets/100/status/pages/77/incidents" in call_url

    @pytest.mark.asyncio
    async def test_create_incident_requires_ticket(self, sp_tool):
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as mg:
            mg.side_effect = [
                _resp({"workspaces": [{"id": 1}]}),
                _resp({"status_pages": [{"id": 77}]}),
            ]
            result = await sp_tool.fn(action="create_incident", title="X")
            assert "error" in result

    @pytest.mark.asyncio
    async def test_create_incident_requires_title(self, sp_tool):
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as mg:
            mg.side_effect = [
                _resp({"workspaces": [{"id": 1}]}),
                _resp({"status_pages": [{"id": 77}]}),
            ]
            result = await sp_tool.fn(action="create_incident", ticket_id=1)
            assert "error" in result

    @pytest.mark.asyncio
    async def test_get_incident(self, sp_tool):
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.side_effect = [
                _resp({"workspaces": [{"id": 1}]}),
                _resp({"status_pages": [{"id": 77}]}),
                _resp({"incident": {"id": 5}}),
            ]
            result = await sp_tool.fn(action="get_incident", ticket_id=1, incident_id=5)
            assert result["incident"]["id"] == 5

    @pytest.mark.asyncio
    async def test_update_incident(self, sp_tool):
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as mg, \
             patch(f"{MOD}.api_put", new_callable=AsyncMock) as mp:
            mg.side_effect = [
                _resp({"workspaces": [{"id": 1}]}),
                _resp({"status_pages": [{"id": 77}]}),
            ]
            mp.return_value = _resp({"incident": {"id": 5}})
            result = await sp_tool.fn(
                action="update_incident", ticket_id=1, incident_id=5, title="Updated",
            )
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_delete_incident(self, sp_tool):
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as mg, \
             patch(f"{MOD}.api_delete", new_callable=AsyncMock) as md:
            mg.side_effect = [
                _resp({"workspaces": [{"id": 1}]}),
                _resp({"status_pages": [{"id": 77}]}),
            ]
            md.return_value = _resp(status=204)
            result = await sp_tool.fn(action="delete_incident", ticket_id=1, incident_id=5)
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_list_incident_updates(self, sp_tool):
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.side_effect = [
                _resp({"workspaces": [{"id": 1}]}),
                _resp({"status_pages": [{"id": 77}]}),
                _resp({"updates": []}),
            ]
            result = await sp_tool.fn(
                action="list_incident_updates", ticket_id=1, incident_id=5,
            )
            assert "updates" in result

    @pytest.mark.asyncio
    async def test_create_incident_update(self, sp_tool):
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as mg, \
             patch(f"{MOD}.api_post", new_callable=AsyncMock) as mp:
            mg.side_effect = [
                _resp({"workspaces": [{"id": 1}]}),
                _resp({"status_pages": [{"id": 77}]}),
            ]
            mp.return_value = _resp({"update": {"id": 1}}, 201)
            result = await sp_tool.fn(
                action="create_incident_update", ticket_id=1, incident_id=5,
                body="Investigating",
            )
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_update_incident_update(self, sp_tool):
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as mg, \
             patch(f"{MOD}.api_put", new_callable=AsyncMock) as mp:
            mg.side_effect = [
                _resp({"workspaces": [{"id": 1}]}),
                _resp({"status_pages": [{"id": 77}]}),
            ]
            mp.return_value = _resp({"update": {"id": 2}})
            result = await sp_tool.fn(
                action="update_incident_update", ticket_id=1, incident_id=5,
                update_id=2, body="Resolved",
            )
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_delete_incident_update(self, sp_tool):
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as mg, \
             patch(f"{MOD}.api_delete", new_callable=AsyncMock) as md:
            mg.side_effect = [
                _resp({"workspaces": [{"id": 1}]}),
                _resp({"status_pages": [{"id": 77}]}),
            ]
            md.return_value = _resp(status=204)
            result = await sp_tool.fn(
                action="delete_incident_update", ticket_id=1, incident_id=5, update_id=2,
            )
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_list_incident_statuses(self, sp_tool):
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.side_effect = [
                _resp({"workspaces": [{"id": 1}]}),
                _resp({"status_pages": [{"id": 77}]}),
                _resp({"statuses": [{"id": 1, "name": "Investigating"}]}),
            ]
            result = await sp_tool.fn(action="list_incident_statuses")
            assert "statuses" in result


class TestStatusPageSubscribers:
    """Subscriber CRUD — lines 585-660."""

    @pytest.mark.asyncio
    async def test_list_subscribers(self, sp_tool):
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.side_effect = [
                _resp({"workspaces": [{"id": 1}]}),
                _resp({"status_pages": [{"id": 77}]}),
                _resp({"subscribers": []}),
            ]
            result = await sp_tool.fn(action="list_subscribers")
            assert "subscribers" in result

    @pytest.mark.asyncio
    async def test_get_subscriber(self, sp_tool):
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.side_effect = [
                _resp({"workspaces": [{"id": 1}]}),
                _resp({"status_pages": [{"id": 77}]}),
                _resp({"subscriber": {"id": 3}}),
            ]
            result = await sp_tool.fn(action="get_subscriber", subscriber_id=3)
            assert result["subscriber"]["id"] == 3

    @pytest.mark.asyncio
    async def test_get_subscriber_requires_id(self, sp_tool):
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.side_effect = [
                _resp({"workspaces": [{"id": 1}]}),
                _resp({"status_pages": [{"id": 77}]}),
            ]
            result = await sp_tool.fn(action="get_subscriber")
            assert "error" in result

    @pytest.mark.asyncio
    async def test_create_subscriber(self, sp_tool):
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as mg, \
             patch(f"{MOD}.api_post", new_callable=AsyncMock) as mp:
            mg.side_effect = [
                _resp({"workspaces": [{"id": 1}]}),
                _resp({"status_pages": [{"id": 77}]}),
            ]
            mp.return_value = _resp({"subscriber": {"id": 4}}, 201)
            result = await sp_tool.fn(
                action="create_subscriber", email="test@example.com",
                service_ids=[1, 2], subscriber_type="email",
            )
            assert result["success"] is True
            payload = mp.call_args[1]["json"]
            assert payload["email"] == "test@example.com"
            assert payload["service_ids"] == [1, 2]
            assert payload["type"] == "email"

    @pytest.mark.asyncio
    async def test_create_subscriber_requires_email(self, sp_tool):
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.side_effect = [
                _resp({"workspaces": [{"id": 1}]}),
                _resp({"status_pages": [{"id": 77}]}),
            ]
            result = await sp_tool.fn(action="create_subscriber")
            assert "error" in result

    @pytest.mark.asyncio
    async def test_update_subscriber(self, sp_tool):
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as mg, \
             patch(f"{MOD}.api_put", new_callable=AsyncMock) as mp:
            mg.side_effect = [
                _resp({"workspaces": [{"id": 1}]}),
                _resp({"status_pages": [{"id": 77}]}),
            ]
            mp.return_value = _resp({"subscriber": {"id": 3}})
            result = await sp_tool.fn(
                action="update_subscriber", subscriber_id=3,
                subscribe_all_services=True, timezone="Europe/Paris",
            )
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_update_subscriber_requires_id(self, sp_tool):
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.side_effect = [
                _resp({"workspaces": [{"id": 1}]}),
                _resp({"status_pages": [{"id": 77}]}),
            ]
            result = await sp_tool.fn(action="update_subscriber")
            assert "error" in result

    @pytest.mark.asyncio
    async def test_delete_subscriber(self, sp_tool):
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as mg, \
             patch(f"{MOD}.api_delete", new_callable=AsyncMock) as md:
            mg.side_effect = [
                _resp({"workspaces": [{"id": 1}]}),
                _resp({"status_pages": [{"id": 77}]}),
            ]
            md.return_value = _resp(status=204)
            result = await sp_tool.fn(action="delete_subscriber", subscriber_id=3)
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_delete_subscriber_requires_id(self, sp_tool):
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.side_effect = [
                _resp({"workspaces": [{"id": 1}]}),
                _resp({"status_pages": [{"id": 77}]}),
            ]
            result = await sp_tool.fn(action="delete_subscriber")
            assert "error" in result


class TestStatusPageMaintenance:
    """Maintenance CRUD from manage_status_page — lines 275-430."""

    @pytest.mark.asyncio
    async def test_create_maintenance_from_change(self, sp_tool):
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as mg, \
             patch(f"{MOD}.api_post", new_callable=AsyncMock) as mp:
            mg.side_effect = [
                _resp({"workspaces": [{"id": 1}]}),
                _resp({"status_pages": [{"id": 77}]}),
            ]
            mp.return_value = _resp({"maintenance": {"id": 1}}, 201)
            result = await sp_tool.fn(
                action="create_maintenance", change_id=10,
                title="Planned", started_at="2025-01-01", ended_at="2025-01-02",
                impacted_services=[{"id": 1, "status": 5}],
            )
            assert result["success"] is True
            call_url = mp.call_args[0][0]
            assert "changes/10/status/pages/77/maintenances" in call_url

    @pytest.mark.asyncio
    async def test_create_maintenance_requires_prefix(self, sp_tool):
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.side_effect = [
                _resp({"workspaces": [{"id": 1}]}),
                _resp({"status_pages": [{"id": 77}]}),
            ]
            result = await sp_tool.fn(action="create_maintenance", title="X")
            assert "error" in result
            assert "change_id or maintenance_window_id required" in result["error"]

    @pytest.mark.asyncio
    async def test_get_maintenance(self, sp_tool):
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.side_effect = [
                _resp({"workspaces": [{"id": 1}]}),
                _resp({"status_pages": [{"id": 77}]}),
                _resp({"maintenance": {"id": 5}}),
            ]
            result = await sp_tool.fn(
                action="get_maintenance", change_id=10, maintenance_id=5,
            )
            assert result["maintenance"]["id"] == 5

    @pytest.mark.asyncio
    async def test_update_maintenance(self, sp_tool):
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as mg, \
             patch(f"{MOD}.api_put", new_callable=AsyncMock) as mp:
            mg.side_effect = [
                _resp({"workspaces": [{"id": 1}]}),
                _resp({"status_pages": [{"id": 77}]}),
            ]
            mp.return_value = _resp({"maintenance": {"id": 5}})
            result = await sp_tool.fn(
                action="update_maintenance", change_id=10, maintenance_id=5,
                title="Updated",
            )
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_delete_maintenance(self, sp_tool):
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as mg, \
             patch(f"{MOD}.api_delete", new_callable=AsyncMock) as md:
            mg.side_effect = [
                _resp({"workspaces": [{"id": 1}]}),
                _resp({"status_pages": [{"id": 77}]}),
            ]
            md.return_value = _resp(status=204)
            result = await sp_tool.fn(
                action="delete_maintenance", change_id=10, maintenance_id=5,
            )
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_list_maintenance_updates(self, sp_tool):
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.side_effect = [
                _resp({"workspaces": [{"id": 1}]}),
                _resp({"status_pages": [{"id": 77}]}),
                _resp({"updates": []}),
            ]
            result = await sp_tool.fn(
                action="list_maintenance_updates", change_id=10, maintenance_id=5,
            )
            assert "updates" in result

    @pytest.mark.asyncio
    async def test_create_maintenance_update(self, sp_tool):
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as mg, \
             patch(f"{MOD}.api_post", new_callable=AsyncMock) as mp:
            mg.side_effect = [
                _resp({"workspaces": [{"id": 1}]}),
                _resp({"status_pages": [{"id": 77}]}),
            ]
            mp.return_value = _resp({"update": {"id": 1}}, 201)
            result = await sp_tool.fn(
                action="create_maintenance_update", change_id=10,
                maintenance_id=5, body="In progress",
            )
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_update_maintenance_update(self, sp_tool):
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as mg, \
             patch(f"{MOD}.api_put", new_callable=AsyncMock) as mp:
            mg.side_effect = [
                _resp({"workspaces": [{"id": 1}]}),
                _resp({"status_pages": [{"id": 77}]}),
            ]
            mp.return_value = _resp({"update": {"id": 2}})
            result = await sp_tool.fn(
                action="update_maintenance_update", change_id=10,
                maintenance_id=5, update_id=2, body="Done",
            )
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_delete_maintenance_update(self, sp_tool):
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as mg, \
             patch(f"{MOD}.api_delete", new_callable=AsyncMock) as md:
            mg.side_effect = [
                _resp({"workspaces": [{"id": 1}]}),
                _resp({"status_pages": [{"id": 77}]}),
            ]
            md.return_value = _resp(status=204)
            result = await sp_tool.fn(
                action="delete_maintenance_update", change_id=10,
                maintenance_id=5, update_id=2,
            )
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_list_maintenance_statuses(self, sp_tool):
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.side_effect = [
                _resp({"workspaces": [{"id": 1}]}),
                _resp({"status_pages": [{"id": 77}]}),
                _resp({"statuses": []}),
            ]
            result = await sp_tool.fn(action="list_maintenance_statuses")
            assert "statuses" in result

    @pytest.mark.asyncio
    async def test_unknown_action(self, sp_tool):
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.side_effect = [
                _resp({"workspaces": [{"id": 1}]}),
                _resp({"status_pages": [{"id": 77}]}),
            ]
            result = await sp_tool.fn(action="bogus_action")
            assert "error" in result
            assert "Unknown action" in result["error"]
