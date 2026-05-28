"""Tests for sub-tools: release notes/tasks/time_entries, locations, requester groups,
agent groups, asset details/relationships."""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from mcp.server.fastmcp import FastMCP


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


# ═══════════════════════════════════════════════════════════════════════════
# Release Note
# ═══════════════════════════════════════════════════════════════════════════
class TestReleaseNote:
    MOD = "freshservice_mcp.tools.releases"

    @pytest.fixture
    def tool(self):
        from freshservice_mcp.tools.releases import register_release_tools
        mcp = FastMCP("test")
        register_release_tools(mcp)
        return mcp._tool_manager._tools["manage_release_note"]

    @pytest.mark.asyncio
    async def test_list(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"notes": []})
            result = await tool.fn(action="list", release_id=1)
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_get(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"note": {"id": 1}})
            result = await tool.fn(action="get", release_id=1, note_id=1)
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_create(self, tool):
        with patch(f"{self.MOD}.api_post", new_callable=AsyncMock) as m:
            m.return_value = _ok({"note": {"id": 1}}, 201)
            result = await tool.fn(action="create", release_id=1, body="Note text")
            assert "note" in result or result.get("success")

    @pytest.mark.asyncio
    async def test_update(self, tool):
        with patch(f"{self.MOD}.api_put", new_callable=AsyncMock) as m:
            m.return_value = _ok({"note": {"id": 1}})
            result = await tool.fn(action="update", release_id=1, note_id=1, body="Updated")
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_delete(self, tool):
        with patch(f"{self.MOD}.api_delete", new_callable=AsyncMock) as m:
            m.return_value = _no_content()
            result = await tool.fn(action="delete", release_id=1, note_id=1)
            assert result.get("success") is True


# ═══════════════════════════════════════════════════════════════════════════
# Release Task
# ═══════════════════════════════════════════════════════════════════════════
class TestReleaseTask:
    MOD = "freshservice_mcp.tools.releases"

    @pytest.fixture
    def tool(self):
        from freshservice_mcp.tools.releases import register_release_tools
        mcp = FastMCP("test")
        register_release_tools(mcp)
        return mcp._tool_manager._tools["manage_release_task"]

    @pytest.mark.asyncio
    async def test_list(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"tasks": []})
            result = await tool.fn(action="list", release_id=1)
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_get(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"task": {"id": 1}})
            result = await tool.fn(action="get", release_id=1, task_id=1)
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_create(self, tool):
        with patch(f"{self.MOD}.api_post", new_callable=AsyncMock) as m:
            m.return_value = _ok({"task": {"id": 1}}, 201)
            result = await tool.fn(action="create", release_id=1, title="Task 1", description="Do it")
            assert "task" in result or result.get("success")

    @pytest.mark.asyncio
    async def test_create_missing(self, tool):
        result = await tool.fn(action="create", release_id=1)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_update(self, tool):
        with patch(f"{self.MOD}.api_put", new_callable=AsyncMock) as m:
            m.return_value = _ok({"task": {"id": 1}})
            result = await tool.fn(action="update", release_id=1, task_id=1, title="Updated")
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_delete(self, tool):
        with patch(f"{self.MOD}.api_delete", new_callable=AsyncMock) as m:
            m.return_value = _no_content()
            result = await tool.fn(action="delete", release_id=1, task_id=1)
            assert result.get("success") is True


