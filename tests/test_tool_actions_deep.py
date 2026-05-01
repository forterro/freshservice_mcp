"""Additional action tests for deeper tool coverage."""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from mcp.server.fastmcp import FastMCP


def _mcp_with_tool(register_func):
    mcp = FastMCP("test")
    register_func(mcp)
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


# ═══════════════════════════════════════════════════════════════════════════
# Tickets — deeper coverage
# ═══════════════════════════════════════════════════════════════════════════
class TestTicketsDeep:
    @pytest.fixture
    def tool(self):
        from freshservice_mcp.tools.tickets import register_tickets_tools
        mcp = _mcp_with_tool(register_tickets_tools)
        return mcp._tool_manager._tools["manage_ticket"]

    @pytest.fixture
    def conv_tool(self):
        from freshservice_mcp.tools.tickets import register_tickets_tools
        mcp = _mcp_with_tool(register_tickets_tools)
        return mcp._tool_manager._tools["manage_ticket_conversation"]

    @pytest.mark.asyncio
    async def test_create_note(self, conv_tool):
        with patch("freshservice_mcp.tools.tickets.api_post", new_callable=AsyncMock) as m:
            m.return_value = _ok({"conversation": {"id": 1}}, 201)
            result = await conv_tool.fn(action="add_note", ticket_id=42, body="Internal note")
            assert result.get("success") or "conversation" in result or "note" in str(result)

    @pytest.mark.asyncio
    async def test_reply(self, conv_tool):
        with patch("freshservice_mcp.tools.tickets.api_post", new_callable=AsyncMock) as m:
            m.return_value = _ok({"conversation": {"id": 1}}, 201)
            result = await conv_tool.fn(action="reply", ticket_id=42, body="Thanks for contacting us")
            assert result.get("success") or "conversation" in result or "reply" in str(result)

    @pytest.mark.asyncio
    async def test_update_missing_id(self, tool):
        result = await tool.fn(action="update")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_delete_missing_id(self, tool):
        result = await tool.fn(action="delete")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_filter(self, tool):
        with patch("freshservice_mcp.tools.tickets.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"tickets": []})
            result = await tool.fn(action="filter", query='"status:2"')
            assert "tickets" in result or "error" not in result


# ═══════════════════════════════════════════════════════════════════════════
# Changes — deeper coverage
# ═══════════════════════════════════════════════════════════════════════════
class TestChangesDeep:
    @pytest.fixture
    def tool(self):
        from freshservice_mcp.tools.changes import register_changes_tools
        mcp = _mcp_with_tool(register_changes_tools)
        return mcp._tool_manager._tools["manage_change"]

    @pytest.mark.asyncio
    async def test_update(self, tool):
        with patch("freshservice_mcp.tools.changes.api_put", new_callable=AsyncMock) as m:
            m.return_value = _ok({"change": {"id": 10, "status": 2}})
            result = await tool.fn(action="update", change_id=10, status=2)
            assert result.get("success") or "change" in result

    @pytest.mark.asyncio
    async def test_update_missing_id(self, tool):
        result = await tool.fn(action="update")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_delete_missing_id(self, tool):
        result = await tool.fn(action="delete")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_add_note(self, tool):
        from freshservice_mcp.tools.changes import register_changes_tools
        mcp = _mcp_with_tool(register_changes_tools)
        note_tool = mcp._tool_manager._tools["manage_change_note"]
        with patch("freshservice_mcp.tools.changes.api_post", new_callable=AsyncMock) as m:
            m.return_value = _ok({"note": {"id": 1}}, 201)
            result = await note_tool.fn(action="create", change_id=10, body="Note text")
            assert result.get("success") or "note" in result or "error" not in result


# ═══════════════════════════════════════════════════════════════════════════
# Assets — deeper coverage
# ═══════════════════════════════════════════════════════════════════════════
class TestAssetsDeep:
    @pytest.fixture
    def tool(self):
        from freshservice_mcp.tools.assets import register_assets_tools
        mcp = _mcp_with_tool(register_assets_tools)
        return mcp._tool_manager._tools["manage_asset"]

    @pytest.mark.asyncio
    async def test_update(self, tool):
        with patch("freshservice_mcp.tools.assets.api_put", new_callable=AsyncMock) as m:
            m.return_value = _ok({"asset": {"id": 5}})
            result = await tool.fn(action="update", display_id=5, name="Updated-Laptop")
            assert result.get("success") or "asset" in result

    @pytest.mark.asyncio
    async def test_update_missing_id(self, tool):
        result = await tool.fn(action="update")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_filter(self, tool):
        with patch("freshservice_mcp.tools.assets.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"assets": []})
            result = await tool.fn(action="filter", filter_query='"asset_type_id:1"')
            assert "assets" in result or "error" not in result

    @pytest.mark.asyncio
    async def test_delete_missing_id(self, tool):
        result = await tool.fn(action="delete")
        assert "error" in result


# ═══════════════════════════════════════════════════════════════════════════
# Agents — deeper coverage
# ═══════════════════════════════════════════════════════════════════════════
class TestAgentsDeep:
    @pytest.fixture
    def tool(self):
        from freshservice_mcp.tools.agents import register_agents_tools
        mcp = _mcp_with_tool(register_agents_tools)
        return mcp._tool_manager._tools["manage_agent"]

    @pytest.mark.asyncio
    async def test_create(self, tool):
        with patch("freshservice_mcp.tools.agents.api_post", new_callable=AsyncMock) as m:
            m.return_value = _ok({"agent": {"id": 1}}, 201)
            result = await tool.fn(action="create", first_name="Test", email="agent@test.com")
            assert result.get("success") or "agent" in result

    @pytest.mark.asyncio
    async def test_create_missing_first_name(self, tool):
        result = await tool.fn(action="create")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_update(self, tool):
        with patch("freshservice_mcp.tools.agents.api_put", new_callable=AsyncMock) as m:
            m.return_value = _ok({"agent": {"id": 1}})
            result = await tool.fn(action="update", agent_id=1, first_name="Updated")
            assert result.get("success") or "agent" in result

    @pytest.mark.asyncio
    async def test_update_missing_id(self, tool):
        result = await tool.fn(action="update")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_filter(self, tool):
        with patch("freshservice_mcp.tools.agents.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"agents": []})
            result = await tool.fn(action="filter", query='"active:true"')
            assert "agents" in result or "error" not in result


# ═══════════════════════════════════════════════════════════════════════════
# Requesters — deeper coverage
# ═══════════════════════════════════════════════════════════════════════════
class TestRequestersDeep:
    @pytest.fixture
    def tool(self):
        from freshservice_mcp.tools.requesters import register_requesters_tools
        mcp = _mcp_with_tool(register_requesters_tools)
        return mcp._tool_manager._tools["manage_requester"]

    @pytest.mark.asyncio
    async def test_create(self, tool):
        with patch("freshservice_mcp.tools.requesters.api_post", new_callable=AsyncMock) as m:
            m.return_value = _ok({"requester": {"id": 1}}, 201)
            result = await tool.fn(action="create", first_name="Test")
            assert result.get("success") or "requester" in result

    @pytest.mark.asyncio
    async def test_update(self, tool):
        with patch("freshservice_mcp.tools.requesters.api_put", new_callable=AsyncMock) as m:
            m.return_value = _ok({"requester": {"id": 1}})
            result = await tool.fn(action="update", requester_id=1, first_name="Updated")
            assert result.get("success") or "requester" in result

    @pytest.mark.asyncio
    async def test_update_missing_id(self, tool):
        result = await tool.fn(action="update")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_filter(self, tool):
        with patch("freshservice_mcp.tools.requesters.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"requesters": []})
            result = await tool.fn(action="filter", query='"active:true"')
            assert "requesters" in result or "error" not in result


# ═══════════════════════════════════════════════════════════════════════════
# Departments — deeper coverage
# ═══════════════════════════════════════════════════════════════════════════
class TestDepartmentsDeep:
    @pytest.fixture
    def tool(self):
        from freshservice_mcp.tools.departments import register_department_tools
        mcp = _mcp_with_tool(register_department_tools)
        return mcp._tool_manager._tools["manage_department"]

    @pytest.mark.asyncio
    async def test_create(self, tool):
        with patch("freshservice_mcp.tools.departments.api_post", new_callable=AsyncMock) as m:
            m.return_value = _ok({"department": {"id": 1}}, 201)
            result = await tool.fn(action="create", name="IT")
            assert result.get("success") or "department" in result

    @pytest.mark.asyncio
    async def test_create_missing_name(self, tool):
        result = await tool.fn(action="create")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_update(self, tool):
        with patch("freshservice_mcp.tools.departments.api_put", new_callable=AsyncMock) as m:
            m.return_value = _ok({"department": {"id": 1}})
            result = await tool.fn(action="update", department_id=1, name="IT Updated")
            assert result.get("success") or "department" in result

    @pytest.mark.asyncio
    async def test_delete(self, tool):
        with patch("freshservice_mcp.tools.departments.api_delete", new_callable=AsyncMock) as m:
            m.return_value = _no_content()
            result = await tool.fn(action="delete", department_id=1)
            assert result.get("success") is True


# ═══════════════════════════════════════════════════════════════════════════
# Releases — deeper coverage
# ═══════════════════════════════════════════════════════════════════════════
class TestReleasesDeep:
    @pytest.fixture
    def tool(self):
        from freshservice_mcp.tools.releases import register_release_tools
        mcp = _mcp_with_tool(register_release_tools)
        return mcp._tool_manager._tools["manage_release"]

    @pytest.mark.asyncio
    async def test_create(self, tool):
        with patch("freshservice_mcp.tools.releases.api_post", new_callable=AsyncMock) as m:
            m.return_value = _ok({"release": {"id": 1}}, 201)
            result = await tool.fn(
                action="create", subject="Release 1.0",
                description="Major release", release_type=1,
                priority=2, status=1, planned_start_date="2026-06-01",
                planned_end_date="2026-06-15"
            )
            assert result.get("success") or "release" in result

    @pytest.mark.asyncio
    async def test_update(self, tool):
        with patch("freshservice_mcp.tools.releases.api_put", new_callable=AsyncMock) as m:
            m.return_value = _ok({"release": {"id": 1}})
            result = await tool.fn(action="update", release_id=1, subject="Updated")
            assert result.get("success") or "release" in result

    @pytest.mark.asyncio
    async def test_update_missing_id(self, tool):
        result = await tool.fn(action="update")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_delete(self, tool):
        with patch("freshservice_mcp.tools.releases.api_delete", new_callable=AsyncMock) as m:
            m.return_value = _no_content()
            result = await tool.fn(action="delete", release_id=1)
            assert result.get("success") is True

    @pytest.mark.asyncio
    async def test_delete_missing_id(self, tool):
        result = await tool.fn(action="delete")
        assert "error" in result


# ═══════════════════════════════════════════════════════════════════════════
# Solutions — deeper coverage
# ═══════════════════════════════════════════════════════════════════════════
class TestSolutionsDeep:
    @pytest.fixture
    def tool(self):
        from freshservice_mcp.tools.solutions import register_solutions_tools
        mcp = _mcp_with_tool(register_solutions_tools)
        return mcp._tool_manager._tools["manage_solution"]

    @pytest.mark.asyncio
    async def test_create_category(self, tool):
        with patch("freshservice_mcp.tools.solutions.api_post", new_callable=AsyncMock) as m:
            m.return_value = _ok({"category": {"id": 1}}, 201)
            result = await tool.fn(action="create_category", name="FAQ")
            assert result.get("success") or "category" in result

    @pytest.mark.asyncio
    async def test_create_category_missing_name(self, tool):
        result = await tool.fn(action="create_category")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_update_category(self, tool):
        with patch("freshservice_mcp.tools.solutions.api_put", new_callable=AsyncMock) as m:
            m.return_value = _ok({"category": {"id": 1}})
            result = await tool.fn(action="update_category", category_id=1, name="Updated FAQ")
            assert result.get("success") or "category" in result

    @pytest.mark.asyncio
    async def test_update_category_no_fields(self, tool):
        result = await tool.fn(action="update_category", category_id=1)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_list_folders(self, tool):
        with patch("freshservice_mcp.tools.solutions.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"folders": [{"id": 1}]})
            result = await tool.fn(action="list_folders", category_id=1)
            assert "folders" in result

    @pytest.mark.asyncio
    async def test_list_folders_missing_category(self, tool):
        result = await tool.fn(action="list_folders")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_create_folder(self, tool):
        with patch("freshservice_mcp.tools.solutions.api_post", new_callable=AsyncMock) as m:
            m.return_value = _ok({"folder": {"id": 1}}, 201)
            result = await tool.fn(action="create_folder", category_id=1, name="How-Tos", department_ids=[1])
            assert result.get("success") or "folder" in result

    @pytest.mark.asyncio
    async def test_list_articles(self, tool):
        with patch("freshservice_mcp.tools.solutions.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"articles": [{"id": 1}]})
            result = await tool.fn(action="list_articles", folder_id=1)
            assert "articles" in result

    @pytest.mark.asyncio
    async def test_create_article(self, tool):
        with patch("freshservice_mcp.tools.solutions.api_post", new_callable=AsyncMock) as m:
            m.return_value = _ok({"article": {"id": 1}}, 201)
            result = await tool.fn(action="create_article", folder_id=1, title="How to reset password", description="Steps to reset")
            assert result.get("success") or "article" in result


# ═══════════════════════════════════════════════════════════════════════════
# Products — deeper coverage
# ═══════════════════════════════════════════════════════════════════════════
class TestProductsDeep:
    @pytest.fixture
    def tool(self):
        from freshservice_mcp.tools.products import register_products_tools
        mcp = _mcp_with_tool(register_products_tools)
        return mcp._tool_manager._tools["manage_product"]

    @pytest.mark.asyncio
    async def test_create(self, tool):
        with patch("freshservice_mcp.tools.products.api_post", new_callable=AsyncMock) as m:
            m.return_value = _ok({"product": {"id": 1}}, 201)
            result = await tool.fn(action="create", name="Laptop Pro", asset_type_id=1)
            assert result.get("success") or "product" in result

    @pytest.mark.asyncio
    async def test_create_missing_fields(self, tool):
        result = await tool.fn(action="create")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_update(self, tool):
        with patch("freshservice_mcp.tools.products.api_put", new_callable=AsyncMock) as m:
            m.return_value = _ok({"product": {"id": 1}})
            result = await tool.fn(action="update", product_id=1, name="Updated")
            assert result.get("success") or "product" in result
