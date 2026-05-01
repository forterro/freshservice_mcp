"""Additional tests for releases, assets, misc, tickets, departments tools."""
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
# Releases — comprehensive coverage
# ═══════════════════════════════════════════════════════════════════════════
class TestReleasesComprehensive:
    @pytest.fixture
    def tool(self):
        from freshservice_mcp.tools.releases import register_release_tools
        mcp = FastMCP("test")
        register_release_tools(mcp)
        return mcp._tool_manager._tools["manage_release"]

    MOD = "freshservice_mcp.tools.releases"

    @pytest.mark.asyncio
    async def test_list(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"releases": [{"id": 1}]})
            result = await tool.fn(action="list")
            assert "releases" in result or "error" not in result

    @pytest.mark.asyncio
    async def test_get(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"release": {"id": 1}})
            result = await tool.fn(action="get", release_id=1)
            assert "release" in result or "error" not in result

    @pytest.mark.asyncio
    async def test_get_missing_id(self, tool):
        result = await tool.fn(action="get")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_create(self, tool):
        with patch(f"{self.MOD}.api_post", new_callable=AsyncMock) as m:
            m.return_value = _ok({"release": {"id": 1}}, 201)
            result = await tool.fn(
                action="create", subject="Release 2.0",
                description="Major", release_type=1,
                priority=2, status=1,
                planned_start_date="2026-06-01",
                planned_end_date="2026-06-15"
            )
            assert "release" in result or result.get("success")

    @pytest.mark.asyncio
    async def test_create_missing_fields(self, tool):
        result = await tool.fn(action="create")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_update(self, tool):
        with patch(f"{self.MOD}.api_put", new_callable=AsyncMock) as m:
            m.return_value = _ok({"release": {"id": 1}})
            result = await tool.fn(action="update", release_id=1, subject="Updated")
            assert "release" in result or "error" not in result

    @pytest.mark.asyncio
    async def test_update_missing_id(self, tool):
        result = await tool.fn(action="update")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_delete(self, tool):
        with patch(f"{self.MOD}.api_delete", new_callable=AsyncMock) as m:
            m.return_value = _no_content()
            result = await tool.fn(action="delete", release_id=1)
            assert result.get("success") is True

    @pytest.mark.asyncio
    async def test_delete_missing_id(self, tool):
        result = await tool.fn(action="delete")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_unknown_action(self, tool):
        result = await tool.fn(action="invalid")
        assert "error" in result


# ═══════════════════════════════════════════════════════════════════════════
# Assets — comprehensive coverage
# ═══════════════════════════════════════════════════════════════════════════
class TestAssetsComprehensive:
    @pytest.fixture
    def tool(self):
        from freshservice_mcp.tools.assets import register_assets_tools
        mcp = FastMCP("test")
        register_assets_tools(mcp)
        return mcp._tool_manager._tools["manage_asset"]

    MOD = "freshservice_mcp.tools.assets"

    @pytest.mark.asyncio
    async def test_list(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"assets": [{"id": 1}]})
            result = await tool.fn(action="list")
            assert "assets" in result or "error" not in result

    @pytest.mark.asyncio
    async def test_get(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"asset": {"id": 1}})
            result = await tool.fn(action="get", display_id=1)
            assert "asset" in result or "error" not in result

    @pytest.mark.asyncio
    async def test_get_missing_id(self, tool):
        result = await tool.fn(action="get")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_create(self, tool):
        with patch(f"{self.MOD}.api_post", new_callable=AsyncMock) as m:
            m.return_value = _ok({"asset": {"id": 1}}, 201)
            result = await tool.fn(action="create", name="Laptop-001", asset_type_id=1)
            assert "asset" in result or result.get("success")

    @pytest.mark.asyncio
    async def test_create_missing_fields(self, tool):
        result = await tool.fn(action="create")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_update(self, tool):
        with patch(f"{self.MOD}.api_put", new_callable=AsyncMock) as m:
            m.return_value = _ok({"asset": {"id": 1}})
            result = await tool.fn(action="update", display_id=1, name="Updated-Laptop")
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_update_missing_id(self, tool):
        result = await tool.fn(action="update")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_delete(self, tool):
        with patch(f"{self.MOD}.api_delete", new_callable=AsyncMock) as m:
            m.return_value = _no_content()
            result = await tool.fn(action="delete", display_id=1)
            assert result.get("success") is True

    @pytest.mark.asyncio
    async def test_delete_missing_id(self, tool):
        result = await tool.fn(action="delete")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_search(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"assets": []})
            result = await tool.fn(action="search", search_query="laptop")
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_filter(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"assets": []})
            result = await tool.fn(action="filter", filter_query='"asset_type_id:1"')
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_get_types(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"asset_types": []})
            result = await tool.fn(action="get_types")
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_unknown_action(self, tool):
        result = await tool.fn(action="invalid")
        assert "error" in result


