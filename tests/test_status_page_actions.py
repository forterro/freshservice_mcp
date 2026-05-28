"""Comprehensive tests for status_page tool actions."""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from mcp.server.fastmcp import FastMCP


def _mcp():
    from freshservice_mcp.tools.status_page import register_status_page_tools
    mcp = FastMCP("test")
    register_status_page_tools(mcp)
    return mcp


def _ok(data, code=200):
    r = MagicMock()
    r.status_code = code
    r.raise_for_status = MagicMock()
    r.json.return_value = data
    r.is_success = True
    r.text = "{}"
    return r


def _no_content():
    r = MagicMock()
    r.status_code = 204
    r.raise_for_status = MagicMock()
    return r


MOD = "freshservice_mcp.tools.status_page"


class TestStatusPageMain:
    @pytest.fixture
    def tool(self):
        return _mcp()._tool_manager._tools["manage_status_page"]

    @pytest.mark.asyncio
    async def test_list_pages(self, tool):
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"status_pages": [{"id": 1}]})
            result = await tool.fn(action="list_pages")
            assert "status_pages" in result or "error" not in result

    @pytest.mark.asyncio
    async def test_list_components(self, tool):
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"components": [{"id": 1}]})
            result = await tool.fn(action="list_components", status_page_id=1)
            assert "components" in result or "error" not in result

    @pytest.mark.asyncio
    async def test_list_components_missing_page(self, tool):
        result = await tool.fn(action="list_components")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_get_component(self, tool):
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"component": {"id": 1}})
            result = await tool.fn(action="get_component", status_page_id=1, component_id=1)
            assert "component" in result or "error" not in result

    @pytest.mark.asyncio
    async def test_get_component_missing_ids(self, tool):
        result = await tool.fn(action="get_component", status_page_id=1)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_list_maintenance(self, tool):
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"maintenances": []})
            result = await tool.fn(action="list_maintenance", status_page_id=1)
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_create_maintenance(self, tool):
        with patch(f"{MOD}.api_post", new_callable=AsyncMock) as m:
            m.return_value = _ok({"maintenance": {"id": 1}}, 201)
            result = await tool.fn(
                action="create_maintenance", status_page_id=1,
                title="Maint", description="Desc",
                started_at="2026-01-01T00:00:00Z", ended_at="2026-01-02T00:00:00Z",
                change_id=10
            )
            assert "maintenance" in result or result.get("success")

    @pytest.mark.asyncio
    async def test_create_maintenance_missing_fields(self, tool):
        result = await tool.fn(action="create_maintenance", status_page_id=1)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_get_maintenance(self, tool):
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"maintenance": {"id": 1}})
            result = await tool.fn(action="get_maintenance", status_page_id=1, change_id=10, maintenance_id=1)
            assert "maintenance" in result or "error" not in result

    @pytest.mark.asyncio
    async def test_get_maintenance_missing_id(self, tool):
        result = await tool.fn(action="get_maintenance", status_page_id=1)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_update_maintenance(self, tool):
        with patch(f"{MOD}.api_put", new_callable=AsyncMock) as m:
            m.return_value = _ok({"maintenance": {"id": 1}})
            result = await tool.fn(
                action="update_maintenance", status_page_id=1,
                change_id=10, maintenance_id=1, title="Updated"
            )
            assert "maintenance" in result or "error" not in result

    @pytest.mark.asyncio
    async def test_update_maintenance_missing_id(self, tool):
        result = await tool.fn(action="update_maintenance", status_page_id=1)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_delete_maintenance(self, tool):
        with patch(f"{MOD}.api_delete", new_callable=AsyncMock) as m:
            m.return_value = _no_content()
            result = await tool.fn(action="delete_maintenance", status_page_id=1, change_id=10, maintenance_id=1)
            assert result.get("success") is True

    @pytest.mark.asyncio
    async def test_delete_maintenance_missing_id(self, tool):
        result = await tool.fn(action="delete_maintenance", status_page_id=1)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_list_maintenance_updates(self, tool):
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"updates": []})
            result = await tool.fn(action="list_maintenance_updates", status_page_id=1, change_id=10, maintenance_id=1)
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_create_maintenance_update(self, tool):
        with patch(f"{MOD}.api_post", new_callable=AsyncMock) as m:
            m.return_value = _ok({"update": {"id": 1}}, 201)
            result = await tool.fn(
                action="create_maintenance_update", status_page_id=1,
                change_id=10, maintenance_id=1, body="Update body"
            )
            assert "update" in result or result.get("success")

    @pytest.mark.asyncio
    async def test_create_maintenance_update_missing(self, tool):
        result = await tool.fn(action="create_maintenance_update", status_page_id=1)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_update_maintenance_update(self, tool):
        with patch(f"{MOD}.api_put", new_callable=AsyncMock) as m:
            m.return_value = _ok({"update": {"id": 1}})
            result = await tool.fn(
                action="update_maintenance_update", status_page_id=1,
                change_id=10, maintenance_id=1, update_id=1, body="New body"
            )
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_update_maintenance_update_missing(self, tool):
        result = await tool.fn(action="update_maintenance_update", status_page_id=1, maintenance_id=1)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_delete_maintenance_update(self, tool):
        with patch(f"{MOD}.api_delete", new_callable=AsyncMock) as m:
            m.return_value = _no_content()
            result = await tool.fn(
                action="delete_maintenance_update", status_page_id=1,
                change_id=10, maintenance_id=1, update_id=1
            )
            assert result.get("success") is True

    @pytest.mark.asyncio
    async def test_delete_maintenance_update_missing(self, tool):
        result = await tool.fn(action="delete_maintenance_update", status_page_id=1, maintenance_id=1)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_list_maintenance_statuses(self, tool):
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"statuses": []})
            result = await tool.fn(action="list_maintenance_statuses", status_page_id=1)
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_list_incidents(self, tool):
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"incidents": []})
            result = await tool.fn(action="list_incidents", status_page_id=1)
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_create_incident(self, tool):
        with patch(f"{MOD}.api_post", new_callable=AsyncMock) as m:
            m.return_value = _ok({"incident": {"id": 1}}, 201)
            result = await tool.fn(
                action="create_incident", status_page_id=1,
                ticket_id=42, title="Outage", description="Service down",
                started_at="2026-01-01T00:00:00Z"
            )
            assert "incident" in result or result.get("success")

    @pytest.mark.asyncio
    async def test_create_incident_missing(self, tool):
        result = await tool.fn(action="create_incident", status_page_id=1)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_get_incident(self, tool):
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"incident": {"id": 1}})
            result = await tool.fn(action="get_incident", status_page_id=1, ticket_id=42, incident_id=1)
            assert "incident" in result or "error" not in result

    @pytest.mark.asyncio
    async def test_get_incident_missing(self, tool):
        result = await tool.fn(action="get_incident", status_page_id=1)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_update_incident(self, tool):
        with patch(f"{MOD}.api_put", new_callable=AsyncMock) as m:
            m.return_value = _ok({"incident": {"id": 1}})
            result = await tool.fn(
                action="update_incident", status_page_id=1,
                ticket_id=42, incident_id=1, title="Updated"
            )
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_update_incident_missing(self, tool):
        result = await tool.fn(action="update_incident", status_page_id=1)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_delete_incident(self, tool):
        with patch(f"{MOD}.api_delete", new_callable=AsyncMock) as m:
            m.return_value = _no_content()
            result = await tool.fn(action="delete_incident", status_page_id=1, ticket_id=42, incident_id=1)
            assert result.get("success") is True

    @pytest.mark.asyncio
    async def test_delete_incident_missing(self, tool):
        result = await tool.fn(action="delete_incident", status_page_id=1)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_list_incident_updates(self, tool):
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"updates": []})
            result = await tool.fn(action="list_incident_updates", status_page_id=1, ticket_id=42, incident_id=1)
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_list_incident_updates_missing(self, tool):
        result = await tool.fn(action="list_incident_updates", status_page_id=1)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_create_incident_update(self, tool):
        with patch(f"{MOD}.api_post", new_callable=AsyncMock) as m:
            m.return_value = _ok({"update": {"id": 1}}, 201)
            result = await tool.fn(
                action="create_incident_update", status_page_id=1,
                ticket_id=42, incident_id=1, body="We are investigating"
            )
            assert "update" in result or result.get("success")

    @pytest.mark.asyncio
    async def test_create_incident_update_missing(self, tool):
        result = await tool.fn(action="create_incident_update", status_page_id=1)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_update_incident_update(self, tool):
        with patch(f"{MOD}.api_put", new_callable=AsyncMock) as m:
            m.return_value = _ok({"update": {"id": 1}})
            result = await tool.fn(
                action="update_incident_update", status_page_id=1,
                ticket_id=42, incident_id=1, update_id=1, body="Fixed"
            )
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_update_incident_update_missing(self, tool):
        result = await tool.fn(action="update_incident_update", status_page_id=1, incident_id=1)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_delete_incident_update(self, tool):
        with patch(f"{MOD}.api_delete", new_callable=AsyncMock) as m:
            m.return_value = _no_content()
            result = await tool.fn(
                action="delete_incident_update", status_page_id=1,
                ticket_id=42, incident_id=1, update_id=1
            )
            assert result.get("success") is True

    @pytest.mark.asyncio
    async def test_delete_incident_update_missing(self, tool):
        result = await tool.fn(action="delete_incident_update", status_page_id=1, incident_id=1)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_list_incident_statuses(self, tool):
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"statuses": []})
            result = await tool.fn(action="list_incident_statuses", status_page_id=1)
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_list_subscribers(self, tool):
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"subscribers": []})
            result = await tool.fn(action="list_subscribers", status_page_id=1)
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_get_subscriber(self, tool):
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"subscriber": {"id": 1}})
            result = await tool.fn(action="get_subscriber", status_page_id=1, subscriber_id=1)
            assert "subscriber" in result or "error" not in result

    @pytest.mark.asyncio
    async def test_get_subscriber_missing(self, tool):
        result = await tool.fn(action="get_subscriber", status_page_id=1)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_create_subscriber(self, tool):
        with patch(f"{MOD}.api_post", new_callable=AsyncMock) as m:
            m.return_value = _ok({"subscriber": {"id": 1}}, 201)
            result = await tool.fn(
                action="create_subscriber", status_page_id=1,
                email="sub@test.com"
            )
            assert "subscriber" in result or result.get("success")

    @pytest.mark.asyncio
    async def test_create_subscriber_missing_email(self, tool):
        result = await tool.fn(action="create_subscriber", status_page_id=1)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_update_subscriber(self, tool):
        with patch(f"{MOD}.api_put", new_callable=AsyncMock) as m:
            m.return_value = _ok({"subscriber": {"id": 1}})
            result = await tool.fn(
                action="update_subscriber", status_page_id=1,
                subscriber_id=1, email="new@test.com"
            )
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_update_subscriber_missing(self, tool):
        result = await tool.fn(action="update_subscriber", status_page_id=1)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_delete_subscriber(self, tool):
        with patch(f"{MOD}.api_delete", new_callable=AsyncMock) as m:
            m.return_value = _no_content()
            result = await tool.fn(action="delete_subscriber", status_page_id=1, subscriber_id=1)
            assert result.get("success") is True

    @pytest.mark.asyncio
    async def test_delete_subscriber_missing(self, tool):
        result = await tool.fn(action="delete_subscriber", status_page_id=1)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_unknown_action(self, tool):
        result = await tool.fn(action="unknown_action")
        assert "error" in result


class TestMaintenanceWindow:
    @pytest.fixture
    def tool(self):
        return _mcp()._tool_manager._tools["manage_maintenance_window"]

    @pytest.mark.asyncio
    async def test_list(self, tool):
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"maintenance_windows": []})
            result = await tool.fn(action="list")
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_get(self, tool):
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"maintenance_window": {"id": 1}})
            result = await tool.fn(action="get", maintenance_window_id=1)
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_get_missing_id(self, tool):
        result = await tool.fn(action="get")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_delete(self, tool):
        with patch(f"{MOD}.api_delete", new_callable=AsyncMock) as m:
            m.return_value = _no_content()
            result = await tool.fn(action="delete", maintenance_window_id=1)
            assert result.get("success") is True

    @pytest.mark.asyncio
    async def test_delete_missing_id(self, tool):
        result = await tool.fn(action="delete")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_unknown_action(self, tool):
        result = await tool.fn(action="invalid")
        assert "error" in result
