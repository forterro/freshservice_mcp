"""Comprehensive tests for problems, status_page, and change_note tools.

Tests verify:
- All CRUD actions with correct API endpoints
- Payload construction with optional fields
- Validation error messages
- Sub-resource operations (notes, tasks, time entries)
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
# Problems — all actions
# ═══════════════════════════════════════════════════════════════════════════
class TestProblemsFull:
    """Test manage_problem: all CRUD actions, close, restore, filter."""

    @pytest.fixture
    def tools(self):
        from freshservice_mcp.tools.problems import register_problem_tools
        mcp = FastMCP("test")
        register_problem_tools(mcp)
        return mcp._tool_manager._tools

    MOD = "freshservice_mcp.tools.problems"

    @pytest.mark.asyncio
    async def test_create_with_all_fields(self, tools):
        """Verify create sends all optional fields in payload."""
        with patch(f"{self.MOD}.api_post", new_callable=AsyncMock) as m:
            m.return_value = _ok({"problem": {"id": 1}}, 201)
            result = await tools["manage_problem"].fn(
                action="create",
                requester_id=100, subject="Disk full",
                description="Root partition at 95%",
                priority=3, status=1, impact=2,
                due_by="2026-06-01T00:00:00Z",
                agent_id=50, group_id=10,
                department_id=5, category="Hardware",
                sub_category="Storage", item_category="Disk",
                known_error=True,
                analysis_fields={"problem_cause": {"description": "Log rotation"}}
            )
            assert result["success"] is True
            payload = m.call_args.kwargs["json"]
            assert payload["requester_id"] == 100
            assert payload["subject"] == "Disk full"
            assert payload["priority"] == 3
            assert payload["agent_id"] == 50
            assert payload["known_error"] is True
            assert "analysis_fields" in payload
            m.assert_called_once_with("problems", json=payload)

    @pytest.mark.asyncio
    async def test_create_missing_fields(self, tools):
        result = await tools["manage_problem"].fn(action="create")
        assert "requester_id, subject, description" in result["error"]

    @pytest.mark.asyncio
    async def test_get_missing_id(self, tools):
        result = await tools["manage_problem"].fn(action="get")
        assert "problem_id required" in result["error"]

    @pytest.mark.asyncio
    async def test_get_success(self, tools):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"problem": {"id": 5}})
            result = await tools["manage_problem"].fn(action="get", problem_id=5)
            m.assert_called_once_with("problems/5")

    @pytest.mark.asyncio
    async def test_update_with_known_error(self, tools):
        """Verify known_error is included in update payload."""
        with patch(f"{self.MOD}.api_put", new_callable=AsyncMock) as m:
            m.return_value = _ok({"problem": {"id": 1}})
            result = await tools["manage_problem"].fn(
                action="update", problem_id=1,
                known_error=False, priority=4
            )
            assert result["success"] is True
            payload = m.call_args.kwargs["json"]
            assert payload["known_error"] is False
            assert payload["priority"] == 4

    @pytest.mark.asyncio
    async def test_update_missing_id(self, tools):
        result = await tools["manage_problem"].fn(action="update")
        assert "problem_id required" in result["error"]

    @pytest.mark.asyncio
    async def test_delete(self, tools):
        with patch(f"{self.MOD}.api_delete", new_callable=AsyncMock) as m:
            m.return_value = _no_content()
            result = await tools["manage_problem"].fn(action="delete", problem_id=7)
            assert result["success"] is True
            assert "7" in result["message"]

    @pytest.mark.asyncio
    async def test_delete_missing_id(self, tools):
        result = await tools["manage_problem"].fn(action="delete")
        assert "problem_id required" in result["error"]

    @pytest.mark.asyncio
    async def test_close(self, tools):
        with patch(f"{self.MOD}.api_put", new_callable=AsyncMock) as m:
            m.return_value = _ok({"problem": {"id": 1, "status": 3}})
            result = await tools["manage_problem"].fn(action="close", problem_id=1)
            assert result["success"] is True
            payload = m.call_args.kwargs["json"]
            assert payload["status"] == 3

    @pytest.mark.asyncio
    async def test_close_missing_id(self, tools):
        result = await tools["manage_problem"].fn(action="close")
        assert "problem_id required" in result["error"]

    @pytest.mark.asyncio
    async def test_restore(self, tools):
        with patch(f"{self.MOD}.api_put", new_callable=AsyncMock) as m:
            m.return_value = _ok({"problem": {"id": 1}})
            result = await tools["manage_problem"].fn(action="restore", problem_id=1)
            assert result["success"] is True
            m.assert_called_once_with("problems/1/restore", json={})

    @pytest.mark.asyncio
    async def test_restore_missing_id(self, tools):
        result = await tools["manage_problem"].fn(action="restore")
        assert "problem_id required" in result["error"]

    @pytest.mark.asyncio
    async def test_filter(self, tools):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"problems": []})
            result = await tools["manage_problem"].fn(
                action="filter", query="priority:3"
            )
            assert "problems" in result
            params = m.call_args.kwargs["params"]
            assert '"priority:3"' == params["query"]

    @pytest.mark.asyncio
    async def test_filter_missing_query(self, tools):
        result = await tools["manage_problem"].fn(action="filter")
        assert "query required" in result["error"]

    @pytest.mark.asyncio
    async def test_get_fields(self, tools):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"problem_form_fields": []})
            result = await tools["manage_problem"].fn(action="get_fields")
            assert "problem_form_fields" in result
            m.assert_called_once_with("problem_form_fields")

    @pytest.mark.asyncio
    async def test_unknown_action(self, tools):
        result = await tools["manage_problem"].fn(action="xyz")
        assert "Unknown action" in result["error"]

    # ── Problem Notes ──
    @pytest.mark.asyncio
    async def test_note_list(self, tools):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"notes": []})
            result = await tools["manage_problem_note"].fn(
                action="list", problem_id=1
            )
            assert "notes" in result

    @pytest.mark.asyncio
    async def test_note_get(self, tools):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"note": {"id": 5}})
            result = await tools["manage_problem_note"].fn(
                action="get", problem_id=1, note_id=5
            )
            m.assert_called_once_with("problems/1/notes/5")

    @pytest.mark.asyncio
    async def test_note_get_missing_id(self, tools):
        result = await tools["manage_problem_note"].fn(
            action="get", problem_id=1
        )
        assert "note_id required" in result["error"]

    @pytest.mark.asyncio
    async def test_note_create(self, tools):
        with patch(f"{self.MOD}.api_post", new_callable=AsyncMock) as m:
            m.return_value = _ok({"note": {"id": 1}}, 201)
            result = await tools["manage_problem_note"].fn(
                action="create", problem_id=1, body="<p>RCA update</p>"
            )
            assert result["success"] is True
            payload = m.call_args.kwargs["json"]
            assert payload["body"] == "<p>RCA update</p>"

    @pytest.mark.asyncio
    async def test_note_create_missing_body(self, tools):
        result = await tools["manage_problem_note"].fn(
            action="create", problem_id=1
        )
        assert "body required" in result["error"]

    @pytest.mark.asyncio
    async def test_note_update(self, tools):
        with patch(f"{self.MOD}.api_put", new_callable=AsyncMock) as m:
            m.return_value = _ok({"note": {"id": 1}})
            result = await tools["manage_problem_note"].fn(
                action="update", problem_id=1, note_id=1,
                body="<p>Updated RCA</p>"
            )
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_note_update_missing_fields(self, tools):
        result = await tools["manage_problem_note"].fn(
            action="update", problem_id=1
        )
        assert "note_id and body" in result["error"]

    @pytest.mark.asyncio
    async def test_note_delete(self, tools):
        with patch(f"{self.MOD}.api_delete", new_callable=AsyncMock) as m:
            m.return_value = _no_content()
            result = await tools["manage_problem_note"].fn(
                action="delete", problem_id=1, note_id=5
            )
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_note_delete_missing_id(self, tools):
        result = await tools["manage_problem_note"].fn(
            action="delete", problem_id=1
        )
        assert "note_id required" in result["error"]

    @pytest.mark.asyncio
    async def test_note_unknown_action(self, tools):
        result = await tools["manage_problem_note"].fn(
            action="xyz", problem_id=1
        )
        assert "Unknown action" in result["error"]

    # ── Problem Tasks ──
    @pytest.mark.asyncio
    async def test_task_list(self, tools):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"tasks": []})
            result = await tools["manage_problem_task"].fn(
                action="list", problem_id=1
            )
            assert "tasks" in result

    @pytest.mark.asyncio
    async def test_task_get(self, tools):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"task": {"id": 3}})
            result = await tools["manage_problem_task"].fn(
                action="get", problem_id=1, task_id=3
            )
            m.assert_called_once_with("problems/1/tasks/3")

    @pytest.mark.asyncio
    async def test_task_get_missing_id(self, tools):
        result = await tools["manage_problem_task"].fn(
            action="get", problem_id=1
        )
        assert "task_id required" in result["error"]

    @pytest.mark.asyncio
    async def test_task_create(self, tools):
        with patch(f"{self.MOD}.api_post", new_callable=AsyncMock) as m:
            m.return_value = _ok({"task": {"id": 1}}, 201)
            result = await tools["manage_problem_task"].fn(
                action="create", problem_id=1,
                title="Investigate root cause",
                description="Check logs", status=1,
                due_date="2026-06-15T10:00:00Z", group_id=5
            )
            assert result["success"] is True
            payload = m.call_args.kwargs["json"]
            assert payload["title"] == "Investigate root cause"
            assert payload["group_id"] == 5

    @pytest.mark.asyncio
    async def test_task_create_missing_title(self, tools):
        result = await tools["manage_problem_task"].fn(
            action="create", problem_id=1
        )
        assert "title required" in result["error"]

    @pytest.mark.asyncio
    async def test_task_update(self, tools):
        with patch(f"{self.MOD}.api_put", new_callable=AsyncMock) as m:
            m.return_value = _ok({"task": {"id": 1}})
            result = await tools["manage_problem_task"].fn(
                action="update", problem_id=1, task_id=1,
                status=3, title="Done"
            )
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_task_update_missing_id(self, tools):
        result = await tools["manage_problem_task"].fn(
            action="update", problem_id=1
        )
        assert "task_id required" in result["error"]

    @pytest.mark.asyncio
    async def test_task_delete(self, tools):
        with patch(f"{self.MOD}.api_delete", new_callable=AsyncMock) as m:
            m.return_value = _no_content()
            result = await tools["manage_problem_task"].fn(
                action="delete", problem_id=1, task_id=3
            )
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_task_delete_missing_id(self, tools):
        result = await tools["manage_problem_task"].fn(
            action="delete", problem_id=1
        )
        assert "task_id required" in result["error"]

    @pytest.mark.asyncio
    async def test_task_unknown_action(self, tools):
        result = await tools["manage_problem_task"].fn(
            action="xyz", problem_id=1
        )
        assert "Unknown action" in result["error"]

    # ── Problem Time Entries ──
    @pytest.mark.asyncio
    async def test_time_entry_list(self, tools):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"time_entries": []})
            result = await tools["manage_problem_time_entry"].fn(
                action="list", problem_id=1
            )
            assert "time_entries" in result

    @pytest.mark.asyncio
    async def test_time_entry_get(self, tools):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"time_entry": {"id": 2}})
            result = await tools["manage_problem_time_entry"].fn(
                action="get", problem_id=1, time_entry_id=2
            )
            m.assert_called_once_with("problems/1/time_entries/2")

    @pytest.mark.asyncio
    async def test_time_entry_get_missing_id(self, tools):
        result = await tools["manage_problem_time_entry"].fn(
            action="get", problem_id=1
        )
        assert "time_entry_id required" in result["error"]

    @pytest.mark.asyncio
    async def test_time_entry_create(self, tools):
        with patch(f"{self.MOD}.api_post", new_callable=AsyncMock) as m:
            m.return_value = _ok({"time_entry": {"id": 1}}, 201)
            result = await tools["manage_problem_time_entry"].fn(
                action="create", problem_id=1,
                time_spent="02:30", agent_id=50,
                note="Debugging session", billable=True
            )
            assert result["success"] is True
            payload = m.call_args.kwargs["json"]
            assert payload["time_spent"] == "02:30"
            assert payload["agent_id"] == 50
            assert payload["billable"] is True

    @pytest.mark.asyncio
    async def test_time_entry_create_missing_time(self, tools):
        result = await tools["manage_problem_time_entry"].fn(
            action="create", problem_id=1
        )
        assert "time_spent required" in result["error"]

    @pytest.mark.asyncio
    async def test_time_entry_update(self, tools):
        with patch(f"{self.MOD}.api_put", new_callable=AsyncMock) as m:
            m.return_value = _ok({"time_entry": {"id": 1}})
            result = await tools["manage_problem_time_entry"].fn(
                action="update", problem_id=1, time_entry_id=1,
                time_spent="03:00", billable=False
            )
            assert result["success"] is True
            payload = m.call_args.kwargs["json"]
            assert payload["time_spent"] == "03:00"
            assert payload["billable"] is False

    @pytest.mark.asyncio
    async def test_time_entry_update_missing_id(self, tools):
        result = await tools["manage_problem_time_entry"].fn(
            action="update", problem_id=1
        )
        assert "time_entry_id required" in result["error"]

    @pytest.mark.asyncio
    async def test_time_entry_delete(self, tools):
        with patch(f"{self.MOD}.api_delete", new_callable=AsyncMock) as m:
            m.return_value = _no_content()
            result = await tools["manage_problem_time_entry"].fn(
                action="delete", problem_id=1, time_entry_id=3
            )
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_time_entry_delete_missing_id(self, tools):
        result = await tools["manage_problem_time_entry"].fn(
            action="delete", problem_id=1
        )
        assert "time_entry_id required" in result["error"]

    @pytest.mark.asyncio
    async def test_time_entry_unknown_action(self, tools):
        result = await tools["manage_problem_time_entry"].fn(
            action="xyz", problem_id=1
        )
        assert "Unknown action" in result["error"]


# ═══════════════════════════════════════════════════════════════════════════
# Change Notes
# ═══════════════════════════════════════════════════════════════════════════
class TestChangeNotesFull:
    """Test change notes: list, create, update, delete."""

    @pytest.fixture
    def tool(self):
        from freshservice_mcp.tools.changes import register_changes_tools
        mcp = FastMCP("test")
        register_changes_tools(mcp)
        return mcp._tool_manager._tools["manage_change_note"]

    MOD = "freshservice_mcp.tools.changes"

    @pytest.mark.asyncio
    async def test_list(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"notes": [{"id": 1}]})
            result = await tool.fn(action="list", change_id=10)
            assert "notes" in result
            m.assert_called_once_with("changes/10/notes")

    @pytest.mark.asyncio
    async def test_create(self, tool):
        with patch(f"{self.MOD}.api_post", new_callable=AsyncMock) as m:
            m.return_value = _ok({"note": {"id": 1}}, 201)
            result = await tool.fn(
                action="create", change_id=10, body="Implementation started"
            )
            assert "note" in result
            payload = m.call_args.kwargs["json"]
            assert payload["body"] == "Implementation started"

    @pytest.mark.asyncio
    async def test_create_missing_body(self, tool):
        result = await tool.fn(action="create", change_id=10)
        assert "body required" in result["error"]

    @pytest.mark.asyncio
    async def test_update(self, tool):
        with patch(f"{self.MOD}.api_put", new_callable=AsyncMock) as m:
            m.return_value = _ok({"note": {"id": 1}})
            result = await tool.fn(
                action="update", change_id=10, note_id=1, body="Updated note"
            )
            assert "note" in result

    @pytest.mark.asyncio
    async def test_update_missing_fields(self, tool):
        result = await tool.fn(action="update", change_id=10)
        assert "note_id and body" in result["error"]

    @pytest.mark.asyncio
    async def test_view(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"note": {"id": 5}})
            result = await tool.fn(action="view", change_id=10, note_id=5)
            assert "note" in result
            m.assert_called_once_with("changes/10/notes/5")

    @pytest.mark.asyncio
    async def test_view_missing_id(self, tool):
        result = await tool.fn(action="view", change_id=10)
        assert "note_id required" in result["error"]

    @pytest.mark.asyncio
    async def test_delete(self, tool):
        with patch(f"{self.MOD}.api_delete", new_callable=AsyncMock) as m:
            m.return_value = _no_content()
            result = await tool.fn(action="delete", change_id=10, note_id=5)
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_delete_missing_id(self, tool):
        result = await tool.fn(action="delete", change_id=10)
        assert "note_id required" in result["error"]

    @pytest.mark.asyncio
    async def test_unknown_action(self, tool):
        result = await tool.fn(action="xyz", change_id=10)
        assert "Unknown action" in result["error"]


# ═══════════════════════════════════════════════════════════════════════════
# Release Notes tool
# ═══════════════════════════════════════════════════════════════════════════
class TestReleaseNotesFull:
    """Test release notes: list, create, update, delete."""

    @pytest.fixture
    def tool(self):
        from freshservice_mcp.tools.releases import register_release_tools
        mcp = FastMCP("test")
        register_release_tools(mcp)
        return mcp._tool_manager._tools.get("manage_release_note")

    MOD = "freshservice_mcp.tools.releases"

    @pytest.mark.asyncio
    async def test_list(self, tool):
        if tool is None:
            pytest.skip("manage_release_note not registered")
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"notes": []})
            result = await tool.fn(action="list", release_id=1)
            assert "notes" in result

    @pytest.mark.asyncio
    async def test_create(self, tool):
        if tool is None:
            pytest.skip("manage_release_note not registered")
        with patch(f"{self.MOD}.api_post", new_callable=AsyncMock) as m:
            m.return_value = _ok({"note": {"id": 1}}, 201)
            result = await tool.fn(
                action="create", release_id=1, body="Release prep notes"
            )
            assert result.get("success") is True

    @pytest.mark.asyncio
    async def test_create_missing_body(self, tool):
        if tool is None:
            pytest.skip("manage_release_note not registered")
        result = await tool.fn(action="create", release_id=1)
        assert "body required" in result.get("error", "")