# ═══════════════════════════════════════════════════════════════════════════
# Misc tools
# ═══════════════════════════════════════════════════════════════════════════
class TestMiscTools:
    @pytest.fixture
    def mcp_tools(self):
        from freshservice_mcp.tools.misc import register_misc_tools
        mcp = FastMCP("test")
        register_misc_tools(mcp)
        return mcp._tool_manager._tools

    MOD = "freshservice_mcp.tools.misc"

    @pytest.mark.asyncio
    async def test_workspace_list(self, mcp_tools):
        tool = mcp_tools["manage_workspace"]
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"workspaces": [{"id": 1}]})
            result = await tool.fn(action="list")
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_workspace_get(self, mcp_tools):
        tool = mcp_tools["manage_workspace"]
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"workspace": {"id": 1}})
            result = await tool.fn(action="get", workspace_id=1)
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_workspace_get_missing(self, mcp_tools):
        tool = mcp_tools["manage_workspace"]
        result = await tool.fn(action="get")
        assert "error" in result


# ═══════════════════════════════════════════════════════════════════════════
# Tickets — conversation tool
# ═══════════════════════════════════════════════════════════════════════════
class TestTicketsConversation:
    @pytest.fixture
    def tool(self):
        from freshservice_mcp.tools.tickets import register_tickets_tools
        mcp = FastMCP("test")
        register_tickets_tools(mcp)
        return mcp._tool_manager._tools["manage_ticket_conversation"]

    MOD = "freshservice_mcp.tools.tickets"

    @pytest.mark.asyncio
    async def test_list(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"conversations": []})
            result = await tool.fn(action="list", ticket_id=1)
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_list_missing_id(self, tool):
        result = await tool.fn(action="list")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_reply(self, tool):
        with patch(f"{self.MOD}.api_post", new_callable=AsyncMock) as m:
            m.return_value = _ok({"conversation": {"id": 1}}, 201)
            result = await tool.fn(action="reply", ticket_id=1, body="Reply text")
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_reply_missing_body(self, tool):
        result = await tool.fn(action="reply", ticket_id=1)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_add_note(self, tool):
        with patch(f"{self.MOD}.api_post", new_callable=AsyncMock) as m:
            m.return_value = _ok({"conversation": {"id": 1}}, 201)
            result = await tool.fn(action="add_note", ticket_id=1, body="Note text")
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_add_note_missing(self, tool):
        result = await tool.fn(action="add_note", ticket_id=1)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_update(self, tool):
        with patch(f"{self.MOD}.api_put", new_callable=AsyncMock) as m:
            m.return_value = _ok({"conversation": {"id": 1}})
            result = await tool.fn(action="update", conversation_id=1, body="Updated")
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_update_missing(self, tool):
        result = await tool.fn(action="update")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_unknown_action(self, tool):
        result = await tool.fn(action="invalid")
        assert "error" in result


# ═══════════════════════════════════════════════════════════════════════════
# Departments — deeper actions
# ═══════════════════════════════════════════════════════════════════════════
class TestDepartmentsComprehensive:
    @pytest.fixture
    def tool(self):
        from freshservice_mcp.tools.departments import register_department_tools
        mcp = FastMCP("test")
        register_department_tools(mcp)
        return mcp._tool_manager._tools["manage_department"]

    MOD = "freshservice_mcp.tools.departments"

    @pytest.mark.asyncio
    async def test_list(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"departments": [{"id": 1}]})
            result = await tool.fn(action="list")
            assert "departments" in result or "error" not in result

    @pytest.mark.asyncio
    async def test_get(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"department": {"id": 1}})
            result = await tool.fn(action="get", department_id=1)
            assert "department" in result or "error" not in result

    @pytest.mark.asyncio
    async def test_get_missing_id(self, tool):
        result = await tool.fn(action="get")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_get_fields(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"department_fields": []})
            result = await tool.fn(action="get_fields")
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_unknown_action(self, tool):
        result = await tool.fn(action="invalid")
        assert "error" in result
