"""Tests targeting except/error branches across all tool modules.

These tests trigger the `except Exception as e: return handle_error(...)` paths
that constitute the majority of remaining uncovered lines.

Pattern: mock the API call to raise Exception, verify error is returned.
"""
import json
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from mcp.server.fastmcp import FastMCP


def _ok(data, code=200, headers=None):
    r = MagicMock()
    r.status_code = code
    r.raise_for_status = MagicMock()
    r.json.return_value = data
    r.is_success = True
    r.text = json.dumps(data)
    r.headers = headers or {"Link": ""}
    return r


def _no_content():
    r = MagicMock()
    r.status_code = 204
    r.raise_for_status = MagicMock()
    return r


# ═══════════════════════════════════════════════════════════════════════════
# Projects — manage_project error paths
# ═══════════════════════════════════════════════════════════════════════════
class TestProjectErrors:
    @pytest.fixture
    def tool(self):
        from freshservice_mcp.tools.projects import register_project_tools
        mcp = FastMCP("test")
        register_project_tools(mcp)
        return mcp._tool_manager._tools["manage_project"]

    MOD = "freshservice_mcp.tools.projects"

    @pytest.mark.asyncio
    async def test_list_error(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.side_effect = Exception("timeout")
            result = await tool.fn(action="list")
            assert "error" in result

    @pytest.mark.asyncio
    async def test_get_error(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.side_effect = Exception("404")
            result = await tool.fn(action="get", project_id=1)
            assert "error" in result

    @pytest.mark.asyncio
    async def test_create_missing_type(self, tool):
        result = await tool.fn(action="create", name="X")
        assert "project_type" in result["error"]

    @pytest.mark.asyncio
    async def test_create_error(self, tool):
        with patch(f"{self.MOD}.api_post", new_callable=AsyncMock) as m:
            m.side_effect = Exception("500")
            result = await tool.fn(action="create", name="X", project_type=0)
            assert "error" in result

    @pytest.mark.asyncio
    async def test_update_error(self, tool):
        with patch(f"{self.MOD}.api_put", new_callable=AsyncMock) as m:
            m.side_effect = Exception("500")
            result = await tool.fn(action="update", project_id=1, name="Y")
            assert "error" in result

    @pytest.mark.asyncio
    async def test_delete_error(self, tool):
        with patch(f"{self.MOD}.api_delete", new_callable=AsyncMock) as m:
            m.side_effect = Exception("500")
            result = await tool.fn(action="delete", project_id=1)
            assert "error" in result

    @pytest.mark.asyncio
    async def test_archive_error(self, tool):
        with patch(f"{self.MOD}.api_post", new_callable=AsyncMock) as m:
            m.side_effect = Exception("500")
            result = await tool.fn(action="archive", project_id=1)
            assert "error" in result

    @pytest.mark.asyncio
    async def test_restore_error(self, tool):
        with patch(f"{self.MOD}.api_post", new_callable=AsyncMock) as m:
            m.side_effect = Exception("500")
            result = await tool.fn(action="restore", project_id=1)
            assert "error" in result

    @pytest.mark.asyncio
    async def test_get_fields_error(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.side_effect = Exception("500")
            result = await tool.fn(action="get_fields")
            assert "error" in result

    @pytest.mark.asyncio
    async def test_get_templates_error(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.side_effect = Exception("500")
            result = await tool.fn(action="get_templates")
            assert "error" in result

    @pytest.mark.asyncio
    async def test_add_members_error(self, tool):
        with patch(f"{self.MOD}.api_post", new_callable=AsyncMock) as m:
            m.side_effect = Exception("500")
            result = await tool.fn(
                action="add_members", project_id=1,
                members=[{"email": "x@co.com"}]
            )
            assert "error" in result

    @pytest.mark.asyncio
    async def test_get_memberships_error(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.side_effect = Exception("500")
            result = await tool.fn(action="get_memberships", project_id=1)
            assert "error" in result

    @pytest.mark.asyncio
    async def test_create_association_bad_module(self, tool):
        result = await tool.fn(
            action="create_association", project_id=1,
            module_name="invalid", ids=[1]
        )
        assert "error" in result

    @pytest.mark.asyncio
    async def test_create_association_error(self, tool):
        with patch(f"{self.MOD}.api_post", new_callable=AsyncMock) as m:
            m.side_effect = Exception("500")
            result = await tool.fn(
                action="create_association", project_id=1,
                module_name="tickets", ids=[1]
            )
            assert "error" in result

    @pytest.mark.asyncio
    async def test_get_associations_bad_module(self, tool):
        result = await tool.fn(
            action="get_associations", project_id=1,
            module_name="invalid"
        )
        assert "error" in result

    @pytest.mark.asyncio
    async def test_get_associations_error(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.side_effect = Exception("500")
            result = await tool.fn(
                action="get_associations", project_id=1,
                module_name="tickets"
            )
            assert "error" in result

    @pytest.mark.asyncio
    async def test_delete_association_bad_module(self, tool):
        result = await tool.fn(
            action="delete_association", project_id=1,
            module_name="invalid", association_id=1
        )
        assert "error" in result

    @pytest.mark.asyncio
    async def test_delete_association_error(self, tool):
        with patch(f"{self.MOD}.api_delete", new_callable=AsyncMock) as m:
            m.side_effect = Exception("500")
            result = await tool.fn(
                action="delete_association", project_id=1,
                module_name="tickets", association_id=1
            )
            assert "error" in result

    @pytest.mark.asyncio
    async def test_get_versions_error(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.side_effect = Exception("500")
            result = await tool.fn(action="get_versions", project_id=1)
            assert "error" in result

    @pytest.mark.asyncio
    async def test_get_sprints_error(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.side_effect = Exception("500")
            result = await tool.fn(action="get_sprints", project_id=1)
            assert "error" in result


# ═══════════════════════════════════════════════════════════════════════════
# Projects — manage_project_task error paths
# ═══════════════════════════════════════════════════════════════════════════
class TestProjectTaskErrors:
    @pytest.fixture
    def tool(self):
        from freshservice_mcp.tools.projects import register_project_tools
        mcp = FastMCP("test")
        register_project_tools(mcp)
        return mcp._tool_manager._tools["manage_project_task"]

    MOD = "freshservice_mcp.tools.projects"

    @pytest.mark.asyncio
    async def test_list_error(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(action="list", project_id=1)
            assert "error" in result

    @pytest.mark.asyncio
    async def test_filter_error(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(action="filter", project_id=1, query="status_id:1")
            assert "error" in result

    @pytest.mark.asyncio
    async def test_get_error(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(action="get", project_id=1, task_id=1)
            assert "error" in result

    @pytest.mark.asyncio
    async def test_create_missing_type(self, tool):
        result = await tool.fn(action="create", project_id=1, title="X")
        assert "type_id" in result["error"]

    @pytest.mark.asyncio
    async def test_create_error(self, tool):
        with patch(f"{self.MOD}.api_post", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(action="create", project_id=1, title="X", type_id=1)
            assert "error" in result

    @pytest.mark.asyncio
    async def test_update_no_fields(self, tool):
        result = await tool.fn(action="update", project_id=1, task_id=1)
        assert "No fields" in result["error"]

    @pytest.mark.asyncio
    async def test_update_error(self, tool):
        with patch(f"{self.MOD}.api_put", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(action="update", project_id=1, task_id=1, title="Y")
            assert "error" in result

    @pytest.mark.asyncio
    async def test_delete_error(self, tool):
        with patch(f"{self.MOD}.api_delete", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(action="delete", project_id=1, task_id=1)
            assert "error" in result

    @pytest.mark.asyncio
    async def test_get_task_types_error(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(action="get_task_types", project_id=1)
            assert "error" in result

    @pytest.mark.asyncio
    async def test_get_task_type_fields_error(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(action="get_task_type_fields", project_id=1, type_id=1)
            assert "error" in result

    @pytest.mark.asyncio
    async def test_get_task_statuses_error(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(action="get_task_statuses", project_id=1)
            assert "error" in result

    @pytest.mark.asyncio
    async def test_get_task_priorities_error(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(action="get_task_priorities", project_id=1)
            assert "error" in result

    @pytest.mark.asyncio
    async def test_create_note_error(self, tool):
        with patch(f"{self.MOD}.api_post", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(
                action="create_note", project_id=1, task_id=1, content="X"
            )
            assert "error" in result

    @pytest.mark.asyncio
    async def test_list_notes_error(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(action="list_notes", project_id=1, task_id=1)
            assert "error" in result

    @pytest.mark.asyncio
    async def test_update_note_missing_content(self, tool):
        result = await tool.fn(
            action="update_note", project_id=1, task_id=1, note_id=1
        )
        assert "content required" in result["error"]

    @pytest.mark.asyncio
    async def test_update_note_error(self, tool):
        with patch(f"{self.MOD}.api_put", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(
                action="update_note", project_id=1, task_id=1, note_id=1, content="X"
            )
            assert "error" in result

    @pytest.mark.asyncio
    async def test_delete_note_error(self, tool):
        with patch(f"{self.MOD}.api_delete", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(
                action="delete_note", project_id=1, task_id=1, note_id=1
            )
            assert "error" in result

    @pytest.mark.asyncio
    async def test_create_association_error(self, tool):
        with patch(f"{self.MOD}.api_post", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(
                action="create_association", project_id=1, task_id=1,
                module_name="tickets", ids=[1]
            )
            assert "error" in result

    @pytest.mark.asyncio
    async def test_get_associations_error(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(
                action="get_associations", project_id=1, task_id=1,
                module_name="tickets"
            )
            assert "error" in result

    @pytest.mark.asyncio
    async def test_delete_association_error(self, tool):
        with patch(f"{self.MOD}.api_delete", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(
                action="delete_association", project_id=1, task_id=1,
                module_name="tickets", association_id=1
            )
            assert "error" in result


# ═══════════════════════════════════════════════════════════════════════════
# Releases — error paths (manage_release + sub-tools)
# ═══════════════════════════════════════════════════════════════════════════
class TestReleaseErrors:
    @pytest.fixture
    def tools(self):
        from freshservice_mcp.tools.releases import register_release_tools
        mcp = FastMCP("test")
        register_release_tools(mcp)
        return mcp._tool_manager._tools

    MOD = "freshservice_mcp.tools.releases"

    @pytest.mark.asyncio
    async def test_manage_release_list_error(self, tools):
        tool = tools["manage_release"]
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(action="list")
            assert "error" in result

    @pytest.mark.asyncio
    async def test_manage_release_get_error(self, tools):
        tool = tools["manage_release"]
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(action="get", release_id=1)
            assert "error" in result

    @pytest.mark.asyncio
    async def test_manage_release_create_error(self, tools):
        tool = tools["manage_release"]
        with patch(f"{self.MOD}.api_post", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(
                action="create", subject="X", release_type=1,
                priority=1, planned_start_date="2026-01-01",
                planned_end_date="2026-01-02"
            )
            assert "error" in result

    @pytest.mark.asyncio
    async def test_manage_release_update_error(self, tools):
        tool = tools["manage_release"]
        with patch(f"{self.MOD}.api_put", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(action="update", release_id=1, subject="Y")
            assert "error" in result

    @pytest.mark.asyncio
    async def test_manage_release_delete_error(self, tools):
        tool = tools["manage_release"]
        with patch(f"{self.MOD}.api_delete", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(action="delete", release_id=1)
            assert "error" in result

    @pytest.mark.asyncio
    async def test_manage_release_restore_error(self, tools):
        tool = tools["manage_release"]
        with patch(f"{self.MOD}.api_put", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(action="restore", release_id=1)
            assert "error" in result

    @pytest.mark.asyncio
    async def test_release_task_list_error(self, tools):
        tool = tools["manage_release_task"]
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(action="list", release_id=1)
            assert "error" in result

    @pytest.mark.asyncio
    async def test_release_task_get_error(self, tools):
        tool = tools["manage_release_task"]
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(action="get", release_id=1, task_id=1)
            assert "error" in result

    @pytest.mark.asyncio
    async def test_release_task_create_error(self, tools):
        tool = tools["manage_release_task"]
        with patch(f"{self.MOD}.api_post", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(action="create", release_id=1, title="X")
            assert "error" in result

    @pytest.mark.asyncio
    async def test_release_task_update_error(self, tools):
        tool = tools["manage_release_task"]
        with patch(f"{self.MOD}.api_put", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(action="update", release_id=1, task_id=1, title="Y")
            assert "error" in result

    @pytest.mark.asyncio
    async def test_release_task_delete_error(self, tools):
        tool = tools["manage_release_task"]
        with patch(f"{self.MOD}.api_delete", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(action="delete", release_id=1, task_id=1)
            assert "error" in result

    @pytest.mark.asyncio
    async def test_release_time_entry_list_error(self, tools):
        tool = tools["manage_release_time_entry"]
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(action="list", release_id=1)
            assert "error" in result

    @pytest.mark.asyncio
    async def test_release_time_entry_get_error(self, tools):
        tool = tools["manage_release_time_entry"]
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(action="get", release_id=1, time_entry_id=1)
            assert "error" in result

    @pytest.mark.asyncio
    async def test_release_time_entry_create_error(self, tools):
        tool = tools["manage_release_time_entry"]
        with patch(f"{self.MOD}.api_post", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(
                action="create", release_id=1,
                time_spent="01:00", agent_id=1,
                executed_at="2026-01-01T10:00:00Z", note="W"
            )
            assert "error" in result

    @pytest.mark.asyncio
    async def test_release_time_entry_update_error(self, tools):
        tool = tools["manage_release_time_entry"]
        with patch(f"{self.MOD}.api_put", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(
                action="update", release_id=1, time_entry_id=1, note="X"
            )
            assert "error" in result

    @pytest.mark.asyncio
    async def test_release_time_entry_delete_error(self, tools):
        tool = tools["manage_release_time_entry"]
        with patch(f"{self.MOD}.api_delete", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(action="delete", release_id=1, time_entry_id=1)
            assert "error" in result


# ═══════════════════════════════════════════════════════════════════════════
# Agents — manage_agent error paths
# ═══════════════════════════════════════════════════════════════════════════
class TestAgentErrors:
    @pytest.fixture
    def tools(self):
        from freshservice_mcp.tools.agents import register_agents_tools
        mcp = FastMCP("test")
        register_agents_tools(mcp)
        return mcp._tool_manager._tools

    MOD = "freshservice_mcp.tools.agents"

    @pytest.mark.asyncio
    async def test_list_error(self, tools):
        tool = tools["manage_agent"]
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(action="list")
            assert "error" in result

    @pytest.mark.asyncio
    async def test_get_error(self, tools):
        tool = tools["manage_agent"]
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(action="get", agent_id=1)
            assert "error" in result

    @pytest.mark.asyncio
    async def test_filter_error(self, tools):
        tool = tools["manage_agent"]
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(action="filter", query="email:'x@y.com'")
            assert "error" in result

    @pytest.mark.asyncio
    async def test_create_error(self, tools):
        tool = tools["manage_agent"]
        with patch(f"{self.MOD}.api_post", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(action="create", email="x@y.com")
            assert "error" in result

    @pytest.mark.asyncio
    async def test_update_error(self, tools):
        tool = tools["manage_agent"]
        with patch(f"{self.MOD}.api_put", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(
                action="update", agent_id=1,
                first_name="X"
            )
            assert "error" in result

    @pytest.mark.asyncio
    async def test_get_fields_error(self, tools):
        tool = tools["manage_agent"]
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(action="get_fields")
            assert "error" in result

    @pytest.mark.asyncio
    async def test_group_list_error(self, tools):
        tool = tools["manage_agent_group"]
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(action="list")
            assert "error" in result

    @pytest.mark.asyncio
    async def test_group_get_error(self, tools):
        tool = tools["manage_agent_group"]
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(action="get", group_id=1)
            assert "error" in result

    @pytest.mark.asyncio
    async def test_group_create_error(self, tools):
        tool = tools["manage_agent_group"]
        with patch(f"{self.MOD}.api_post", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(action="create", name="TestGroup")
            assert "error" in result


# ═══════════════════════════════════════════════════════════════════════════
# Assets — manage_asset error paths
# ═══════════════════════════════════════════════════════════════════════════
class TestAssetErrors:
    @pytest.fixture
    def tool(self):
        from freshservice_mcp.tools.assets import register_assets_tools
        mcp = FastMCP("test")
        register_assets_tools(mcp)
        return mcp._tool_manager._tools["manage_asset"]

    MOD = "freshservice_mcp.tools.assets"

    @pytest.mark.asyncio
    async def test_list_error(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(action="list")
            assert "error" in result

    @pytest.mark.asyncio
    async def test_get_error(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(action="get", display_id=1)
            assert "error" in result

    @pytest.mark.asyncio
    async def test_filter_error(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(action="filter", filter_query="asset_type_id:1")
            assert "error" in result

    @pytest.mark.asyncio
    async def test_create_error(self, tool):
        with patch(f"{self.MOD}.api_post", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(
                action="create", name="X", asset_type_id=1
            )
            assert "error" in result

    @pytest.mark.asyncio
    async def test_update_error(self, tool):
        with patch(f"{self.MOD}.api_put", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(
                action="update", display_id=1,
                asset_fields={"name": "Y"}
            )
            assert "error" in result

    @pytest.mark.asyncio
    async def test_delete_error(self, tool):
        with patch(f"{self.MOD}.api_delete", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(action="delete", display_id=1)
            assert "error" in result

    @pytest.mark.asyncio
    async def test_restore_error(self, tool):
        with patch(f"{self.MOD}.api_put", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(action="restore", display_id=1)
            assert "error" in result

    @pytest.mark.asyncio
    async def test_get_fields_error(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(action="get_fields")
            assert "error" in result

    @pytest.mark.asyncio
    async def test_get_types_error(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(action="get_types")
            assert "error" in result

    @pytest.mark.asyncio
    async def test_search_error(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(action="search", search_query="server")
            assert "error" in result


# ═══════════════════════════════════════════════════════════════════════════
# Changes — error paths (sub-tools except blocks)
# ═══════════════════════════════════════════════════════════════════════════
class TestChangeErrors:
    @pytest.fixture
    def tools(self):
        from freshservice_mcp.tools.changes import register_changes_tools
        mcp = FastMCP("test")
        register_changes_tools(mcp)
        return mcp._tool_manager._tools

    MOD = "freshservice_mcp.tools.changes"

    @pytest.mark.asyncio
    async def test_task_view_error(self, tools):
        tool = tools["manage_change_task"]
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(action="view", change_id=1, task_id=1)
            assert "error" in result

    @pytest.mark.asyncio
    async def test_task_update_error(self, tools):
        tool = tools["manage_change_task"]
        with patch(f"{self.MOD}.api_put", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(
                action="update", change_id=1, task_id=1,
                task_fields={"status": 3}
            )
            assert "error" in result

    @pytest.mark.asyncio
    async def test_task_delete_error(self, tools):
        tool = tools["manage_change_task"]
        with patch(f"{self.MOD}.api_delete", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(action="delete", change_id=1, task_id=1)
            assert "error" in result

    @pytest.mark.asyncio
    async def test_time_entry_view_error(self, tools):
        tool = tools["manage_change_time_entry"]
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(action="view", change_id=1, time_entry_id=1)
            assert "error" in result

    @pytest.mark.asyncio
    async def test_time_entry_create_error(self, tools):
        tool = tools["manage_change_time_entry"]
        with patch(f"{self.MOD}.api_post", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(
                action="create", change_id=1,
                time_spent="01:00", note="W", te_agent_id=1
            )
            assert "error" in result

    @pytest.mark.asyncio
    async def test_time_entry_update_error(self, tools):
        tool = tools["manage_change_time_entry"]
        with patch(f"{self.MOD}.api_put", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(
                action="update", change_id=1, time_entry_id=1, note="X"
            )
            assert "error" in result

    @pytest.mark.asyncio
    async def test_time_entry_delete_error(self, tools):
        tool = tools["manage_change_time_entry"]
        with patch(f"{self.MOD}.api_delete", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(action="delete", change_id=1, time_entry_id=1)
            assert "error" in result

    @pytest.mark.asyncio
    async def test_approval_list_groups_error(self, tools):
        tool = tools["manage_change_approval"]
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(action="list_groups", change_id=1)
            assert "error" in result

    @pytest.mark.asyncio
    async def test_approval_create_group_error(self, tools):
        tool = tools["manage_change_approval"]
        with patch(f"{self.MOD}.api_post", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(
                action="create_group", change_id=1,
                name="CAB", approver_ids=[1]
            )
            assert "error" in result

    @pytest.mark.asyncio
    async def test_approval_list_error(self, tools):
        tool = tools["manage_change_approval"]
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(action="list", change_id=1)
            assert "error" in result

    @pytest.mark.asyncio
    async def test_approval_view_error(self, tools):
        tool = tools["manage_change_approval"]
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(action="view", change_id=1, approval_id=1)
            assert "error" in result


# ═══════════════════════════════════════════════════════════════════════════
# Departments — error paths
# ═══════════════════════════════════════════════════════════════════════════
class TestDepartmentErrors:
    @pytest.fixture
    def tool(self):
        from freshservice_mcp.tools.departments import register_department_tools
        mcp = FastMCP("test")
        register_department_tools(mcp)
        return mcp._tool_manager._tools["manage_department"]

    MOD = "freshservice_mcp.tools.departments"

    @pytest.mark.asyncio
    async def test_get_error(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(action="get", department_id=1)
            assert "error" in result

    @pytest.mark.asyncio
    async def test_get_fields_error(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(action="get_fields")
            assert "error" in result

    @pytest.mark.asyncio
    async def test_filter_error(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(action="filter", query="name:'IT'")
            assert "error" in result


# ═══════════════════════════════════════════════════════════════════════════
# Problems — error paths
# ═══════════════════════════════════════════════════════════════════════════
class TestProblemErrors:
    @pytest.fixture
    def tool(self):
        from freshservice_mcp.tools.problems import register_problem_tools
        mcp = FastMCP("test")
        register_problem_tools(mcp)
        return mcp._tool_manager._tools["manage_problem"]

    MOD = "freshservice_mcp.tools.problems"

    @pytest.mark.asyncio
    async def test_create_error(self, tool):
        with patch(f"{self.MOD}.api_post", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(
                action="create", subject="X", requester_id=1,
                description="desc", priority=1, status=1, impact=1
            )
            assert "error" in result

    @pytest.mark.asyncio
    async def test_update_error(self, tool):
        with patch(f"{self.MOD}.api_put", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(action="update", problem_id=1, subject="Y")
            assert "error" in result

    @pytest.mark.asyncio
    async def test_delete_error(self, tool):
        with patch(f"{self.MOD}.api_delete", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(action="delete", problem_id=1)
            assert "error" in result

    @pytest.mark.asyncio
    async def test_task_error(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(action="list_tasks", problem_id=1)
            assert "error" in result

    @pytest.mark.asyncio
    async def test_note_error(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(action="list_notes", problem_id=1)
            assert "error" in result

    @pytest.mark.asyncio
    async def test_time_entry_error(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(action="list_time_entries", problem_id=1)
            assert "error" in result


# ═══════════════════════════════════════════════════════════════════════════
# Status Page — error paths for actions in manage_status_page
# ═══════════════════════════════════════════════════════════════════════════
class TestStatusPageErrors:
    @pytest.fixture
    def tool(self):
        from freshservice_mcp.tools.status_page import register_status_page_tools
        mcp = FastMCP("test")
        register_status_page_tools(mcp)
        return mcp._tool_manager._tools["manage_status_page"]

    MOD = "freshservice_mcp.tools.status_page"

    @pytest.mark.asyncio
    async def test_list_components_error(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(action="list_components", status_page_id=1)
            assert "error" in result

    @pytest.mark.asyncio
    async def test_get_component_error(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(
                action="get_component", status_page_id=1, component_id=1
            )
            assert "error" in result

    @pytest.mark.asyncio
    async def test_list_maintenance_error(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(action="list_maintenance", status_page_id=1)
            assert "error" in result

    @pytest.mark.asyncio
    async def test_create_maintenance_error(self, tool):
        with patch(f"{self.MOD}.api_post", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(
                action="create_maintenance", status_page_id=1,
                title="MW", description="Desc",
                started_at="2026-01-01T00:00:00Z",
                ended_at="2026-01-01T04:00:00Z",
                change_id=1,
                impacted_services=[{"id": 1, "status": 5}]
            )
            assert "error" in result

    @pytest.mark.asyncio
    async def test_get_maintenance_error(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(
                action="get_maintenance", status_page_id=1,
                change_id=1, maintenance_id=1
            )
            assert "error" in result

    @pytest.mark.asyncio
    async def test_update_maintenance_error(self, tool):
        with patch(f"{self.MOD}.api_put", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(
                action="update_maintenance", status_page_id=1,
                change_id=1, maintenance_id=1, title="Y"
            )
            assert "error" in result

    @pytest.mark.asyncio
    async def test_delete_maintenance_error(self, tool):
        with patch(f"{self.MOD}.api_delete", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(
                action="delete_maintenance", status_page_id=1,
                change_id=1, maintenance_id=1
            )
            assert "error" in result

    @pytest.mark.asyncio
    async def test_list_incidents_error(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(action="list_incidents", status_page_id=1)
            assert "error" in result

    @pytest.mark.asyncio
    async def test_create_incident_error(self, tool):
        with patch(f"{self.MOD}.api_post", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(
                action="create_incident", status_page_id=1,
                title="Outage", description="Desc",
                ticket_id=1,
                impacted_services=[{"id": 1, "status": 30}]
            )
            assert "error" in result

    @pytest.mark.asyncio
    async def test_get_incident_error(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(
                action="get_incident", status_page_id=1,
                ticket_id=1, incident_id=1
            )
            assert "error" in result

    @pytest.mark.asyncio
    async def test_update_incident_error(self, tool):
        with patch(f"{self.MOD}.api_put", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(
                action="update_incident", status_page_id=1,
                ticket_id=1, incident_id=1, title="Y"
            )
            assert "error" in result

    @pytest.mark.asyncio
    async def test_delete_incident_error(self, tool):
        with patch(f"{self.MOD}.api_delete", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(
                action="delete_incident", status_page_id=1,
                ticket_id=1, incident_id=1
            )
            assert "error" in result

    @pytest.mark.asyncio
    async def test_create_maintenance_update_error(self, tool):
        with patch(f"{self.MOD}.api_post", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(
                action="create_maintenance_update", status_page_id=1,
                change_id=1, maintenance_id=1, body="Update note"
            )
            assert "error" in result

    @pytest.mark.asyncio
    async def test_list_maintenance_updates_error(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(
                action="list_maintenance_updates", status_page_id=1,
                change_id=1, maintenance_id=1
            )
            assert "error" in result

    @pytest.mark.asyncio
    async def test_update_maintenance_update_error(self, tool):
        with patch(f"{self.MOD}.api_put", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(
                action="update_maintenance_update", status_page_id=1,
                change_id=1, maintenance_id=1, update_id=1, body="Updated"
            )
            assert "error" in result

    @pytest.mark.asyncio
    async def test_delete_maintenance_update_error(self, tool):
        with patch(f"{self.MOD}.api_delete", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(
                action="delete_maintenance_update", status_page_id=1,
                change_id=1, maintenance_id=1, update_id=1
            )
            assert "error" in result

    @pytest.mark.asyncio
    async def test_create_incident_update_error(self, tool):
        with patch(f"{self.MOD}.api_post", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(
                action="create_incident_update", status_page_id=1,
                ticket_id=1, incident_id=1, body="Update"
            )
            assert "error" in result

    @pytest.mark.asyncio
    async def test_list_incident_updates_error(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(
                action="list_incident_updates", status_page_id=1,
                ticket_id=1, incident_id=1
            )
            assert "error" in result

    @pytest.mark.asyncio
    async def test_update_incident_update_error(self, tool):
        with patch(f"{self.MOD}.api_put", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(
                action="update_incident_update", status_page_id=1,
                ticket_id=1, incident_id=1, update_id=1, body="Updated"
            )
            assert "error" in result

    @pytest.mark.asyncio
    async def test_delete_incident_update_error(self, tool):
        with patch(f"{self.MOD}.api_delete", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(
                action="delete_incident_update", status_page_id=1,
                ticket_id=1, incident_id=1, update_id=1
            )
            assert "error" in result

    @pytest.mark.asyncio
    async def test_list_subscribers_error(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(action="list_subscribers", status_page_id=1)
            assert "error" in result

    @pytest.mark.asyncio
    async def test_get_subscriber_error(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(
                action="get_subscriber", status_page_id=1, subscriber_id=1
            )
            assert "error" in result

    @pytest.mark.asyncio
    async def test_create_subscriber_error(self, tool):
        with patch(f"{self.MOD}.api_post", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(
                action="create_subscriber", status_page_id=1,
                email="user@co.com"
            )
            assert "error" in result

    @pytest.mark.asyncio
    async def test_update_subscriber_error(self, tool):
        with patch(f"{self.MOD}.api_put", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(
                action="update_subscriber", status_page_id=1,
                subscriber_id=1, email="x@y.com"
            )
            assert "error" in result

    @pytest.mark.asyncio
    async def test_delete_subscriber_error(self, tool):
        with patch(f"{self.MOD}.api_delete", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(
                action="delete_subscriber", status_page_id=1, subscriber_id=1
            )
            assert "error" in result


# ═══════════════════════════════════════════════════════════════════════════
# Tickets — service catalog error paths
# ═══════════════════════════════════════════════════════════════════════════
class TestTicketErrors:
    @pytest.fixture
    def tools(self):
        from freshservice_mcp.tools.tickets import register_tickets_tools
        mcp = FastMCP("test")
        register_tickets_tools(mcp)
        return mcp._tool_manager._tools

    MOD = "freshservice_mcp.tools.tickets"

    @pytest.mark.asyncio
    async def test_catalog_list_error(self, tools):
        tool = tools["manage_service_catalog"]
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(action="list_items")
            assert "error" in result

    @pytest.mark.asyncio
    async def test_catalog_place_request_error(self, tools):
        tool = tools["manage_service_catalog"]
        with patch(f"{self.MOD}.api_post", new_callable=AsyncMock) as m:
            m.side_effect = Exception("err")
            result = await tool.fn(
                action="place_request", display_id=1, email="x@y.com"
            )
            assert "error" in result