# ═══════════════════════════════════════════════════════════════════════════
# Release Time Entry
# ═══════════════════════════════════════════════════════════════════════════
class TestReleaseTimeEntry:
    MOD = "freshservice_mcp.tools.releases"

    @pytest.fixture
    def tool(self):
        from freshservice_mcp.tools.releases import register_release_tools
        mcp = FastMCP("test")
        register_release_tools(mcp)
        return mcp._tool_manager._tools["manage_release_time_entry"]

    @pytest.mark.asyncio
    async def test_list(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"time_entries": []})
            result = await tool.fn(action="list", release_id=1)
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_get(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"time_entry": {"id": 1}})
            result = await tool.fn(action="get", release_id=1, time_entry_id=1)
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_create(self, tool):
        with patch(f"{self.MOD}.api_post", new_callable=AsyncMock) as m:
            m.return_value = _ok({"time_entry": {"id": 1}}, 201)
            result = await tool.fn(action="create", release_id=1, agent_id=1, time_spent="01:00", note="Work")
            assert "time_entry" in result or result.get("success")

    @pytest.mark.asyncio
    async def test_update(self, tool):
        with patch(f"{self.MOD}.api_put", new_callable=AsyncMock) as m:
            m.return_value = _ok({"time_entry": {"id": 1}})
            result = await tool.fn(action="update", release_id=1, time_entry_id=1, time_spent="02:00")
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_delete(self, tool):
        with patch(f"{self.MOD}.api_delete", new_callable=AsyncMock) as m:
            m.return_value = _no_content()
            result = await tool.fn(action="delete", release_id=1, time_entry_id=1)
            assert result.get("success") is True


# ═══════════════════════════════════════════════════════════════════════════
# Location (departments module)
# ═══════════════════════════════════════════════════════════════════════════
class TestLocation:
    MOD = "freshservice_mcp.tools.departments"

    @pytest.fixture
    def tool(self):
        from freshservice_mcp.tools.departments import register_department_tools
        mcp = FastMCP("test")
        register_department_tools(mcp)
        return mcp._tool_manager._tools["manage_location"]

    @pytest.mark.asyncio
    async def test_list(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"locations": []})
            result = await tool.fn(action="list")
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_get(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"location": {"id": 1}})
            result = await tool.fn(action="get", location_id=1)
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_get_missing_id(self, tool):
        result = await tool.fn(action="get")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_create(self, tool):
        with patch(f"{self.MOD}.api_post", new_callable=AsyncMock) as m:
            m.return_value = _ok({"location": {"id": 1}}, 201)
            result = await tool.fn(action="create", name="HQ")
            assert "location" in result or result.get("success")

    @pytest.mark.asyncio
    async def test_create_missing(self, tool):
        result = await tool.fn(action="create")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_update(self, tool):
        with patch(f"{self.MOD}.api_put", new_callable=AsyncMock) as m:
            m.return_value = _ok({"location": {"id": 1}})
            result = await tool.fn(action="update", location_id=1, name="Updated HQ")
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_update_missing_id(self, tool):
        result = await tool.fn(action="update")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_delete(self, tool):
        with patch(f"{self.MOD}.api_delete", new_callable=AsyncMock) as m:
            m.return_value = _no_content()
            result = await tool.fn(action="delete", location_id=1)
            assert result.get("success") is True

    @pytest.mark.asyncio
    async def test_delete_missing_id(self, tool):
        result = await tool.fn(action="delete")
        assert "error" in result


# ═══════════════════════════════════════════════════════════════════════════
# Requester Group
# ═══════════════════════════════════════════════════════════════════════════
class TestRequesterGroup:
    MOD = "freshservice_mcp.tools.requesters"

    @pytest.fixture
    def tool(self):
        from freshservice_mcp.tools.requesters import register_requesters_tools
        mcp = FastMCP("test")
        register_requesters_tools(mcp)
        return mcp._tool_manager._tools["manage_requester_group"]

    @pytest.mark.asyncio
    async def test_list(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"requester_groups": []})
            result = await tool.fn(action="list")
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_get(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"requester_group": {"id": 1}})
            result = await tool.fn(action="get", group_id=1)
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_get_missing_id(self, tool):
        result = await tool.fn(action="get")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_create(self, tool):
        with patch(f"{self.MOD}.api_post", new_callable=AsyncMock) as m:
            m.return_value = _ok({"requester_group": {"id": 1}}, 201)
            result = await tool.fn(action="create", name="VIP")
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_create_missing(self, tool):
        result = await tool.fn(action="create")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_update(self, tool):
        with patch(f"{self.MOD}.api_put", new_callable=AsyncMock) as m:
            m.return_value = _ok({"requester_group": {"id": 1}})
            result = await tool.fn(action="update", group_id=1, name="Updated")
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_update_missing_id(self, tool):
        result = await tool.fn(action="update")
        assert "error" in result


