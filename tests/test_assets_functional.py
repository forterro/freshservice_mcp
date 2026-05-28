"""Functional tests for asset tools — verifies business logic, payloads, error paths.

Tests cover:
- create: validates enum values, builds correct payload with type_fields
- update: merges asset_fields with explicit params, rejects empty update
- list: pagination params, include/order/trashed options
- search/filter: query building, trashed option
- delete/restore/move: correct endpoints, workspace_id requirement
- get_types/get_type: basic CRUD
- manage_asset_details: endpoint routing for sub-resources
- manage_asset_relationship: bulk create with auto-fill, JSON string guard, delete
"""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from mcp.server.fastmcp import FastMCP
from freshservice_mcp.tools.assets import register_assets_tools

MOD = "freshservice_mcp.tools.assets"


def _resp(data=None, status=200, link=""):
    r = MagicMock()
    r.status_code = status
    r.json.return_value = data or {}
    r.raise_for_status = MagicMock()
    r.headers = {"Link": link}
    return r


@pytest.fixture
def tools():
    mcp = FastMCP("test")
    register_assets_tools(mcp)
    return mcp


def _t(mcp, name):
    return mcp._tool_manager._tools[name]


# ═══════════════════════════════════════════════════════════════════════════
# manage_asset — Create
# ═══════════════════════════════════════════════════════════════════════════


class TestAssetCreate:
    """Verify create payload construction and validation."""

    @pytest.mark.asyncio
    async def test_create_builds_correct_payload(self, tools):
        """All params should appear in the POST body with correct values."""
        tool = _t(tools, "manage_asset")
        with patch(f"{MOD}.api_post", new_callable=AsyncMock) as m:
            m.return_value = _resp({"asset": {"display_id": 42}}, 201)
            result = await tool.fn(
                action="create", name="Laptop-001",
                asset_type_id=500, impact="medium", usage_type="loaner",
                asset_tag="TAG-001", description="Dev laptop",
                user_id=10, location_id=20, department_id=30,
                agent_id=40, group_id=50, assigned_on="2025-01-15",
                workspace_id=2, type_fields={"serial_number": "SN123"},
            )
            assert result["success"] is True
            payload = m.call_args[1]["json"]
            # Core required fields
            assert payload["name"] == "Laptop-001"
            assert payload["asset_type_id"] == 500
            # Enum normalized to lowercase
            assert payload["impact"] == "medium"
            assert payload["usage_type"] == "loaner"
            # Optional fields all present
            assert payload["asset_tag"] == "TAG-001"
            assert payload["user_id"] == 10
            assert payload["workspace_id"] == 2
            assert payload["type_fields"] == {"serial_number": "SN123"}

    @pytest.mark.asyncio
    async def test_create_rejects_invalid_impact(self, tools):
        """Invalid impact enum should return validation error."""
        tool = _t(tools, "manage_asset")
        result = await tool.fn(action="create", name="X", asset_type_id=1, impact="critical")
        assert "error" in result
        assert "impact" in result["error"]

    @pytest.mark.asyncio
    async def test_create_rejects_invalid_usage_type(self, tools):
        tool = _t(tools, "manage_asset")
        result = await tool.fn(action="create", name="X", asset_type_id=1, usage_type="shared")
        assert "error" in result
        assert "usage_type" in result["error"]

    @pytest.mark.asyncio
    async def test_create_requires_name_and_type(self, tools):
        tool = _t(tools, "manage_asset")
        result = await tool.fn(action="create", name="X")
        assert "error" in result
        assert "asset_type_id" in result["error"]


# ═══════════════════════════════════════════════════════════════════════════
# manage_asset — Update
# ═══════════════════════════════════════════════════════════════════════════


