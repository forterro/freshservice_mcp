"""Functional tests for error handling paths across all tool modules.

These verify that HTTP errors are properly caught, wrapped by handle_error(),
and returned as {"error": "..."} dicts — critical for regression detection.
Also tests pagination validation and service catalog multi-page logic.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

import httpx
from mcp.server.fastmcp import FastMCP

from freshservice_mcp.tools.tickets import register_tickets_tools
from freshservice_mcp.tools.releases import register_release_tools
from freshservice_mcp.tools.solutions import register_solutions_tools
from freshservice_mcp.tools.misc import register_misc_tools
from freshservice_mcp.tools.departments import register_department_tools
from freshservice_mcp.tools.requesters import register_requesters_tools
from freshservice_mcp.tools.products import register_products_tools

MOD_TICKETS = "freshservice_mcp.tools.tickets"
MOD_RELEASES = "freshservice_mcp.tools.releases"
MOD_SOLUTIONS = "freshservice_mcp.tools.solutions"
MOD_MISC = "freshservice_mcp.tools.misc"
MOD_DEPTS = "freshservice_mcp.tools.departments"
MOD_REQUESTERS = "freshservice_mcp.tools.requesters"
MOD_PRODUCTS = "freshservice_mcp.tools.products"


def _raise_http_error(*args, **kwargs):
    """Simulate a Freshservice API 422 error."""
    raise httpx.HTTPStatusError(
        "Validation failed",
        request=MagicMock(),
        response=MagicMock(status_code=422, text="Validation Error"),
    )


def _raise_connection(*args, **kwargs):
    """Simulate network failure."""
    raise Exception("Connection refused")


def _resp(data=None, status=200, link=""):
    r = MagicMock()
    r.status_code = status
    r.json.return_value = data or {}
    r.raise_for_status = MagicMock()
    r.headers = {"Link": link}
    return r


def _t(mcp, name):
    return mcp._tool_manager._tools[name]


# ═══════════════════════════════════════════════════════════════════════════
# Tickets — error handling and pagination validation
# ═══════════════════════════════════════════════════════════════════════════


@pytest.fixture
def ticket_tools():
    mcp = FastMCP("test")
    register_tickets_tools(mcp)
    return mcp


class TestTicketPaginationValidation:
    """_validate_pagination rejects invalid page/per_page."""

    @pytest.mark.asyncio
    async def test_page_zero_rejected(self, ticket_tools):
        tool = _t(ticket_tools, "manage_ticket")
        result = await tool.fn(action="list", page=0)
        assert "error" in result
        assert "Page number" in result["error"]

    @pytest.mark.asyncio
    async def test_per_page_over_100_rejected(self, ticket_tools):
        tool = _t(ticket_tools, "manage_ticket")
        result = await tool.fn(action="list", per_page=101)
        assert "error" in result
        assert "Page size" in result["error"]

    @pytest.mark.asyncio
    async def test_per_page_zero_rejected(self, ticket_tools):
        tool = _t(ticket_tools, "manage_ticket")
        result = await tool.fn(action="list", per_page=0)
        assert "error" in result


class TestTicketErrorHandling:
    """Verify handle_error wraps exceptions from API calls."""

    @pytest.mark.asyncio
    async def test_list_api_failure(self, ticket_tools):
        tool = _t(ticket_tools, "manage_ticket")
        with patch(f"{MOD_TICKETS}.api_get", new_callable=AsyncMock, side_effect=_raise_connection):
            result = await tool.fn(action="list")
            assert "error" in result

    @pytest.mark.asyncio
    async def test_get_api_failure(self, ticket_tools):
        tool = _t(ticket_tools, "manage_ticket")
        with patch(f"{MOD_TICKETS}.api_get", new_callable=AsyncMock, side_effect=_raise_connection):
            result = await tool.fn(action="get", ticket_id=1)
            assert "error" in result

    @pytest.mark.asyncio
    async def test_create_api_failure(self, ticket_tools):
        tool = _t(ticket_tools, "manage_ticket")
        with patch(f"{MOD_TICKETS}.api_post", new_callable=AsyncMock, side_effect=_raise_connection):
            result = await tool.fn(
                action="create", subject="T", description="D", email="a@b.com",
            )
            assert "error" in result

    @pytest.mark.asyncio
    async def test_update_api_failure(self, ticket_tools):
        tool = _t(ticket_tools, "manage_ticket")
        with patch(f"{MOD_TICKETS}.api_put", new_callable=AsyncMock, side_effect=_raise_connection):
            result = await tool.fn(action="update", ticket_id=1, priority=3)
            assert "error" in result

    @pytest.mark.asyncio
    async def test_delete_api_failure(self, ticket_tools):
        tool = _t(ticket_tools, "manage_ticket")
        with patch(f"{MOD_TICKETS}.api_delete", new_callable=AsyncMock, side_effect=_raise_connection):
            result = await tool.fn(action="delete", ticket_id=1)
            assert "error" in result

    @pytest.mark.asyncio
    async def test_filter_api_failure(self, ticket_tools):
        tool = _t(ticket_tools, "manage_ticket")
        with patch(f"{MOD_TICKETS}.api_get", new_callable=AsyncMock, side_effect=_raise_connection):
            result = await tool.fn(action="filter", query="status:2")
            assert "error" in result

    @pytest.mark.asyncio
    async def test_get_fields_api_failure(self, ticket_tools):
        tool = _t(ticket_tools, "manage_ticket")
        with patch(f"{MOD_TICKETS}.api_get", new_callable=AsyncMock, side_effect=_raise_connection):
            result = await tool.fn(action="get_fields")
            assert "error" in result


class TestTicketConversationErrors:
    """Error paths in manage_ticket_conversation."""

    @pytest.mark.asyncio
    async def test_reply_api_failure(self, ticket_tools):
        tool = _t(ticket_tools, "manage_ticket_conversation")
        with patch(f"{MOD_TICKETS}.api_post", new_callable=AsyncMock, side_effect=_raise_connection):
            result = await tool.fn(action="reply", ticket_id=1, body="Hi")
            assert "error" in result

    @pytest.mark.asyncio
    async def test_add_note_api_failure(self, ticket_tools):
        tool = _t(ticket_tools, "manage_ticket_conversation")
        with patch(f"{MOD_TICKETS}.api_post", new_callable=AsyncMock, side_effect=_raise_connection):
            result = await tool.fn(action="add_note", ticket_id=1, body="Note")
            assert "error" in result

    @pytest.mark.asyncio
    async def test_update_api_failure(self, ticket_tools):
        tool = _t(ticket_tools, "manage_ticket_conversation")
        with patch(f"{MOD_TICKETS}.api_put", new_callable=AsyncMock, side_effect=_raise_connection):
            result = await tool.fn(action="update", conversation_id=1, body="X")
            assert "error" in result

    @pytest.mark.asyncio
    async def test_list_api_failure(self, ticket_tools):
        tool = _t(ticket_tools, "manage_ticket_conversation")
        with patch(f"{MOD_TICKETS}.api_get", new_callable=AsyncMock, side_effect=_raise_connection):
            result = await tool.fn(action="list", ticket_id=1)
            assert "error" in result


class TestServiceCatalogErrors:
    """Error paths and multi-page logic in manage_service_catalog."""

    @pytest.mark.asyncio
    async def test_list_items_api_failure(self, ticket_tools):
        tool = _t(ticket_tools, "manage_service_catalog")
        with patch(f"{MOD_TICKETS}.api_get", new_callable=AsyncMock, side_effect=_raise_connection):
            result = await tool.fn(action="list_items")
            assert "error" in result

    @pytest.mark.asyncio
    async def test_list_items_multi_page(self, ticket_tools):
        """Should follow pagination links until no 'next'."""
        tool = _t(ticket_tools, "manage_service_catalog")
        page1 = _resp({"items": [{"id": 1}]}, link='<url?page=2>; rel="next"')
        page2 = _resp({"items": [{"id": 2}]}, link="")
        with patch(f"{MOD_TICKETS}.api_get", new_callable=AsyncMock) as m:
            m.side_effect = [page1, page2]
            result = await tool.fn(action="list_items")
            assert result["success"] is True
            assert len(result["items"]) == 2
            assert m.call_count == 2

    @pytest.mark.asyncio
    async def test_get_requested_items_api_failure(self, ticket_tools):
        tool = _t(ticket_tools, "manage_service_catalog")
        with patch(f"{MOD_TICKETS}.api_get", new_callable=AsyncMock, side_effect=_raise_connection):
            result = await tool.fn(action="get_requested_items", ticket_id=1)
            assert "error" in result

    @pytest.mark.asyncio
    async def test_place_request_api_failure(self, ticket_tools):
        tool = _t(ticket_tools, "manage_service_catalog")
        with patch(f"{MOD_TICKETS}.api_post", new_callable=AsyncMock, side_effect=_raise_connection):
            result = await tool.fn(action="place_request", display_id=1, email="a@b.com")
            assert "error" in result


# ═══════════════════════════════════════════════════════════════════════════
# Releases — error paths
# ═══════════════════════════════════════════════════════════════════════════


@pytest.fixture
def release_tools():
    mcp = FastMCP("test")
    register_release_tools(mcp)
    return mcp


class TestReleaseErrors:
    @pytest.mark.asyncio
    async def test_list_api_failure(self, release_tools):
        tool = _t(release_tools, "manage_release")
        with patch(f"{MOD_RELEASES}.api_get", new_callable=AsyncMock, side_effect=_raise_connection):
            result = await tool.fn(action="list")
            assert "error" in result

    @pytest.mark.asyncio
    async def test_get_api_failure(self, release_tools):
        tool = _t(release_tools, "manage_release")
        with patch(f"{MOD_RELEASES}.api_get", new_callable=AsyncMock, side_effect=_raise_connection):
            result = await tool.fn(action="get", release_id=1)
            assert "error" in result

    @pytest.mark.asyncio
    async def test_create_api_failure(self, release_tools):
        tool = _t(release_tools, "manage_release")
        with patch(f"{MOD_RELEASES}.api_post", new_callable=AsyncMock, side_effect=_raise_connection):
            result = await tool.fn(
                action="create", subject="R", description="D",
                priority=1, status=1, release_type=1,
                planned_start_date="2025-01-01", planned_end_date="2025-01-02",
            )
            assert "error" in result

    @pytest.mark.asyncio
    async def test_update_api_failure(self, release_tools):
        tool = _t(release_tools, "manage_release")
        with patch(f"{MOD_RELEASES}.api_put", new_callable=AsyncMock, side_effect=_raise_connection):
            result = await tool.fn(action="update", release_id=1, subject="X")
            assert "error" in result

    @pytest.mark.asyncio
    async def test_delete_api_failure(self, release_tools):
        tool = _t(release_tools, "manage_release")
        with patch(f"{MOD_RELEASES}.api_delete", new_callable=AsyncMock, side_effect=_raise_connection):
            result = await tool.fn(action="delete", release_id=1)
            assert "error" in result

    @pytest.mark.asyncio
    async def test_restore_api_failure(self, release_tools):
        tool = _t(release_tools, "manage_release")
        with patch(f"{MOD_RELEASES}.api_put", new_callable=AsyncMock, side_effect=_raise_connection):
            result = await tool.fn(action="restore", release_id=1)
            assert "error" in result

    @pytest.mark.asyncio
    async def test_filter_api_failure(self, release_tools):
        tool = _t(release_tools, "manage_release")
        with patch(f"{MOD_RELEASES}.api_get", new_callable=AsyncMock, side_effect=_raise_connection):
            result = await tool.fn(action="filter", query="x")
            assert "error" in result

    @pytest.mark.asyncio
    async def test_get_fields_api_failure(self, release_tools):
        tool = _t(release_tools, "manage_release")
        with patch(f"{MOD_RELEASES}.api_get", new_callable=AsyncMock, side_effect=_raise_connection):
            result = await tool.fn(action="get_fields")
            assert "error" in result


# ═══════════════════════════════════════════════════════════════════════════
# Solutions — all actions + errors
# ═══════════════════════════════════════════════════════════════════════════


@pytest.fixture
def solution_tools():
    mcp = FastMCP("test")
    register_solutions_tools(mcp)
    return mcp


class TestSolutionErrors:
    """Test error handlers for all solution actions."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("action,kwargs", [
        ("list_categories", {}),
        ("get_category", {"category_id": 1}),
        ("create_category", {"name": "X"}),
        ("update_category", {"category_id": 1, "name": "Y"}),
        ("list_folders", {"category_id": 1}),
        ("get_folder", {"folder_id": 1}),
        ("create_folder", {"name": "F", "category_id": 1, "department_ids": [1]}),
        ("update_folder", {"folder_id": 1, "name": "Z"}),
        ("list_articles", {"folder_id": 1}),
        ("get_article", {"article_id": 1}),
        ("create_article", {"title": "T", "description": "D", "folder_id": 1}),
        ("update_article", {"article_id": 1, "title": "New"}),
        ("publish_article", {"article_id": 1}),
    ])
    async def test_api_failure_returns_error(self, solution_tools, action, kwargs):
        tool = _t(solution_tools, "manage_solution")
        with patch(f"{MOD_SOLUTIONS}.api_get", new_callable=AsyncMock, side_effect=_raise_connection), \
             patch(f"{MOD_SOLUTIONS}.api_post", new_callable=AsyncMock, side_effect=_raise_connection), \
             patch(f"{MOD_SOLUTIONS}.api_put", new_callable=AsyncMock, side_effect=_raise_connection):
            result = await tool.fn(action=action, **kwargs)
            assert "error" in result


