"""Tests for freshservice_mcp.tools — tool registration and basic action handling."""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from mcp.server.fastmcp import FastMCP


def _create_mcp():
    """Create a fresh MCP instance for testing."""
    return FastMCP("test")


class TestMiscToolRegistration:
    def test_registers_tools(self):
        from freshservice_mcp.tools.misc import register_misc_tools
        mcp = _create_mcp()
        register_misc_tools(mcp)
        tools = mcp._tool_manager._tools
        assert "manage_canned_response" in tools
        assert "manage_workspace" in tools


class TestSolutionsToolRegistration:
    def test_registers_tools(self):
        from freshservice_mcp.tools.solutions import register_solutions_tools
        mcp = _create_mcp()
        register_solutions_tools(mcp)
        tools = mcp._tool_manager._tools
        assert "manage_solution" in tools


class TestProductsToolRegistration:
    def test_registers_tools(self):
        from freshservice_mcp.tools.products import register_products_tools
        mcp = _create_mcp()
        register_products_tools(mcp)
        tools = mcp._tool_manager._tools
        assert "manage_product" in tools


class TestTicketsToolRegistration:
    def test_registers_tools(self):
        from freshservice_mcp.tools.tickets import register_tickets_tools
        mcp = _create_mcp()
        register_tickets_tools(mcp)
        tools = mcp._tool_manager._tools
        assert "manage_ticket" in tools


class TestChangesToolRegistration:
    def test_registers_tools(self):
        from freshservice_mcp.tools.changes import register_changes_tools
        mcp = _create_mcp()
        register_changes_tools(mcp)
        tools = mcp._tool_manager._tools
        assert "manage_change" in tools


class TestAssetsToolRegistration:
    def test_registers_tools(self):
        from freshservice_mcp.tools.assets import register_assets_tools
        mcp = _create_mcp()
        register_assets_tools(mcp)
        tools = mcp._tool_manager._tools
        assert "manage_asset" in tools


class TestAgentsToolRegistration:
    def test_registers_tools(self):
        from freshservice_mcp.tools.agents import register_agents_tools
        mcp = _create_mcp()
        register_agents_tools(mcp)
        tools = mcp._tool_manager._tools
        assert "manage_agent" in tools


class TestRequestersToolRegistration:
    def test_registers_tools(self):
        from freshservice_mcp.tools.requesters import register_requesters_tools
        mcp = _create_mcp()
        register_requesters_tools(mcp)
        tools = mcp._tool_manager._tools
        assert "manage_requester" in tools


class TestDepartmentsToolRegistration:
    def test_registers_tools(self):
        from freshservice_mcp.tools.departments import register_department_tools
        mcp = _create_mcp()
        register_department_tools(mcp)
        tools = mcp._tool_manager._tools
        assert "manage_department" in tools


class TestProblemsToolRegistration:
    def test_registers_tools(self):
        from freshservice_mcp.tools.problems import register_problem_tools
        mcp = _create_mcp()
        register_problem_tools(mcp)
        tools = mcp._tool_manager._tools
        assert "manage_problem" in tools


class TestReleasesToolRegistration:
    def test_registers_tools(self):
        from freshservice_mcp.tools.releases import register_release_tools
        mcp = _create_mcp()
        register_release_tools(mcp)
        tools = mcp._tool_manager._tools
        assert "manage_release" in tools


class TestProjectsToolRegistration:
    def test_registers_tools(self):
        from freshservice_mcp.tools.projects import register_project_tools
        mcp = _create_mcp()
        register_project_tools(mcp)
        tools = mcp._tool_manager._tools
        assert "manage_project" in tools
        assert "manage_project_task" in tools


class TestStatusPageToolRegistration:
    def test_registers_tools(self):
        from freshservice_mcp.tools.status_page import register_status_page_tools
        mcp = _create_mcp()
        register_status_page_tools(mcp)
        tools = mcp._tool_manager._tools
        assert "manage_status_page" in tools
        assert "manage_maintenance_window" in tools


class TestMiscToolActions:
    @pytest.mark.asyncio
    async def test_manage_workspace_unknown_action(self):
        from freshservice_mcp.tools.misc import register_misc_tools
        mcp = _create_mcp()
        register_misc_tools(mcp)
        tool = mcp._tool_manager._tools["manage_workspace"]
        result = await tool.fn(action="invalid_action")
        assert "error" in result
        assert "Unknown action" in result["error"]

    @pytest.mark.asyncio
    async def test_manage_canned_response_unknown_action(self):
        from freshservice_mcp.tools.misc import register_misc_tools
        mcp = _create_mcp()
        register_misc_tools(mcp)
        tool = mcp._tool_manager._tools["manage_canned_response"]
        result = await tool.fn(action="invalid_action")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_manage_workspace_get_missing_id(self):
        from freshservice_mcp.tools.misc import register_misc_tools
        mcp = _create_mcp()
        register_misc_tools(mcp)
        tool = mcp._tool_manager._tools["manage_workspace"]
        result = await tool.fn(action="get")
        assert "error" in result
        assert "workspace_id" in result["error"]

    @pytest.mark.asyncio
    async def test_manage_workspace_list(self):
        from freshservice_mcp.tools.misc import register_misc_tools
        mcp = _create_mcp()
        register_misc_tools(mcp)
        tool = mcp._tool_manager._tools["manage_workspace"]

        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"workspaces": [{"id": 1, "name": "IT"}]}

        with patch("freshservice_mcp.tools.misc.api_get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_resp
            result = await tool.fn(action="list")
            assert "workspaces" in result


class TestProductsToolActions:
    @pytest.mark.asyncio
    async def test_list_products(self):
        from freshservice_mcp.tools.products import register_products_tools
        mcp = _create_mcp()
        register_products_tools(mcp)
        tool = mcp._tool_manager._tools["manage_product"]

        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"products": [{"id": 1}]}

        with patch("freshservice_mcp.tools.products.api_get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_resp
            result = await tool.fn(action="list")
            assert "products" in result

    @pytest.mark.asyncio
    async def test_get_product_missing_id(self):
        from freshservice_mcp.tools.products import register_products_tools
        mcp = _create_mcp()
        register_products_tools(mcp)
        tool = mcp._tool_manager._tools["manage_product"]
        result = await tool.fn(action="get")
        assert "error" in result
        assert "product_id" in result["error"]