class TestAssetUpdate:
    """Verify update merges asset_fields with explicit params."""

    @pytest.mark.asyncio
    async def test_update_explicit_params_override_asset_fields(self, tools):
        """Explicit params should override values in asset_fields dict."""
        tool = _t(tools, "manage_asset")
        with patch(f"{MOD}.api_put", new_callable=AsyncMock) as m:
            m.return_value = _resp({"asset": {"display_id": 1}})
            result = await tool.fn(
                action="update", display_id=1,
                asset_fields={"name": "Old", "description": "Existing"},
                name="New Name", type_fields={"cpu": "i7"},
            )
            assert result["success"] is True
            payload = m.call_args[1]["json"]
            # Explicit param wins
            assert payload["name"] == "New Name"
            # asset_fields value preserved
            assert payload["description"] == "Existing"
            # type_fields included
            assert payload["type_fields"] == {"cpu": "i7"}

    @pytest.mark.asyncio
    async def test_update_rejects_empty(self, tools):
        """Must reject update with no fields at all."""
        tool = _t(tools, "manage_asset")
        result = await tool.fn(action="update", display_id=1)
        assert "error" in result
        assert "No fields" in result["error"]

    @pytest.mark.asyncio
    async def test_update_requires_display_id(self, tools):
        tool = _t(tools, "manage_asset")
        result = await tool.fn(action="update", name="X")
        assert "error" in result


# ═══════════════════════════════════════════════════════════════════════════
# manage_asset — List / Search / Filter
# ═══════════════════════════════════════════════════════════════════════════


class TestAssetListSearchFilter:
    @pytest.mark.asyncio
    async def test_list_passes_all_query_params(self, tools):
        """Verify include, order, trashed, workspace params reach API."""
        tool = _t(tools, "manage_asset")
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _resp({"assets": []}, link='<url?page=2>; rel="next"')
            result = await tool.fn(
                action="list", include="type_fields", order_by="created_at",
                order_type="desc", trashed=True, workspace_id=3, page=1, per_page=50,
            )
            params = m.call_args[1]["params"]
            assert params["include"] == "type_fields"
            assert params["order_by"] == "created_at"
            assert params["order_type"] == "desc"
            assert params["trashed"] == "true"
            assert params["workspace_id"] == 3
            assert "pagination" in result

    @pytest.mark.asyncio
    async def test_search_wraps_query_in_quotes(self, tools):
        """Search query should be wrapped in quotes for the API."""
        tool = _t(tools, "manage_asset")
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _resp({"assets": []})
            await tool.fn(action="search", search_query="Dell XPS", trashed=True)
            params = m.call_args[1]["params"]
            assert params["query"] == '"Dell XPS"'
            assert params["trashed"] == "true"

    @pytest.mark.asyncio
    async def test_search_requires_query(self, tools):
        tool = _t(tools, "manage_asset")
        result = await tool.fn(action="search")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_filter_strips_outer_quotes(self, tools):
        """Filter query should strip any user-provided outer quotes."""
        tool = _t(tools, "manage_asset")
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _resp({"assets": []})
            await tool.fn(action="filter", filter_query='"asset_type_id:500"', include="type_fields")
            params = m.call_args[1]["params"]
            # Should be re-quoted cleanly, not double-quoted
            assert params["filter"] == '"asset_type_id:500"'
            assert params["include"] == "type_fields"

    @pytest.mark.asyncio
    async def test_filter_requires_query(self, tools):
        tool = _t(tools, "manage_asset")
        result = await tool.fn(action="filter")
        assert "error" in result


# ═══════════════════════════════════════════════════════════════════════════
# manage_asset — Delete / Restore / Move
# ═══════════════════════════════════════════════════════════════════════════