# ═══════════════════════════════════════════════════════════════════════════
# Misc — all actions + errors
# ═══════════════════════════════════════════════════════════════════════════


@pytest.fixture
def misc_tools():
    mcp = FastMCP("test")
    register_misc_tools(mcp)
    return mcp


class TestMiscErrors:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("tool_name,action,kwargs", [
        ("manage_canned_response", "list", {}),
        ("manage_canned_response", "get", {"response_id": 1}),
        ("manage_canned_response", "list_folders", {}),
        ("manage_canned_response", "get_folder", {"folder_id": 1}),
        ("manage_workspace", "list", {}),
        ("manage_workspace", "get", {"workspace_id": 1}),
    ])
    async def test_api_failure(self, misc_tools, tool_name, action, kwargs):
        tool = _t(misc_tools, tool_name)
        with patch(f"{MOD_MISC}.api_get", new_callable=AsyncMock, side_effect=_raise_connection):
            result = await tool.fn(action=action, **kwargs)
            assert "error" in result


# ═══════════════════════════════════════════════════════════════════════════
# Departments — all actions + errors
# ═══════════════════════════════════════════════════════════════════════════


@pytest.fixture
def dept_tools():
    mcp = FastMCP("test")
    register_department_tools(mcp)
    return mcp


class TestDepartmentErrors:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("action,kwargs", [
        ("list", {}),
        ("get", {"department_id": 1}),
        ("create", {"name": "X"}),
        ("update", {"department_id": 1, "name": "Y"}),
        ("delete", {"department_id": 1}),
        ("filter", {"query": "name:'X'"}),
        ("get_fields", {}),
    ])
    async def test_department_api_failure(self, dept_tools, action, kwargs):
        tool = _t(dept_tools, "manage_department")
        with patch(f"{MOD_DEPTS}.api_get", new_callable=AsyncMock, side_effect=_raise_connection), \
             patch(f"{MOD_DEPTS}.api_post", new_callable=AsyncMock, side_effect=_raise_connection), \
             patch(f"{MOD_DEPTS}.api_put", new_callable=AsyncMock, side_effect=_raise_connection), \
             patch(f"{MOD_DEPTS}.api_delete", new_callable=AsyncMock, side_effect=_raise_connection):
            result = await tool.fn(action=action, **kwargs)
            assert "error" in result

    @pytest.mark.asyncio
    @pytest.mark.parametrize("action,kwargs", [
        ("list", {}),
        ("get", {"location_id": 1}),
        ("create", {"name": "NYC"}),
        ("update", {"location_id": 1, "name": "LA"}),
        ("delete", {"location_id": 1}),
        ("filter", {"query": "name:'X'"}),
    ])
    async def test_location_api_failure(self, dept_tools, action, kwargs):
        tool = _t(dept_tools, "manage_location")
        with patch(f"{MOD_DEPTS}.api_get", new_callable=AsyncMock, side_effect=_raise_connection), \
             patch(f"{MOD_DEPTS}.api_post", new_callable=AsyncMock, side_effect=_raise_connection), \
             patch(f"{MOD_DEPTS}.api_put", new_callable=AsyncMock, side_effect=_raise_connection), \
             patch(f"{MOD_DEPTS}.api_delete", new_callable=AsyncMock, side_effect=_raise_connection):
            result = await tool.fn(action=action, **kwargs)
            assert "error" in result


