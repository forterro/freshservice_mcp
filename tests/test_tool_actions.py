"""Tests for tool action handlers — exercises the action dispatch logic."""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from mcp.server.fastmcp import FastMCP


def _mcp_with_tool(register_func):
    """Helper to create MCP and register tools."""
    mcp = FastMCP("test")
    register_func(mcp)
    return mcp


def _ok_response(data, status_code=200):
    """Create a mock successful response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.raise_for_status = MagicMock()
    resp.json.return_value = data
    resp.is_success = True
    resp.text = "{}"
    return resp


def _no_content_response():
    """Create a mock 204 response."""
    resp = MagicMock()
    resp.status_code = 204
    resp.raise_for_status = MagicMock()
    return resp


# ═══════════════════════════════════════════════════════════════════════════
# Tickets
# ═══════════════════════════════════════════════════════════════════════════
class TestManageTicket:
    @pytest.fixture
    def tool(self):
        from freshservice_mcp.tools.tickets import register_tickets_tools
        mcp = _mcp_with_tool(register_tickets_tools)
        return mcp._tool_manager._tools["manage_ticket"]

    @pytest.mark.asyncio
    async def test_list(self, tool):
        with patch("freshservice_mcp.tools.tickets.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok_response({"tickets": [{"id": 1}]})
            result = await tool.fn(action="list")
            assert "tickets" in result

    @pytest.mark.asyncio
    async def test_get(self, tool):
        with patch("freshservice_mcp.tools.tickets.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok_response({"ticket": {"id": 42}})
            result = await tool.fn(action="get", ticket_id=42)
            assert "ticket" in result

    @pytest.mark.asyncio
    async def test_get_missing_id(self, tool):
        result = await tool.fn(action="get")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_create(self, tool):
        with patch("freshservice_mcp.tools.tickets.api_post", new_callable=AsyncMock) as m:
            m.return_value = _ok_response({"ticket": {"id": 1}}, 201)
            result = await tool.fn(action="create", subject="Test", description="Desc", email="user@test.com")
            assert result.get("success") or "ticket" in result

    @pytest.mark.asyncio
    async def test_update(self, tool):
        with patch("freshservice_mcp.tools.tickets.api_put", new_callable=AsyncMock) as m:
            m.return_value = _ok_response({"ticket": {"id": 42, "status": 3}})
            result = await tool.fn(action="update", ticket_id=42, status=3)
            assert result.get("success") or "ticket" in result

    @pytest.mark.asyncio
    async def test_delete(self, tool):
        with patch("freshservice_mcp.tools.tickets.api_delete", new_callable=AsyncMock) as m:
            m.return_value = _no_content_response()
            result = await tool.fn(action="delete", ticket_id=42)
            assert result.get("success") is True

    @pytest.mark.asyncio
    async def test_unknown_action(self, tool):
        result = await tool.fn(action="nonexistent")
        assert "error" in result


# ═══════════════════════════════════════════════════════════════════════════
# Changes
# ═══════════════════════════════════════════════════════════════════════════
class TestManageChange:
    @pytest.fixture
    def tool(self):
        from freshservice_mcp.tools.changes import register_changes_tools
        mcp = _mcp_with_tool(register_changes_tools)
        return mcp._tool_manager._tools["manage_change"]

    @pytest.mark.asyncio
    async def test_list(self, tool):
        with patch("freshservice_mcp.tools.changes.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok_response({"changes": [{"id": 1}]})
            result = await tool.fn(action="list")
            assert "changes" in result

    @pytest.mark.asyncio
    async def test_get(self, tool):
        with patch("freshservice_mcp.tools.changes.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok_response({"change": {"id": 10}})
            result = await tool.fn(action="get", change_id=10)
            assert "change" in result

    @pytest.mark.asyncio
    async def test_get_missing_id(self, tool):
        result = await tool.fn(action="get")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_create(self, tool):
        with patch("freshservice_mcp.tools.changes.api_post", new_callable=AsyncMock) as m:
            m.return_value = _ok_response({"change": {"id": 1}}, 201)
            result = await tool.fn(action="create", subject="Upgrade", description="Upgrade DB", requester_id=1, change_type=2)
            assert result.get("success") or "change" in result

    @pytest.mark.asyncio
    async def test_delete(self, tool):
        with patch("freshservice_mcp.tools.changes.api_delete", new_callable=AsyncMock) as m:
            m.return_value = _no_content_response()
            result = await tool.fn(action="delete", change_id=10)
            assert result.get("success") is True

    @pytest.mark.asyncio
    async def test_unknown_action(self, tool):
        result = await tool.fn(action="nonexistent")
        assert "error" in result


# ═══════════════════════════════════════════════════════════════════════════
# Assets
# ═══════════════════════════════════════════════════════════════════════════
class TestManageAsset:
    @pytest.fixture
    def tool(self):
        from freshservice_mcp.tools.assets import register_assets_tools
        mcp = _mcp_with_tool(register_assets_tools)
        return mcp._tool_manager._tools["manage_asset"]

    @pytest.mark.asyncio
    async def test_list(self, tool):
        with patch("freshservice_mcp.tools.assets.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok_response({"assets": [{"id": 1}]})
            result = await tool.fn(action="list")
            assert "assets" in result

    @pytest.mark.asyncio
    async def test_get(self, tool):
        with patch("freshservice_mcp.tools.assets.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok_response({"asset": {"id": 5}})
            result = await tool.fn(action="get", display_id=5)
            assert "asset" in result

    @pytest.mark.asyncio
    async def test_get_missing_id(self, tool):
        result = await tool.fn(action="get")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_create(self, tool):
        with patch("freshservice_mcp.tools.assets.api_post", new_callable=AsyncMock) as m:
            m.return_value = _ok_response({"asset": {"id": 1}}, 201)
            result = await tool.fn(action="create", name="Laptop-001", asset_type_id=1)
            assert result.get("success") or "asset" in result

    @pytest.mark.asyncio
    async def test_delete(self, tool):
        with patch("freshservice_mcp.tools.assets.api_delete", new_callable=AsyncMock) as m:
            m.return_value = _no_content_response()
            result = await tool.fn(action="delete", display_id=5)
            assert result.get("success") is True

    @pytest.mark.asyncio
    async def test_unknown_action(self, tool):
        result = await tool.fn(action="nonexistent")
        assert "error" in result


# ═══════════════════════════════════════════════════════════════════════════
# Agents
# ═══════════════════════════════════════════════════════════════════════════
class TestManageAgent:
    @pytest.fixture
    def tool(self):
        from freshservice_mcp.tools.agents import register_agents_tools
        mcp = _mcp_with_tool(register_agents_tools)
        return mcp._tool_manager._tools["manage_agent"]

    @pytest.mark.asyncio
    async def test_list(self, tool):
        with patch("freshservice_mcp.tools.agents.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok_response({"agents": [{"id": 1}]})
            result = await tool.fn(action="list")
            assert "agents" in result

    @pytest.mark.asyncio
    async def test_get(self, tool):
        with patch("freshservice_mcp.tools.agents.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok_response({"agent": {"id": 1}})
            result = await tool.fn(action="get", agent_id=1)
            assert "agent" in result

    @pytest.mark.asyncio
    async def test_get_missing_id(self, tool):
        result = await tool.fn(action="get")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_unknown_action(self, tool):
        result = await tool.fn(action="nonexistent")
        assert "error" in result


# ═══════════════════════════════════════════════════════════════════════════
# Requesters
# ═══════════════════════════════════════════════════════════════════════════
class TestManageRequester:
    @pytest.fixture
    def tool(self):
        from freshservice_mcp.tools.requesters import register_requesters_tools
        mcp = _mcp_with_tool(register_requesters_tools)
        return mcp._tool_manager._tools["manage_requester"]

    @pytest.mark.asyncio
    async def test_list(self, tool):
        with patch("freshservice_mcp.tools.requesters.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok_response({"requesters": [{"id": 1}]})
            result = await tool.fn(action="list")
            assert "requesters" in result

    @pytest.mark.asyncio
    async def test_get(self, tool):
        with patch("freshservice_mcp.tools.requesters.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok_response({"requester": {"id": 1}})
            result = await tool.fn(action="get", requester_id=1)
            assert "requester" in result

    @pytest.mark.asyncio
    async def test_get_missing_id(self, tool):
        result = await tool.fn(action="get")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_unknown_action(self, tool):
        result = await tool.fn(action="nonexistent")
        assert "error" in result


# ═══════════════════════════════════════════════════════════════════════════
# Problems
# ═══════════════════════════════════════════════════════════════════════════
class TestManageProblem:
    @pytest.fixture
    def tool(self):
        from freshservice_mcp.tools.problems import register_problem_tools
        mcp = _mcp_with_tool(register_problem_tools)
        return mcp._tool_manager._tools["manage_problem"]

    @pytest.mark.asyncio
    async def test_list(self, tool):
        with patch("freshservice_mcp.tools.problems.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok_response({"problems": [{"id": 1}]})
            result = await tool.fn(action="list")
            assert "problems" in result

    @pytest.mark.asyncio
    async def test_get(self, tool):
        with patch("freshservice_mcp.tools.problems.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok_response({"problem": {"id": 1}})
            result = await tool.fn(action="get", problem_id=1)
            assert "problem" in result

    @pytest.mark.asyncio
    async def test_get_missing_id(self, tool):
        result = await tool.fn(action="get")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_create(self, tool):
        with patch("freshservice_mcp.tools.problems.api_post", new_callable=AsyncMock) as m:
            m.return_value = _ok_response({"problem": {"id": 1}}, 201)
            result = await tool.fn(
                action="create", subject="Bug", description="Desc",
                requester_id=1, priority=2, status=1, impact=1, due_by="2026-12-31"
            )
            assert result.get("success") or "problem" in result

    @pytest.mark.asyncio
    async def test_delete(self, tool):
        with patch("freshservice_mcp.tools.problems.api_delete", new_callable=AsyncMock) as m:
            m.return_value = _no_content_response()
            result = await tool.fn(action="delete", problem_id=1)
            assert result.get("success") is True

    @pytest.mark.asyncio
    async def test_unknown_action(self, tool):
        result = await tool.fn(action="nonexistent")
        assert "error" in result


# ═══════════════════════════════════════════════════════════════════════════
# Releases
# ═══════════════════════════════════════════════════════════════════════════
class TestManageRelease:
    @pytest.fixture
    def tool(self):
        from freshservice_mcp.tools.releases import register_release_tools
        mcp = _mcp_with_tool(register_release_tools)
        return mcp._tool_manager._tools["manage_release"]

    @pytest.mark.asyncio
    async def test_list(self, tool):
        with patch("freshservice_mcp.tools.releases.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok_response({"releases": [{"id": 1}]})
            result = await tool.fn(action="list")
            assert "releases" in result

    @pytest.mark.asyncio
    async def test_get(self, tool):
        with patch("freshservice_mcp.tools.releases.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok_response({"release": {"id": 1}})
            result = await tool.fn(action="get", release_id=1)
            assert "release" in result

    @pytest.mark.asyncio
    async def test_get_missing_id(self, tool):
        result = await tool.fn(action="get")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_unknown_action(self, tool):
        result = await tool.fn(action="nonexistent")
        assert "error" in result


# ═══════════════════════════════════════════════════════════════════════════
# Solutions
# ═══════════════════════════════════════════════════════════════════════════
class TestManageSolution:
    @pytest.fixture
    def tool(self):
        from freshservice_mcp.tools.solutions import register_solutions_tools
        mcp = _mcp_with_tool(register_solutions_tools)
        return mcp._tool_manager._tools["manage_solution"]

    @pytest.mark.asyncio
    async def test_list_categories(self, tool):
        with patch("freshservice_mcp.tools.solutions.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok_response({"categories": [{"id": 1}]})
            result = await tool.fn(action="list_categories")
            assert "categories" in result

    @pytest.mark.asyncio
    async def test_get_category(self, tool):
        with patch("freshservice_mcp.tools.solutions.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok_response({"category": {"id": 1}})
            result = await tool.fn(action="get_category", category_id=1)
            assert "category" in result

    @pytest.mark.asyncio
    async def test_get_category_missing_id(self, tool):
        result = await tool.fn(action="get_category")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_unknown_action(self, tool):
        result = await tool.fn(action="nonexistent")
        assert "error" in result


# ═══════════════════════════════════════════════════════════════════════════
# Departments
# ═══════════════════════════════════════════════════════════════════════════
class TestManageDepartment:
    @pytest.fixture
    def tool(self):
        from freshservice_mcp.tools.departments import register_department_tools
        mcp = _mcp_with_tool(register_department_tools)
        return mcp._tool_manager._tools["manage_department"]

    @pytest.mark.asyncio
    async def test_list(self, tool):
        with patch("freshservice_mcp.tools.departments.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok_response({"departments": [{"id": 1}]})
            result = await tool.fn(action="list")
            assert "departments" in result

    @pytest.mark.asyncio
    async def test_get(self, tool):
        with patch("freshservice_mcp.tools.departments.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok_response({"department": {"id": 1}})
            result = await tool.fn(action="get", department_id=1)
            assert "department" in result

    @pytest.mark.asyncio
    async def test_get_missing_id(self, tool):
        result = await tool.fn(action="get")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_unknown_action(self, tool):
        result = await tool.fn(action="nonexistent")
        assert "error" in result


# ═══════════════════════════════════════════════════════════════════════════
# Projects
# ═══════════════════════════════════════════════════════════════════════════
class TestManageProject:
    @pytest.fixture
    def tool(self):
        from freshservice_mcp.tools.projects import register_project_tools
        mcp = _mcp_with_tool(register_project_tools)
        return mcp._tool_manager._tools["manage_project"]

    @pytest.mark.asyncio
    async def test_list(self, tool):
        with patch("freshservice_mcp.tools.projects.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok_response({"projects": [{"id": 1}]})
            result = await tool.fn(action="list")
            assert "projects" in result

    @pytest.mark.asyncio
    async def test_get(self, tool):
        with patch("freshservice_mcp.tools.projects.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok_response({"project": {"id": 1}})
            result = await tool.fn(action="get", project_id=1)
            assert "project" in result

    @pytest.mark.asyncio
    async def test_get_missing_id(self, tool):
        result = await tool.fn(action="get")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_unknown_action(self, tool):
        result = await tool.fn(action="nonexistent")
        assert "error" in result


# ═══════════════════════════════════════════════════════════════════════════
# Status Page
# ═══════════════════════════════════════════════════════════════════════════
class TestManageStatusPage:
    @pytest.fixture
    def tool(self):
        from freshservice_mcp.tools.status_page import register_status_page_tools
        mcp = _mcp_with_tool(register_status_page_tools)
        return mcp._tool_manager._tools["manage_status_page"]

    @pytest.mark.asyncio
    async def test_list_pages(self, tool):
        with patch("freshservice_mcp.tools.status_page.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok_response({"status_pages": [{"id": 1}]})
            result = await tool.fn(action="list_pages")
            assert "status_pages" in result

    @pytest.mark.asyncio
    async def test_list_components(self, tool):
        with patch("freshservice_mcp.tools.status_page._resolve_status_page_id", new_callable=AsyncMock) as mock_sp, \
             patch("freshservice_mcp.tools.status_page.api_get", new_callable=AsyncMock) as m:
            mock_sp.return_value = 1
            m.return_value = _ok_response({"service_components": [{"id": 1}]})
            result = await tool.fn(action="list_components")
            assert "service_components" in result

    @pytest.mark.asyncio
    async def test_unknown_action(self, tool):
        with patch("freshservice_mcp.tools.status_page._resolve_status_page_id", new_callable=AsyncMock) as mock_sp:
            mock_sp.return_value = 1
            result = await tool.fn(action="nonexistent_action_xyz")
            assert "error" in result
