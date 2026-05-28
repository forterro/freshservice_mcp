"""Tests for sub-resource tools: change tasks, change time entries,
change approvals, release tasks, tickets service catalog, and
remaining error/payload branches.

Tests verify:
- Correct API endpoints for sub-resources
- Payload construction with all optional fields
- Error paths (API exceptions returning proper error messages)
- Input validation messages
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
# Change Tasks
# ═══════════════════════════════════════════════════════════════════════════
class TestChangeTasksFull:
    """Test manage_change_task: all CRUD actions."""

    @pytest.fixture
    def tool(self):
        from freshservice_mcp.tools.changes import register_changes_tools
        mcp = FastMCP("test")
        register_changes_tools(mcp)
        return mcp._tool_manager._tools["manage_change_task"]

    MOD = "freshservice_mcp.tools.changes"

    @pytest.mark.asyncio
    async def test_list(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"tasks": [{"id": 1}]})
            result = await tool.fn(action="list", change_id=10)
            assert "tasks" in result
            m.assert_called_once_with("changes/10/tasks")

    @pytest.mark.asyncio
    async def test_create(self, tool):
        with patch(f"{self.MOD}.api_post", new_callable=AsyncMock) as m:
            m.return_value = _ok({"task": {"id": 1}}, 201)
            result = await tool.fn(
                action="create", change_id=10,
                title="Test rollback", description="Verify rollback script",
                task_status=1, task_priority=2,
                assigned_to_id=50, task_group_id=5,
                due_date="2026-06-15T10:00:00Z"
            )
            assert "task" in result
            payload = m.call_args.kwargs["json"]
            assert payload["title"] == "Test rollback"
            assert payload["description"] == "Verify rollback script"
            assert payload["status"] == 1
            assert payload["priority"] == 2
            assert payload["assigned_to_id"] == 50
            assert payload["group_id"] == 5
            assert payload["due_date"] == "2026-06-15T10:00:00Z"

    @pytest.mark.asyncio
    async def test_create_missing_fields(self, tool):
        result = await tool.fn(action="create", change_id=10, title="X")
        assert "description required" in result["error"]

    @pytest.mark.asyncio
    async def test_view(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"task": {"id": 3}})
            result = await tool.fn(action="view", change_id=10, task_id=3)
            m.assert_called_once_with("changes/10/tasks/3")

    @pytest.mark.asyncio
    async def test_view_missing_id(self, tool):
        result = await tool.fn(action="view", change_id=10)
        assert "task_id required" in result["error"]

    @pytest.mark.asyncio
    async def test_update(self, tool):
        with patch(f"{self.MOD}.api_put", new_callable=AsyncMock) as m:
            m.return_value = _ok({"task": {"id": 1}})
            result = await tool.fn(
                action="update", change_id=10, task_id=1,
                task_fields={"status": 3}
            )
            assert "task" in result

    @pytest.mark.asyncio
    async def test_update_missing_id(self, tool):
        result = await tool.fn(action="update", change_id=10)
        assert "task_id required" in result["error"]

    @pytest.mark.asyncio
    async def test_delete(self, tool):
        with patch(f"{self.MOD}.api_delete", new_callable=AsyncMock) as m:
            m.return_value = _no_content()
            result = await tool.fn(action="delete", change_id=10, task_id=3)
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_delete_missing_id(self, tool):
        result = await tool.fn(action="delete", change_id=10)
        assert "task_id required" in result["error"]

    @pytest.mark.asyncio
    async def test_unknown_action(self, tool):
        result = await tool.fn(action="xyz", change_id=10)
        assert "Unknown action" in result["error"]

    @pytest.mark.asyncio
    async def test_list_error(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.side_effect = Exception("Network")
            result = await tool.fn(action="list", change_id=10)
            assert "error" in result

    @pytest.mark.asyncio
    async def test_create_error(self, tool):
        with patch(f"{self.MOD}.api_post", new_callable=AsyncMock) as m:
            m.side_effect = Exception("Server error")
            result = await tool.fn(
                action="create", change_id=10,
                title="T", description="D"
            )
            assert "error" in result


# ═══════════════════════════════════════════════════════════════════════════
# Change Time Entries
# ═══════════════════════════════════════════════════════════════════════════
class TestChangeTimeEntriesFull:
    """Test manage_change_time_entry: all CRUD actions."""

    @pytest.fixture
    def tool(self):
        from freshservice_mcp.tools.changes import register_changes_tools
        mcp = FastMCP("test")
        register_changes_tools(mcp)
        return mcp._tool_manager._tools["manage_change_time_entry"]

    MOD = "freshservice_mcp.tools.changes"

    @pytest.mark.asyncio
    async def test_list(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"time_entries": []})
            result = await tool.fn(action="list", change_id=10)
            assert "time_entries" in result
            m.assert_called_once_with("changes/10/time_entries")

    @pytest.mark.asyncio
    async def test_create(self, tool):
        with patch(f"{self.MOD}.api_post", new_callable=AsyncMock) as m:
            m.return_value = _ok({"time_entry": {"id": 1}}, 201)
            result = await tool.fn(
                action="create", change_id=10,
                time_spent="02:30", note="Implementation",
                te_agent_id=50, executed_at="2026-06-01T10:00:00Z"
            )
            assert "time_entry" in result
            payload = m.call_args.kwargs["json"]
            assert payload["time_spent"] == "02:30"
            assert payload["note"] == "Implementation"
            assert payload["agent_id"] == 50
            assert payload["executed_at"] == "2026-06-01T10:00:00Z"

    @pytest.mark.asyncio
    async def test_create_missing_fields(self, tool):
        result = await tool.fn(action="create", change_id=10, time_spent="01:00")
        assert "note, and te_agent_id" in result["error"]

    @pytest.mark.asyncio
    async def test_view(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"time_entry": {"id": 5}})
            result = await tool.fn(action="view", change_id=10, time_entry_id=5)
            m.assert_called_once_with("changes/10/time_entries/5")

    @pytest.mark.asyncio
    async def test_view_missing_id(self, tool):
        result = await tool.fn(action="view", change_id=10)
        assert "time_entry_id required" in result["error"]

    @pytest.mark.asyncio
    async def test_update(self, tool):
        with patch(f"{self.MOD}.api_put", new_callable=AsyncMock) as m:
            m.return_value = _ok({"time_entry": {"id": 1}})
            result = await tool.fn(
                action="update", change_id=10, time_entry_id=1,
                time_spent="03:00", note="Extended work"
            )
            assert "time_entry" in result
            payload = m.call_args.kwargs["json"]
            assert payload["time_spent"] == "03:00"
            assert payload["note"] == "Extended work"

    @pytest.mark.asyncio
    async def test_update_missing_id(self, tool):
        result = await tool.fn(action="update", change_id=10)
        assert "time_entry_id required" in result["error"]

    @pytest.mark.asyncio
    async def test_delete(self, tool):
        with patch(f"{self.MOD}.api_delete", new_callable=AsyncMock) as m:
            m.return_value = _no_content()
            result = await tool.fn(action="delete", change_id=10, time_entry_id=3)
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_delete_missing_id(self, tool):
        result = await tool.fn(action="delete", change_id=10)
        assert "time_entry_id required" in result["error"]

    @pytest.mark.asyncio
    async def test_unknown_action(self, tool):
        result = await tool.fn(action="xyz", change_id=10)
        assert "Unknown action" in result["error"]


# ═══════════════════════════════════════════════════════════════════════════
# Change Approvals
# ═══════════════════════════════════════════════════════════════════════════
class TestChangeApprovalsFull:
    """Test manage_change_approval: groups and individual approvals."""

    @pytest.fixture
    def tool(self):
        from freshservice_mcp.tools.changes import register_changes_tools
        mcp = FastMCP("test")
        register_changes_tools(mcp)
        return mcp._tool_manager._tools["manage_change_approval"]

    MOD = "freshservice_mcp.tools.changes"

    @pytest.mark.asyncio
    async def test_list_groups(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"approval_groups": []})
            result = await tool.fn(action="list_groups", change_id=10)
            assert "approval_groups" in result

    @pytest.mark.asyncio
    async def test_create_group(self, tool):
        with patch(f"{self.MOD}.api_post", new_callable=AsyncMock) as m:
            m.return_value = _ok({"approval_group": {"id": 1}}, 201)
            result = await tool.fn(
                action="create_group", change_id=10,
                name="CAB", approver_ids=[1, 2, 3],
                approval_type="any"
            )
            assert "approval_group" in result
            payload = m.call_args.kwargs["json"]
            assert payload["name"] == "CAB"
            assert payload["approver_ids"] == [1, 2, 3]
            assert payload["approval_type"] == "any"

    @pytest.mark.asyncio
    async def test_create_group_missing_fields(self, tool):
        result = await tool.fn(action="create_group", change_id=10)
        assert "name and approver_ids" in result["error"]

    @pytest.mark.asyncio
    async def test_update_group(self, tool):
        with patch(f"{self.MOD}.api_put", new_callable=AsyncMock) as m:
            m.return_value = _ok({"approval_group": {"id": 1}})
            result = await tool.fn(
                action="update_group", change_id=10,
                approval_group_id=1, name="Updated CAB"
            )
            assert "approval_group" in result

    @pytest.mark.asyncio
    async def test_update_group_missing_id(self, tool):
        result = await tool.fn(action="update_group", change_id=10)
        assert "approval_group_id required" in result["error"]

    @pytest.mark.asyncio
    async def test_cancel_group(self, tool):
        with patch(f"{self.MOD}.api_put", new_callable=AsyncMock) as m:
            m.return_value = _ok({})
            result = await tool.fn(
                action="cancel_group", change_id=10, approval_group_id=1
            )
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_cancel_group_missing_id(self, tool):
        result = await tool.fn(action="cancel_group", change_id=10)
        assert "approval_group_id required" in result["error"]

    @pytest.mark.asyncio
    async def test_list_approvals(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"approvals": []})
            result = await tool.fn(action="list", change_id=10)
            assert "approvals" in result

    @pytest.mark.asyncio
    async def test_view_approval(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"approval": {"id": 5}})
            result = await tool.fn(action="view", change_id=10, approval_id=5)
            m.assert_called_once_with("changes/10/approvals/5")

    @pytest.mark.asyncio
    async def test_view_missing_id(self, tool):
        result = await tool.fn(action="view", change_id=10)
        assert "approval_id required" in result["error"]

    @pytest.mark.asyncio
    async def test_remind(self, tool):
        with patch(f"{self.MOD}.api_put", new_callable=AsyncMock) as m:
            m.return_value = _ok({})
            result = await tool.fn(action="remind", change_id=10, approval_id=5)
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_remind_missing_id(self, tool):
        result = await tool.fn(action="remind", change_id=10)
        assert "approval_id required" in result["error"]


# ═══════════════════════════════════════════════════════════════════════════
# Change create — payload branches (custom_fields, assets, impacted_services)
# ═══════════════════════════════════════════════════════════════════════════
class TestChangeCreatePayload:
    """Test that custom_fields, assets, impacted_services are sent in create."""

    @pytest.fixture
    def tool(self):
        from freshservice_mcp.tools.changes import register_changes_tools
        mcp = FastMCP("test")
        register_changes_tools(mcp)
        return mcp._tool_manager._tools["manage_change"]

    MOD = "freshservice_mcp.tools.changes"

    @pytest.mark.asyncio
    async def test_create_with_custom_fields_assets_services(self, tool):
        with patch(f"{self.MOD}.api_post", new_callable=AsyncMock) as m:
            m.return_value = _ok({"change": {"id": 1}}, 201)
            result = await tool.fn(
                action="create",
                requester_id=1, subject="Deploy",
                description="Deploy app",
                custom_fields={"cf_env": "production"},
                assets=[{"display_id": 101}],
                impacted_services=[{"id": 50}]
            )
            assert result["success"] is True
            payload = m.call_args.kwargs["json"]
            assert payload["custom_fields"] == {"cf_env": "production"}
            assert payload["assets"] == [{"display_id": 101}]
            assert payload["impacted_services"] == [{"id": 50}]

    @pytest.mark.asyncio
    async def test_create_api_error(self, tool):
        with patch(f"{self.MOD}.api_post", new_callable=AsyncMock) as m:
            m.side_effect = Exception("Server error")
            result = await tool.fn(
                action="create",
                requester_id=1, subject="X", description="X"
            )
            assert "error" in result

    @pytest.mark.asyncio
    async def test_update_with_custom_fields_and_services(self, tool):
        with patch(f"{self.MOD}.api_put", new_callable=AsyncMock) as m:
            m.return_value = _ok({"change": {"id": 1}})
            result = await tool.fn(
                action="update", change_id=1,
                custom_fields={"cf_env": "staging"},
                assets=[{"display_id": 102}],
                impacted_services=[{"id": 51}],
                maintenance_window_id=10
            )
            assert result["success"] is True
            payload = m.call_args.kwargs["json"]
            assert payload["custom_fields"] == {"cf_env": "staging"}
            assert payload["assets"] == [{"display_id": 102}]
            assert payload["impacted_services"] == [{"id": 51}]
            assert payload["maintenance_window"] == {"id": 10}


# ═══════════════════════════════════════════════════════════════════════════
# Tickets — service catalog & conversation payload branches
# ═══════════════════════════════════════════════════════════════════════════
class TestTicketsServiceCatalog:
    """Test manage_service_catalog tool."""

    @pytest.fixture
    def tool(self):
        from freshservice_mcp.tools.tickets import register_tickets_tools
        mcp = FastMCP("test")
        register_tickets_tools(mcp)
        return mcp._tool_manager._tools["manage_service_catalog"]

    MOD = "freshservice_mcp.tools.tickets"

    @pytest.mark.asyncio
    async def test_list_items(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            resp = _ok({"service_items": [{"id": 1}]})
            resp.headers = {"Link": ""}
            m.return_value = resp
            result = await tool.fn(action="list_items")
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_get_requested_items(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            ticket_resp = _ok({"ticket": {"type": "Service Request"}})
            items_resp = _ok({"requested_items": [{"id": 1}]})
            m.side_effect = [ticket_resp, items_resp]
            result = await tool.fn(action="get_requested_items", ticket_id=42)
            assert "requested_items" in result

    @pytest.mark.asyncio
    async def test_get_requested_items_not_service_request(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            ticket_resp = _ok({"ticket": {"type": "Incident"}})
            m.return_value = ticket_resp
            result = await tool.fn(action="get_requested_items", ticket_id=42)
            assert "service requests" in result["error"]

    @pytest.mark.asyncio
    async def test_get_requested_items_missing_id(self, tool):
        result = await tool.fn(action="get_requested_items")
        assert "ticket_id required" in result["error"]

    @pytest.mark.asyncio
    async def test_place_request(self, tool):
        with patch(f"{self.MOD}.api_post", new_callable=AsyncMock) as m:
            m.return_value = _ok({"service_request": {"id": 1}}, 201)
            result = await tool.fn(
                action="place_request", display_id=100,
                email="user@test.com", requested_for="boss@test.com",
                quantity=3
            )
            assert "service_request" in result
            payload = m.call_args.kwargs["json"]
            assert payload["email"] == "user@test.com"
            assert payload["requested_for"] == "boss@test.com"
            assert payload["quantity"] == 3

    @pytest.mark.asyncio
    async def test_place_request_missing_fields(self, tool):
        result = await tool.fn(action="place_request")
        assert "display_id and email" in result["error"]

    @pytest.mark.asyncio
    async def test_unknown_action(self, tool):
        result = await tool.fn(action="xyz")
        assert "Unknown action" in result["error"]


class TestTicketsConversationPayload:
    """Test conversation reply with optional fields."""

    @pytest.fixture
    def tool(self):
        from freshservice_mcp.tools.tickets import register_tickets_tools
        mcp = FastMCP("test")
        register_tickets_tools(mcp)
        return mcp._tool_manager._tools["manage_ticket_conversation"]

    MOD = "freshservice_mcp.tools.tickets"

    @pytest.mark.asyncio
    async def test_reply_with_all_fields(self, tool):
        """Verify cc_emails, bcc_emails, user_id are sent in reply."""
        with patch(f"{self.MOD}.api_post", new_callable=AsyncMock) as m:
            m.return_value = _ok({"conversation": {"id": 1}}, 201)
            result = await tool.fn(
                action="reply", ticket_id=42,
                body="Thanks for reaching out",
                from_email="support@company.com",
                user_id=100,
                cc_emails=["manager@company.com"],
                bcc_emails=["archive@company.com"]
            )
            assert "conversation" in result
            payload = m.call_args.kwargs["json"]
            assert payload["body"] == "Thanks for reaching out"
            assert payload["from_email"] == "support@company.com"
            assert payload["user_id"] == 100
            assert payload["cc_emails"] == ["manager@company.com"]
            assert payload["bcc_emails"] == ["archive@company.com"]

    @pytest.mark.asyncio
    async def test_reply_error(self, tool):
        with patch(f"{self.MOD}.api_post", new_callable=AsyncMock) as m:
            m.side_effect = Exception("Timeout")
            result = await tool.fn(
                action="reply", ticket_id=1, body="X"
            )
            assert "error" in result

    @pytest.mark.asyncio
    async def test_add_note_error(self, tool):
        with patch(f"{self.MOD}.api_post", new_callable=AsyncMock) as m:
            m.side_effect = Exception("Timeout")
            result = await tool.fn(
                action="add_note", ticket_id=1, body="X"
            )
            assert "error" in result

    @pytest.mark.asyncio
    async def test_update_error(self, tool):
        with patch(f"{self.MOD}.api_put", new_callable=AsyncMock) as m:
            m.side_effect = Exception("Timeout")
            result = await tool.fn(
                action="update", conversation_id=1, body="X"
            )
            assert "error" in result


# ═══════════════════════════════════════════════════════════════════════════
# Releases — sub-tools (tasks, notes)
# ═══════════════════════════════════════════════════════════════════════════
class TestReleaseTasksFull:
    """Test manage_release_task if it exists."""

    @pytest.fixture
    def tools(self):
        from freshservice_mcp.tools.releases import register_release_tools
        mcp = FastMCP("test")
        register_release_tools(mcp)
        return mcp._tool_manager._tools

    MOD = "freshservice_mcp.tools.releases"

    @pytest.mark.asyncio
    async def test_task_list(self, tools):
        tool = tools.get("manage_release_task")
        if tool is None:
            pytest.skip("manage_release_task not registered")
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"tasks": []})
            result = await tool.fn(action="list", release_id=1)
            assert "tasks" in result

    @pytest.mark.asyncio
    async def test_task_create(self, tools):
        tool = tools.get("manage_release_task")
        if tool is None:
            pytest.skip("manage_release_task not registered")
        with patch(f"{self.MOD}.api_post", new_callable=AsyncMock) as m:
            m.return_value = _ok({"task": {"id": 1}}, 201)
            result = await tool.fn(
                action="create", release_id=1,
                title="Build artifacts", description="Build Docker images"
            )
            assert "task" in result

    @pytest.mark.asyncio
    async def test_task_create_missing_fields(self, tools):
        tool = tools.get("manage_release_task")
        if tool is None:
            pytest.skip("manage_release_task not registered")
        result = await tool.fn(action="create", release_id=1)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_task_view(self, tools):
        tool = tools.get("manage_release_task")
        if tool is None:
            pytest.skip("manage_release_task not registered")
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"task": {"id": 3}})
            result = await tool.fn(action="get", release_id=1, task_id=3)
            assert "task" in result

    @pytest.mark.asyncio
    async def test_task_view_missing_id(self, tools):
        tool = tools.get("manage_release_task")
        if tool is None:
            pytest.skip("manage_release_task not registered")
        result = await tool.fn(action="get", release_id=1)
        assert "task_id required" in result.get("error", "")

    @pytest.mark.asyncio
    async def test_task_update(self, tools):
        tool = tools.get("manage_release_task")
        if tool is None:
            pytest.skip("manage_release_task not registered")
        with patch(f"{self.MOD}.api_put", new_callable=AsyncMock) as m:
            m.return_value = _ok({"task": {"id": 1}})
            result = await tool.fn(
                action="update", release_id=1, task_id=1,
                status=3, title="Done"
            )
            assert result.get("success") is True

    @pytest.mark.asyncio
    async def test_task_update_missing_id(self, tools):
        tool = tools.get("manage_release_task")
        if tool is None:
            pytest.skip("manage_release_task not registered")
        result = await tool.fn(action="update", release_id=1)
        assert "task_id required" in result.get("error", "")

    @pytest.mark.asyncio
    async def test_task_delete(self, tools):
        tool = tools.get("manage_release_task")
        if tool is None:
            pytest.skip("manage_release_task not registered")
        with patch(f"{self.MOD}.api_delete", new_callable=AsyncMock) as m:
            m.return_value = _no_content()
            result = await tool.fn(action="delete", release_id=1, task_id=3)
            assert result.get("success") is True

    @pytest.mark.asyncio
    async def test_task_delete_missing_id(self, tools):
        tool = tools.get("manage_release_task")
        if tool is None:
            pytest.skip("manage_release_task not registered")
        result = await tool.fn(action="delete", release_id=1)
        assert "task_id required" in result.get("error", "")


# ═══════════════════════════════════════════════════════════════════════════
# Assets — manage_asset_relationship (all actions)
# ═══════════════════════════════════════════════════════════════════════════
class TestAssetsSubtools:
    """Test asset relationship tool: all actions."""

    @pytest.fixture
    def tool(self):
        from freshservice_mcp.tools.assets import register_assets_tools
        mcp = FastMCP("test")
        register_assets_tools(mcp)
        return mcp._tool_manager._tools["manage_asset_relationship"]

    MOD = "freshservice_mcp.tools.assets"

    @pytest.mark.asyncio
    async def test_list_for_asset(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"relationships": [{"id": 1}]})
            result = await tool.fn(action="list_for_asset", display_id=10)
            assert "relationships" in result
            m.assert_called_once_with("assets/10/relationships")

    @pytest.mark.asyncio
    async def test_list_for_asset_missing_id(self, tool):
        result = await tool.fn(action="list_for_asset")
        assert "display_id required" in result["error"]

    @pytest.mark.asyncio
    async def test_list_all(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            resp = _ok([{"id": 1}])
            resp.headers = {"Link": ""}
            m.return_value = resp
            result = await tool.fn(action="list_all", page=2, per_page=10)
            m.assert_called_once_with("relationships", params={"page": 2, "per_page": 10})
            assert "relationships" in result

    @pytest.mark.asyncio
    async def test_get(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"relationship": {"id": 5}})
            result = await tool.fn(action="get", relationship_id=5)
            assert "relationship" in result

    @pytest.mark.asyncio
    async def test_get_missing_id(self, tool):
        result = await tool.fn(action="get")
        assert "relationship_id required" in result["error"]

    @pytest.mark.asyncio
    async def test_create(self, tool):
        with patch(f"{self.MOD}.api_post", new_callable=AsyncMock) as m:
            m.return_value = _ok({"relationships": [{"id": 1}]}, 201)
            result = await tool.fn(
                action="create", display_id=10,
                relationships=[
                    {"relationship_type_id": 1, "secondary_id": 20, "secondary_type": "asset"}
                ]
            )
            # Verify primary_id/primary_type auto-fill
            payload = m.call_args.kwargs["json"]
            assert payload["relationships"][0]["primary_id"] == 10
            assert payload["relationships"][0]["primary_type"] == "asset"

    @pytest.mark.asyncio
    async def test_create_missing_relationships(self, tool):
        result = await tool.fn(action="create")
        assert "relationships list required" in result["error"]

    @pytest.mark.asyncio
    async def test_create_json_string(self, tool):
        """Test that relationships as JSON string are parsed."""
        with patch(f"{self.MOD}.api_post", new_callable=AsyncMock) as m:
            m.return_value = _ok({"relationships": []}, 201)
            result = await tool.fn(
                action="create",
                relationships='[{"relationship_type_id": 1, "primary_id": 5, "primary_type": "asset", "secondary_id": 6, "secondary_type": "asset"}]'
            )
            payload = m.call_args.kwargs["json"]
            assert isinstance(payload["relationships"], list)

    @pytest.mark.asyncio
    async def test_create_bad_json_string(self, tool):
        result = await tool.fn(action="create", relationships="not-json")
        assert "JSON array" in result["error"]

    @pytest.mark.asyncio
    async def test_delete(self, tool):
        with patch(f"{self.MOD}.api_delete", new_callable=AsyncMock) as m:
            m.return_value = _no_content()
            result = await tool.fn(action="delete", relationship_ids=[1, 2, 3])
            assert result["success"] is True
            assert "ids=1,2,3" in m.call_args.args[0]

    @pytest.mark.asyncio
    async def test_delete_missing_ids(self, tool):
        result = await tool.fn(action="delete")
        assert "relationship_ids list required" in result["error"]

    @pytest.mark.asyncio
    async def test_delete_json_string(self, tool):
        with patch(f"{self.MOD}.api_delete", new_callable=AsyncMock) as m:
            m.return_value = _no_content()
            result = await tool.fn(action="delete", relationship_ids="[10,20]")
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_delete_bad_json_string(self, tool):
        result = await tool.fn(action="delete", relationship_ids="bad")
        assert "JSON array" in result["error"]

    @pytest.mark.asyncio
    async def test_get_types(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"relationship_types": []})
            result = await tool.fn(action="get_types")
            m.assert_called_once_with("relationship_types")

    @pytest.mark.asyncio
    async def test_job_status(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"job": {"status": "completed"}})
            result = await tool.fn(action="job_status", job_id="abc123")
            m.assert_called_once_with("jobs/abc123")

    @pytest.mark.asyncio
    async def test_job_status_missing_id(self, tool):
        result = await tool.fn(action="job_status")
        assert "job_id required" in result["error"]

    @pytest.mark.asyncio
    async def test_unknown_action(self, tool):
        result = await tool.fn(action="xyz")
        assert "Unknown action" in result["error"]

    @pytest.mark.asyncio
    async def test_list_for_asset_error(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.side_effect = Exception("Timeout")
            result = await tool.fn(action="list_for_asset", display_id=1)
            assert "error" in result

    @pytest.mark.asyncio
    async def test_create_error(self, tool):
        with patch(f"{self.MOD}.api_post", new_callable=AsyncMock) as m:
            m.side_effect = Exception("Server error")
            result = await tool.fn(
                action="create",
                relationships=[{"relationship_type_id": 1, "primary_id": 1, "primary_type": "asset", "secondary_id": 2, "secondary_type": "asset"}]
            )
            assert "error" in result


# ═══════════════════════════════════════════════════════════════════════════
# Agents — get_me tool (OAuth branch + API key mode)
# ═══════════════════════════════════════════════════════════════════════════
class TestAgentIdentity:
    """Test get_me for both OAuth and API key modes."""

    @pytest.fixture
    def tool(self):
        from freshservice_mcp.tools.agents import register_agents_tools
        mcp = FastMCP("test")
        register_agents_tools(mcp)
        return mcp._tool_manager._tools["get_me"]

    MOD = "freshservice_mcp.tools.agents"

    def _make_token(self, claims):
        import base64 as b64
        payload = b64.urlsafe_b64encode(
            json.dumps(claims).encode()
        ).decode().rstrip("=")
        return f"header.{payload}.signature"

    @pytest.mark.asyncio
    async def test_apikey_mode(self, tool):
        """When no Bearer token, uses /agents/me."""
        with patch(f"{self.MOD}._auth_header", return_value="Basic abc") as _, \
             patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"agent": {"id": 1, "email": "admin@co.com"}})
            result = await tool.fn()
            assert "agent" in result
            m.assert_called_once_with("agents/me")

    @pytest.mark.asyncio
    async def test_oauth_mode_found(self, tool):
        """When Bearer token, decodes JWT and looks up agent."""
        token = self._make_token({"email": "user@co.com"})
        with patch(f"{self.MOD}._auth_header", return_value=f"Bearer {token}"), \
             patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"agents": [{"id": 5, "email": "user@co.com"}]})
            result = await tool.fn()
            assert result["agent"]["email"] == "user@co.com"
            assert result["source"] == "oauth_jwt"

    @pytest.mark.asyncio
    async def test_oauth_mode_not_found(self, tool):
        """When OAuth lookup finds no agent, returns error."""
        token = self._make_token({"email": "unknown@co.com"})
        with patch(f"{self.MOD}._auth_header", return_value=f"Bearer {token}"), \
             patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"agents": []})
            result = await tool.fn()
            assert "error" in result
            assert "unknown@co.com" in result["error"]

    @pytest.mark.asyncio
    async def test_oauth_mode_api_error(self, tool):
        """When OAuth API call fails, returns error."""
        token = self._make_token({"email": "x@co.com"})
        with patch(f"{self.MOD}._auth_header", return_value=f"Bearer {token}"), \
             patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.side_effect = Exception("Network error")
            result = await tool.fn()
            assert "error" in result

    @pytest.mark.asyncio
    async def test_apikey_mode_error(self, tool):
        """When API key mode /agents/me fails."""
        with patch(f"{self.MOD}._auth_header", return_value="Basic abc"), \
             patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.side_effect = Exception("Forbidden")
            result = await tool.fn()
            assert "error" in result

    @pytest.mark.asyncio
    async def test_oauth_bad_token(self, tool):
        """When JWT is malformed, returns error."""
        with patch(f"{self.MOD}._auth_header", return_value="Bearer not.valid-base64.sig"):
            result = await tool.fn()
            assert "error" in result

    @pytest.mark.asyncio
    async def test_oauth_no_email_claim(self, tool):
        """When JWT has no email-like claim."""
        token = self._make_token({"sub": "1234", "aud": "api"})
        with patch(f"{self.MOD}._auth_header", return_value=f"Bearer {token}"):
            result = await tool.fn()
            assert "error" in result
            assert "Could not extract email" in result["error"]

    @pytest.mark.asyncio
    async def test_oauth_user_claim(self, tool):
        """JWT with 'user' field instead of 'email'."""
        token = self._make_token({"user": "alt@co.com"})
        with patch(f"{self.MOD}._auth_header", return_value=f"Bearer {token}"), \
             patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"agents": [{"id": 7, "email": "alt@co.com"}]})
            result = await tool.fn()
            assert result["agent"]["email"] == "alt@co.com"