# ═══════════════════════════════════════════════════════════════════════════
# Requesters — error paths + functional
# ═══════════════════════════════════════════════════════════════════════════


@pytest.fixture
def requester_tools():
    mcp = FastMCP("test")
    register_requesters_tools(mcp)
    return mcp


class TestRequesterErrors:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("action,kwargs", [
        ("list", {}),
        ("get", {"requester_id": 1}),
        ("filter", {"query": "email:'x@y.com'"}),
        ("create", {"first_name": "X"}),
        ("update", {"requester_id": 1, "first_name": "Y"}),
        ("add_to_group", {"requester_id": 1, "group_id": 5}),
        ("get_fields", {}),
    ])
    async def test_requester_api_failure(self, requester_tools, action, kwargs):
        tool = _t(requester_tools, "manage_requester")
        with patch(f"{MOD_REQUESTERS}.api_get", new_callable=AsyncMock, side_effect=_raise_connection), \
             patch(f"{MOD_REQUESTERS}.api_post", new_callable=AsyncMock, side_effect=_raise_connection), \
             patch(f"{MOD_REQUESTERS}.api_put", new_callable=AsyncMock, side_effect=_raise_connection):
            result = await tool.fn(action=action, **kwargs)
            assert "error" in result

    @pytest.mark.asyncio
    @pytest.mark.parametrize("action,kwargs", [
        ("list", {}),
        ("get", {"group_id": 1}),
        ("create", {"name": "G"}),
        ("update", {"group_id": 1, "name": "H"}),
        ("list_members", {"group_id": 1}),
    ])
    async def test_requester_group_api_failure(self, requester_tools, action, kwargs):
        tool = _t(requester_tools, "manage_requester_group")
        with patch(f"{MOD_REQUESTERS}.api_get", new_callable=AsyncMock, side_effect=_raise_connection), \
             patch(f"{MOD_REQUESTERS}.api_post", new_callable=AsyncMock, side_effect=_raise_connection), \
             patch(f"{MOD_REQUESTERS}.api_put", new_callable=AsyncMock, side_effect=_raise_connection):
            result = await tool.fn(action=action, **kwargs)
            assert "error" in result


# ═══════════════════════════════════════════════════════════════════════════
# Products — error paths
# ═══════════════════════════════════════════════════════════════════════════


@pytest.fixture
def product_tools():
    mcp = FastMCP("test")
    register_products_tools(mcp)
    return mcp


class TestProductErrors:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("action,kwargs", [
        ("list", {}),
        ("get", {"product_id": 1}),
        ("create", {"name": "P"}),
        ("update", {"product_id": 1, "name": "Q"}),
    ])
    async def test_product_api_failure(self, product_tools, action, kwargs):
        tool = _t(product_tools, "manage_product")
        with patch(f"{MOD_PRODUCTS}.api_get", new_callable=AsyncMock, side_effect=_raise_connection), \
             patch(f"{MOD_PRODUCTS}.api_post", new_callable=AsyncMock, side_effect=_raise_connection), \
             patch(f"{MOD_PRODUCTS}.api_put", new_callable=AsyncMock, side_effect=_raise_connection):
            result = await tool.fn(action=action, **kwargs)
            assert "error" in result