class TestAssetLifecycle:
    @pytest.mark.asyncio
    async def test_delete_soft(self, tools):
        tool = _t(tools, "manage_asset")
        with patch(f"{MOD}.api_delete", new_callable=AsyncMock) as m:
            m.return_value = _resp(status=204)
            result = await tool.fn(action="delete", display_id=5)
            assert result["success"] is True
            assert "trash" in result["message"]
            m.assert_called_once_with("assets/5")

    @pytest.mark.asyncio
    async def test_delete_permanently(self, tools):
        tool = _t(tools, "manage_asset")
        with patch(f"{MOD}.api_put", new_callable=AsyncMock) as m:
            m.return_value = _resp(status=204)
            result = await tool.fn(action="delete_permanently", display_id=5)
            assert result["success"] is True
            m.assert_called_once_with("assets/5/delete_forever")

    @pytest.mark.asyncio
    async def test_restore(self, tools):
        tool = _t(tools, "manage_asset")
        with patch(f"{MOD}.api_put", new_callable=AsyncMock) as m:
            m.return_value = _resp({"asset": {"display_id": 5}})
            result = await tool.fn(action="restore", display_id=5)
            assert result["success"] is True
            m.assert_called_once_with("assets/5/restore")

    @pytest.mark.asyncio
    async def test_move_includes_agent_and_group(self, tools):
        """Move should include agent_id and group_id in body when given."""
        tool = _t(tools, "manage_asset")
        with patch(f"{MOD}.api_put", new_callable=AsyncMock) as m:
            m.return_value = _resp({"asset": {"display_id": 5}})
            await tool.fn(action="move", display_id=5, workspace_id=3, agent_id=10, group_id=20)
            payload = m.call_args[1]["json"]
            assert payload == {"workspace_id": 3, "agent_id": 10, "group_id": 20}

    @pytest.mark.asyncio
    async def test_move_requires_workspace(self, tools):
        tool = _t(tools, "manage_asset")
        result = await tool.fn(action="move", display_id=5)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_get_with_include(self, tools):
        tool = _t(tools, "manage_asset")
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _resp({"asset": {"display_id": 1}})
            await tool.fn(action="get", display_id=1, include="type_fields")
            params = m.call_args[1].get("params")
            assert params["include"] == "type_fields"

    @pytest.mark.asyncio
    async def test_get_types(self, tools):
        tool = _t(tools, "manage_asset")
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _resp({"asset_types": [{"id": 1}]})
            result = await tool.fn(action="get_types")
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_get_type_by_id(self, tools):
        tool = _t(tools, "manage_asset")
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _resp({"asset_type": {"id": 500}})
            result = await tool.fn(action="get_type", asset_type_id=500)
            assert "error" not in result
            m.assert_called_once_with("asset_types/500")

    @pytest.mark.asyncio
    async def test_get_type_requires_id(self, tools):
        tool = _t(tools, "manage_asset")
        result = await tool.fn(action="get_type")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_unknown_action(self, tools):
        tool = _t(tools, "manage_asset")
        result = await tool.fn(action="explode")
        assert "error" in result
        assert "explode" in result["error"]


# ═══════════════════════════════════════════════════════════════════════════
# manage_asset_details — sub-resource routing
# ═══════════════════════════════════════════════════════════════════════════


