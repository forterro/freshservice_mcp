"""Functional tests for change sub-tools: notes, tasks, time entries, approvals.

These test the actual business logic and API contract:
- Correct endpoint construction (changes/{id}/notes|tasks|time_entries|approvals)
- Payload validation (required fields, correct field mapping)
- Response handling (204 → success message, JSON response passthrough)
- Error paths (missing IDs, missing required fields)
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from mcp.server.fastmcp import FastMCP
from freshservice_mcp.tools.changes import register_changes_tools

MOD = "freshservice_mcp.tools.changes"


def _resp(data=None, status=200):
    r = MagicMock()
    r.status_code = status
    r.json.return_value = data or {}
    r.raise_for_status = MagicMock()
    r.headers = {"Link": ""}
    return r


@pytest.fixture
def tools():
    mcp = FastMCP("test")
    register_changes_tools(mcp)
    return mcp


def _t(mcp, name):
    return mcp._tool_manager._tools[name]


# ═══════════════════════════════════════════════════════════════════════════
# Change Notes — CRUD
# ═══════════════════════════════════════════════════════════════════════════


class TestChangeNote:
    """Notes are simple CRUD on changes/{id}/notes."""

    @pytest.mark.asyncio
    async def test_list_calls_correct_endpoint(self, tools):
        tool = _t(tools, "manage_change_note")
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _resp({"notes": [{"id": 1}]})
            result = await tool.fn(action="list", change_id=42)
            m.assert_called_once_with("changes/42/notes")
            assert result == {"notes": [{"id": 1}]}

    @pytest.mark.asyncio
    async def test_create_sends_body_in_payload(self, tools):
        tool = _t(tools, "manage_change_note")
        with patch(f"{MOD}.api_post", new_callable=AsyncMock) as m:
            m.return_value = _resp({"note": {"id": 5, "body": "<p>Test</p>"}}, 201)
            result = await tool.fn(action="create", change_id=10, body="<p>Test</p>")
            m.assert_called_once_with("changes/10/notes", json={"body": "<p>Test</p>"})
            assert result["note"]["body"] == "<p>Test</p>"

    @pytest.mark.asyncio
    async def test_create_requires_body(self, tools):
        tool = _t(tools, "manage_change_note")
        result = await tool.fn(action="create", change_id=10)
        assert "error" in result
        assert "body" in result["error"]

    @pytest.mark.asyncio
    async def test_view_by_id(self, tools):
        tool = _t(tools, "manage_change_note")
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _resp({"note": {"id": 7}})
            await tool.fn(action="view", change_id=10, note_id=7)
            m.assert_called_once_with("changes/10/notes/7")

    @pytest.mark.asyncio
    async def test_view_requires_note_id(self, tools):
        tool = _t(tools, "manage_change_note")
        result = await tool.fn(action="view", change_id=10)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_update_sends_new_body(self, tools):
        tool = _t(tools, "manage_change_note")
        with patch(f"{MOD}.api_put", new_callable=AsyncMock) as m:
            m.return_value = _resp({"note": {"id": 7}})
            await tool.fn(action="update", change_id=10, note_id=7, body="Updated")
            m.assert_called_once_with("changes/10/notes/7", json={"body": "Updated"})

    @pytest.mark.asyncio
    async def test_update_requires_both(self, tools):
        tool = _t(tools, "manage_change_note")
        result = await tool.fn(action="update", change_id=10, note_id=7)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_delete_returns_success_on_204(self, tools):
        tool = _t(tools, "manage_change_note")
        with patch(f"{MOD}.api_delete", new_callable=AsyncMock) as m:
            m.return_value = _resp(status=204)
            result = await tool.fn(action="delete", change_id=10, note_id=7)
            assert result["success"] is True
            m.assert_called_once_with("changes/10/notes/7")

    @pytest.mark.asyncio
    async def test_delete_requires_note_id(self, tools):
        tool = _t(tools, "manage_change_note")
        result = await tool.fn(action="delete", change_id=10)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_unknown_action(self, tools):
        tool = _t(tools, "manage_change_note")
        result = await tool.fn(action="archive", change_id=10)
        assert "error" in result


# ═══════════════════════════════════════════════════════════════════════════
# Change Tasks — verifies payload construction with optional fields
# ═══════════════════════════════════════════════════════════════════════════


class TestChangeTask:
    """Tasks have richer payload: status, priority, assigned_to, group, due_date."""

    @pytest.mark.asyncio
    async def test_create_builds_full_payload(self, tools):
        """All optional task fields should appear in the POST body."""
        tool = _t(tools, "manage_change_task")
        with patch(f"{MOD}.api_post", new_callable=AsyncMock) as m:
            m.return_value = _resp({"task": {"id": 1}}, 201)
            await tool.fn(
                action="create", change_id=5,
                title="Deploy v2", description="Roll out to prod",
                task_status=1, task_priority=2,
                assigned_to_id=100, task_group_id=50,
                due_date="2025-06-01",
            )
            payload = m.call_args[1]["json"]
            assert payload["title"] == "Deploy v2"
            assert payload["description"] == "Roll out to prod"
            assert payload["status"] == 1
            assert payload["priority"] == 2
            assert payload["assigned_to_id"] == 100
            assert payload["group_id"] == 50
            assert payload["due_date"] == "2025-06-01"

    @pytest.mark.asyncio
    async def test_create_requires_title_and_description(self, tools):
        tool = _t(tools, "manage_change_task")
        result = await tool.fn(action="create", change_id=5, title="Only title")
        assert "error" in result
        assert "description" in result["error"]

    @pytest.mark.asyncio
    async def test_list(self, tools):
        tool = _t(tools, "manage_change_task")
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _resp({"tasks": []})
            await tool.fn(action="list", change_id=5)
            m.assert_called_once_with("changes/5/tasks")

    @pytest.mark.asyncio
    async def test_view(self, tools):
        tool = _t(tools, "manage_change_task")
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _resp({"task": {"id": 3}})
            await tool.fn(action="view", change_id=5, task_id=3)
            m.assert_called_once_with("changes/5/tasks/3")

    @pytest.mark.asyncio
    async def test_update_uses_task_fields(self, tools):
        """Update should pass task_fields dict directly to PUT."""
        tool = _t(tools, "manage_change_task")
        with patch(f"{MOD}.api_put", new_callable=AsyncMock) as m:
            m.return_value = _resp({"task": {"id": 3}})
            await tool.fn(
                action="update", change_id=5, task_id=3,
                task_fields={"status": 2, "priority": 1},
            )
            payload = m.call_args[1]["json"]
            assert payload == {"status": 2, "priority": 1}

    @pytest.mark.asyncio
    async def test_delete(self, tools):
        tool = _t(tools, "manage_change_task")
        with patch(f"{MOD}.api_delete", new_callable=AsyncMock) as m:
            m.return_value = _resp(status=204)
            result = await tool.fn(action="delete", change_id=5, task_id=3)
            assert result["success"] is True


# ═══════════════════════════════════════════════════════════════════════════
# Change Time Entries — verifies te_agent_id → agent_id mapping
# ═══════════════════════════════════════════════════════════════════════════


class TestChangeTimeEntry:
    """Critical: te_agent_id param maps to 'agent_id' in the API payload."""

    @pytest.mark.asyncio
    async def test_create_maps_te_agent_id_to_agent_id(self, tools):
        """The API expects 'agent_id', but the tool param is 'te_agent_id'."""
        tool = _t(tools, "manage_change_time_entry")
        with patch(f"{MOD}.api_post", new_callable=AsyncMock) as m:
            m.return_value = _resp({"time_entry": {"id": 1}}, 201)
            await tool.fn(
                action="create", change_id=10,
                time_spent="02:30", note="Fixed config",
                te_agent_id=99, executed_at="2025-01-15T10:00:00Z",
            )
            payload = m.call_args[1]["json"]
            assert payload["agent_id"] == 99  # mapped from te_agent_id
            assert payload["time_spent"] == "02:30"
            assert payload["note"] == "Fixed config"
            assert payload["executed_at"] == "2025-01-15T10:00:00Z"

    @pytest.mark.asyncio
    async def test_create_requires_all_three(self, tools):
        tool = _t(tools, "manage_change_time_entry")
        # Missing te_agent_id
        result = await tool.fn(
            action="create", change_id=10, time_spent="01:00", note="Work",
        )
        assert "error" in result
        assert "te_agent_id" in result["error"]

    @pytest.mark.asyncio
    async def test_update_partial_fields(self, tools):
        """Update should only send provided fields."""
        tool = _t(tools, "manage_change_time_entry")
        with patch(f"{MOD}.api_put", new_callable=AsyncMock) as m:
            m.return_value = _resp({"time_entry": {"id": 5}})
            await tool.fn(
                action="update", change_id=10, time_entry_id=5,
                time_spent="03:00",
            )
            payload = m.call_args[1]["json"]
            assert payload == {"time_spent": "03:00"}

    @pytest.mark.asyncio
    async def test_list(self, tools):
        tool = _t(tools, "manage_change_time_entry")
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _resp({"time_entries": []})
            await tool.fn(action="list", change_id=10)
            m.assert_called_once_with("changes/10/time_entries")

    @pytest.mark.asyncio
    async def test_view(self, tools):
        tool = _t(tools, "manage_change_time_entry")
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _resp({"time_entry": {"id": 5}})
            await tool.fn(action="view", change_id=10, time_entry_id=5)
            m.assert_called_once_with("changes/10/time_entries/5")

    @pytest.mark.asyncio
    async def test_delete(self, tools):
        tool = _t(tools, "manage_change_time_entry")
        with patch(f"{MOD}.api_delete", new_callable=AsyncMock) as m:
            m.return_value = _resp(status=204)
            result = await tool.fn(action="delete", change_id=10, time_entry_id=5)
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_unknown_action(self, tools):
        tool = _t(tools, "manage_change_time_entry")
        result = await tool.fn(action="bogus", change_id=10)
        assert "error" in result


# ═══════════════════════════════════════════════════════════════════════════
# Change Approvals — groups + individual approvals + chain rule
# ═══════════════════════════════════════════════════════════════════════════


class TestChangeApproval:
    """Approval management: groups, individual approvals, chain rules."""

    @pytest.mark.asyncio
    async def test_list_groups(self, tools):
        tool = _t(tools, "manage_change_approval")
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _resp({"approval_groups": []})
            await tool.fn(action="list_groups", change_id=5)
            m.assert_called_once_with("changes/5/approval_groups")

    @pytest.mark.asyncio
    async def test_create_group_builds_payload(self, tools):
        tool = _t(tools, "manage_change_approval")
        with patch(f"{MOD}.api_post", new_callable=AsyncMock) as m:
            m.return_value = _resp({"approval_group": {"id": 1}}, 201)
            await tool.fn(
                action="create_group", change_id=5,
                name="CAB", approver_ids=[10, 20],
                approval_type="any",
            )
            payload = m.call_args[1]["json"]
            assert payload == {
                "name": "CAB",
                "approver_ids": [10, 20],
                "approval_type": "any",
            }

    @pytest.mark.asyncio
    async def test_create_group_defaults_to_everyone(self, tools):
        """approval_type should default to 'everyone' when not specified."""
        tool = _t(tools, "manage_change_approval")
        with patch(f"{MOD}.api_post", new_callable=AsyncMock) as m:
            m.return_value = _resp({"approval_group": {"id": 1}}, 201)
            await tool.fn(
                action="create_group", change_id=5,
                name="Approvers", approver_ids=[10],
            )
            payload = m.call_args[1]["json"]
            assert payload["approval_type"] == "everyone"

    @pytest.mark.asyncio
    async def test_create_group_requires_name_and_ids(self, tools):
        tool = _t(tools, "manage_change_approval")
        result = await tool.fn(action="create_group", change_id=5, name="X")
        assert "error" in result
        assert "approver_ids" in result["error"]

    @pytest.mark.asyncio
    async def test_update_group(self, tools):
        tool = _t(tools, "manage_change_approval")
        with patch(f"{MOD}.api_put", new_callable=AsyncMock) as m:
            m.return_value = _resp({"approval_group": {"id": 1}})
            await tool.fn(
                action="update_group", change_id=5, approval_group_id=1,
                name="New CAB", approver_ids=[30], approval_type="any",
            )
            call_args = m.call_args
            assert "changes/5/approval_groups/1" in call_args[0][0]
            payload = call_args[1]["json"]
            assert payload["name"] == "New CAB"
            assert payload["approver_ids"] == [30]
            assert payload["approval_type"] == "any"

    @pytest.mark.asyncio
    async def test_cancel_group(self, tools):
        tool = _t(tools, "manage_change_approval")
        with patch(f"{MOD}.api_put", new_callable=AsyncMock) as m:
            m.return_value = _resp({})
            result = await tool.fn(action="cancel_group", change_id=5, approval_group_id=1)
            assert result["success"] is True
            m.assert_called_once_with("changes/5/approval_groups/1/cancel")

    @pytest.mark.asyncio
    async def test_list_approvals(self, tools):
        tool = _t(tools, "manage_change_approval")
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _resp({"approvals": []})
            await tool.fn(action="list", change_id=5)
            m.assert_called_once_with("changes/5/approvals")

    @pytest.mark.asyncio
    async def test_view_approval(self, tools):
        tool = _t(tools, "manage_change_approval")
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _resp({"approval": {"id": 3}})
            await tool.fn(action="view", change_id=5, approval_id=3)
            m.assert_called_once_with("changes/5/approvals/3")

    @pytest.mark.asyncio
    async def test_remind(self, tools):
        tool = _t(tools, "manage_change_approval")
        with patch(f"{MOD}.api_put", new_callable=AsyncMock) as m:
            m.return_value = _resp({})
            result = await tool.fn(action="remind", change_id=5, approval_id=3)
            assert result["success"] is True
            m.assert_called_once_with("changes/5/approvals/3/resend_approval")

    @pytest.mark.asyncio
    async def test_cancel_approval(self, tools):
        tool = _t(tools, "manage_change_approval")
        with patch(f"{MOD}.api_put", new_callable=AsyncMock) as m:
            m.return_value = _resp({})
            result = await tool.fn(action="cancel", change_id=5, approval_id=3)
            assert result["success"] is True
            m.assert_called_once_with("changes/5/approvals/3/cancel")

    @pytest.mark.asyncio
    async def test_set_chain_rule_parallel(self, tools):
        tool = _t(tools, "manage_change_approval")
        with patch(f"{MOD}.api_put", new_callable=AsyncMock) as m:
            m.return_value = _resp({"approval_chain_type": "parallel"})
            result = await tool.fn(
                action="set_chain_rule", change_id=5,
                approval_chain_type="parallel",
            )
            payload = m.call_args[1]["json"]
            assert payload == {"approval_chain_type": "parallel"}

    @pytest.mark.asyncio
    async def test_set_chain_rule_rejects_invalid(self, tools):
        tool = _t(tools, "manage_change_approval")
        result = await tool.fn(
            action="set_chain_rule", change_id=5,
            approval_chain_type="random",
        )
        assert "error" in result
        assert "parallel" in result["error"]

    @pytest.mark.asyncio
    async def test_unknown_action(self, tools):
        tool = _t(tools, "manage_change_approval")
        result = await tool.fn(action="explode", change_id=5)
        assert "error" in result