# ═══════════════════════════════════════════════════════════════════════════
# Agent Group
# ═══════════════════════════════════════════════════════════════════════════
class TestAgentGroup:
    MOD = "freshservice_mcp.tools.agents"

    @pytest.fixture
    def tool(self):
        from freshservice_mcp.tools.agents import register_agents_tools
        mcp = FastMCP("test")
        register_agents_tools(mcp)
        return mcp._tool_manager._tools["manage_agent_group"]

    @pytest.mark.asyncio
    async def test_list(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"groups": []})
            result = await tool.fn(action="list")
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_get(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"group": {"id": 1}})
            result = await tool.fn(action="get", group_id=1)
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_get_missing_id(self, tool):
        result = await tool.fn(action="get")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_create(self, tool):
        with patch(f"{self.MOD}.api_post", new_callable=AsyncMock) as m:
            m.return_value = _ok({"group": {"id": 1}}, 201)
            result = await tool.fn(action="create", name="Support L2")
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_create_missing(self, tool):
        result = await tool.fn(action="create")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_update(self, tool):
        with patch(f"{self.MOD}.api_put", new_callable=AsyncMock) as m:
            m.return_value = _ok({"group": {"id": 1}})
            result = await tool.fn(action="update", group_id=1, name="Updated")
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_update_missing_id(self, tool):
        result = await tool.fn(action="update")
        assert "error" in result


# ═══════════════════════════════════════════════════════════════════════════
# Asset Details
# ═══════════════════════════════════════════════════════════════════════════
class TestAssetDetails:
    MOD = "freshservice_mcp.tools.assets"

    @pytest.fixture
    def tool(self):
        from freshservice_mcp.tools.assets import register_assets_tools
        mcp = FastMCP("test")
        register_assets_tools(mcp)
        return mcp._tool_manager._tools["manage_asset_details"]

    @pytest.mark.asyncio
    async def test_get_contracts(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"contracts": []})
            result = await tool.fn(action="contracts", display_id=1)
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_get_contracts_missing(self, tool):
        result = await tool.fn(action="invalid_action", display_id=1)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_get_requests(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"requests": []})
            result = await tool.fn(action="requests", display_id=1)
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_get_components(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"components": []})
            result = await tool.fn(action="components", display_id=1)
            assert "error" not in result


# ═══════════════════════════════════════════════════════════════════════════
# Asset Relationship
# ═══════════════════════════════════════════════════════════════════════════
class TestAssetRelationship:
    MOD = "freshservice_mcp.tools.assets"

    @pytest.fixture
    def tool(self):
        from freshservice_mcp.tools.assets import register_assets_tools
        mcp = FastMCP("test")
        register_assets_tools(mcp)
        return mcp._tool_manager._tools["manage_asset_relationship"]

    @pytest.mark.asyncio
    async def test_list(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"relationships": []})
            result = await tool.fn(action="list_for_asset", display_id=1)
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_list_missing_id(self, tool):
        result = await tool.fn(action="list_for_asset")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_create(self, tool):
        with patch(f"{self.MOD}.api_post", new_callable=AsyncMock) as m:
            m.return_value = _ok({"relationships": [{"id": 1}]}, 201)
            result = await tool.fn(action="create", relationships=[{"relationship_type_id": 1, "primary_id": 1, "secondary_id": 2, "secondary_type": "asset"}])
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_create_missing(self, tool):
        result = await tool.fn(action="create")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_delete(self, tool):
        with patch(f"{self.MOD}.api_delete", new_callable=AsyncMock) as m:
            m.return_value = _no_content()
            result = await tool.fn(action="delete", relationship_ids=[1, 2])
            assert result.get("success") is True

    @pytest.mark.asyncio
    async def test_delete_missing(self, tool):
        result = await tool.fn(action="delete")
        assert "error" in result