class TestAssetDetails:
    """Verify the endpoint routing maps action → correct API path."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("action,endpoint", [
        ("components", "assets/1/components"),
        ("assignment_history", "assets/1/assignment-history"),
        ("requests", "assets/1/requests"),
        ("contracts", "assets/1/contracts"),
    ])
    async def test_routes_to_correct_endpoint(self, tools, action, endpoint):
        tool = _t(tools, "manage_asset_details")
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _resp({"data": []})
            await tool.fn(action=action, display_id=1)
            m.assert_called_once_with(endpoint)

    @pytest.mark.asyncio
    async def test_unknown_action_shows_valid_options(self, tools):
        tool = _t(tools, "manage_asset_details")
        result = await tool.fn(action="invoices", display_id=1)
        assert "error" in result
        assert "components" in result["error"]


# ═══════════════════════════════════════════════════════════════════════════
# manage_asset_relationship — bulk create, JSON guard, auto-fill
# ═══════════════════════════════════════════════════════════════════════════


class TestAssetRelationship:
    """Key business logic: auto-fill primary_id, JSON string deserialization."""

    @pytest.mark.asyncio
    async def test_create_auto_fills_primary_from_display_id(self, tools):
        """When display_id is given, it should auto-fill primary_id/type."""
        tool = _t(tools, "manage_asset_relationship")
        with patch(f"{MOD}.api_post", new_callable=AsyncMock) as m:
            m.return_value = _resp({"job_id": "abc"}, 201)
            await tool.fn(
                action="create", display_id=42,
                relationships=[{"relationship_type_id": 1, "secondary_id": 99, "secondary_type": "asset"}],
            )
            payload = m.call_args[1]["json"]
            rel = payload["relationships"][0]
            assert rel["primary_id"] == 42
            assert rel["primary_type"] == "asset"

    @pytest.mark.asyncio
    async def test_create_accepts_json_string(self, tools):
        """MCP may send relationships as JSON string — should deserialize."""
        tool = _t(tools, "manage_asset_relationship")
        with patch(f"{MOD}.api_post", new_callable=AsyncMock) as m:
            m.return_value = _resp({"job_id": "def"}, 201)
            json_str = json.dumps([{"relationship_type_id": 2, "primary_id": 1, "secondary_id": 3}])
            await tool.fn(action="create", relationships=json_str)
            payload = m.call_args[1]["json"]
            assert len(payload["relationships"]) == 1

    @pytest.mark.asyncio
    async def test_create_rejects_invalid_json_string(self, tools):
        tool = _t(tools, "manage_asset_relationship")
        result = await tool.fn(action="create", relationships="not json at all")
        assert "error" in result
        assert "JSON" in result["error"]

    @pytest.mark.asyncio
    async def test_create_rejects_non_list(self, tools):
        tool = _t(tools, "manage_asset_relationship")
        result = await tool.fn(action="create", relationships='{"key": "val"}')
        assert "error" in result
        assert "list" in result["error"]

    @pytest.mark.asyncio
    async def test_delete_sends_ids_in_query_string(self, tools):
        """Delete should pass IDs as comma-separated query param."""
        tool = _t(tools, "manage_asset_relationship")
        with patch(f"{MOD}.api_delete", new_callable=AsyncMock) as m:
            m.return_value = _resp(status=204)
            await tool.fn(action="delete", relationship_ids=[10, 20, 30])
            m.assert_called_once_with("relationships?ids=10,20,30")

    @pytest.mark.asyncio
    async def test_delete_accepts_json_string_ids(self, tools):
        """relationship_ids might arrive as JSON string from MCP."""
        tool = _t(tools, "manage_asset_relationship")
        with patch(f"{MOD}.api_delete", new_callable=AsyncMock) as m:
            m.return_value = _resp(status=204)
            await tool.fn(action="delete", relationship_ids="[5, 6]")
            m.assert_called_once_with("relationships?ids=5,6")

    @pytest.mark.asyncio
    async def test_list_for_asset(self, tools):
        tool = _t(tools, "manage_asset_relationship")
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _resp({"relationships": []})
            await tool.fn(action="list_for_asset", display_id=5)
            m.assert_called_once_with("assets/5/relationships")

    @pytest.mark.asyncio
    async def test_list_all_with_pagination(self, tools):
        tool = _t(tools, "manage_asset_relationship")
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _resp({"relationships": []})
            result = await tool.fn(action="list_all", page=2, per_page=10)
            params = m.call_args[1]["params"]
            assert params["page"] == 2
            assert params["per_page"] == 10
            assert "pagination" in result

    @pytest.mark.asyncio
    async def test_get_relationship(self, tools):
        tool = _t(tools, "manage_asset_relationship")
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _resp({"relationship": {"id": 7}})
            await tool.fn(action="get", relationship_id=7)
            m.assert_called_once_with("relationships/7")

    @pytest.mark.asyncio
    async def test_get_types(self, tools):
        tool = _t(tools, "manage_asset_relationship")
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _resp({"types": []})
            await tool.fn(action="get_types")
            m.assert_called_once_with("relationship_types")

    @pytest.mark.asyncio
    async def test_job_status(self, tools):
        tool = _t(tools, "manage_asset_relationship")
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _resp({"job": {"status": "complete"}})
            await tool.fn(action="job_status", job_id="abc-123")
            m.assert_called_once_with("jobs/abc-123")

    @pytest.mark.asyncio
    async def test_job_status_requires_id(self, tools):
        tool = _t(tools, "manage_asset_relationship")
        result = await tool.fn(action="job_status")
        assert "error" in result
