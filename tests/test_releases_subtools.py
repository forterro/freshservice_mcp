"""Functional tests for release sub-tools: notes, tasks, time entries.

Verifies:
- Correct API endpoint construction (releases/{id}/notes|tasks|time_entries)
- Payload building with optional fields for tasks and time entries
- Required field validation
- Delete 204 handling
- Error propagation from API failures
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from mcp.server.fastmcp import FastMCP
from freshservice_mcp.tools.releases import register_release_tools

MOD = "freshservice_mcp.tools.releases"


def _resp(data=None, status=200):
    r = MagicMock()
    r.status_code = status
    r.json.return_value = data or {}
    r.raise_for_status = MagicMock()
    r.headers = {"Link": ""}
    return r


def _raise(*a, **kw):
    raise Exception("API error")


@pytest.fixture
def tools():
    mcp = FastMCP("test")
    register_release_tools(mcp)
    return mcp


def _t(mcp, name):
    return mcp._tool_manager._tools[name]


# ═══════════════════════════════════════════════════════════════════════════
# Release Notes
# ═══════════════════════════════════════════════════════════════════════════


class TestReleaseNote:
    @pytest.mark.asyncio
    async def test_list(self, tools):
        tool = _t(tools, "manage_release_note")
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _resp({"notes": [{"id": 1}]})
            result = await tool.fn(action="list", release_id=10)
            m.assert_called_once_with("releases/10/notes")
            assert result == {"notes": [{"id": 1}]}

    @pytest.mark.asyncio
    async def test_get(self, tools):
        tool = _t(tools, "manage_release_note")
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _resp({"note": {"id": 5}})
            await tool.fn(action="get", release_id=10, note_id=5)
            m.assert_called_once_with("releases/10/notes/5")

    @pytest.mark.asyncio
    async def test_get_requires_note_id(self, tools):
        tool = _t(tools, "manage_release_note")
        result = await tool.fn(action="get", release_id=10)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_create_sends_body(self, tools):
        tool = _t(tools, "manage_release_note")
        with patch(f"{MOD}.api_post", new_callable=AsyncMock) as m:
            m.return_value = _resp({"note": {"id": 6}}, 201)
            result = await tool.fn(action="create", release_id=10, body="<p>Done</p>")
            m.assert_called_once_with("releases/10/notes", json={"body": "<p>Done</p>"})
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_create_requires_body(self, tools):
        tool = _t(tools, "manage_release_note")
        result = await tool.fn(action="create", release_id=10)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_update(self, tools):
        tool = _t(tools, "manage_release_note")
        with patch(f"{MOD}.api_put", new_callable=AsyncMock) as m:
            m.return_value = _resp({"note": {"id": 5}})
            result = await tool.fn(action="update", release_id=10, note_id=5, body="Updated")
            m.assert_called_once_with("releases/10/notes/5", json={"body": "Updated"})
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_update_requires_both(self, tools):
        tool = _t(tools, "manage_release_note")
        result = await tool.fn(action="update", release_id=10, note_id=5)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_delete(self, tools):
        tool = _t(tools, "manage_release_note")
        with patch(f"{MOD}.api_delete", new_callable=AsyncMock) as m:
            m.return_value = _resp(status=204)
            result = await tool.fn(action="delete", release_id=10, note_id=5)
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_delete_requires_note_id(self, tools):
        tool = _t(tools, "manage_release_note")
        result = await tool.fn(action="delete", release_id=10)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_unknown_action(self, tools):
        tool = _t(tools, "manage_release_note")
        result = await tool.fn(action="archive", release_id=10)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_list_api_error(self, tools):
        tool = _t(tools, "manage_release_note")
        with patch(f"{MOD}.api_get", new_callable=AsyncMock, side_effect=_raise):
            result = await tool.fn(action="list", release_id=10)
            assert "error" in result


# ═══════════════════════════════════════════════════════════════════════════
# Release Tasks — payload building with optional fields
# ═══════════════════════════════════════════════════════════════════════════


class TestReleaseTask:
    @pytest.mark.asyncio
    async def test_create_builds_full_payload(self, tools):
        """All optional fields should be included in create payload."""
        tool = _t(tools, "manage_release_task")
        with patch(f"{MOD}.api_post", new_callable=AsyncMock) as m:
            m.return_value = _resp({"task": {"id": 1}}, 201)
            result = await tool.fn(
                action="create", release_id=10, title="Deploy",
                description="Roll out", status=2, due_date="2025-06-01",
                notify_before=24, group_id=5,
            )
            payload = m.call_args[1]["json"]
            assert payload == {
                "title": "Deploy",
                "description": "Roll out",
                "status": 2,
                "due_date": "2025-06-01",
                "notify_before": 24,
                "group_id": 5,
            }
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_create_requires_title(self, tools):
        tool = _t(tools, "manage_release_task")
        result = await tool.fn(action="create", release_id=10)
        assert "error" in result
        assert "title" in result["error"]

    @pytest.mark.asyncio
    async def test_list(self, tools):
        tool = _t(tools, "manage_release_task")
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _resp({"tasks": []})
            await tool.fn(action="list", release_id=10)
            m.assert_called_once_with("releases/10/tasks")

    @pytest.mark.asyncio
    async def test_get(self, tools):
        tool = _t(tools, "manage_release_task")
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _resp({"task": {"id": 3}})
            await tool.fn(action="get", release_id=10, task_id=3)
            m.assert_called_once_with("releases/10/tasks/3")

    @pytest.mark.asyncio
    async def test_update_partial(self, tools):
        """Update should only send provided fields."""
        tool = _t(tools, "manage_release_task")
        with patch(f"{MOD}.api_put", new_callable=AsyncMock) as m:
            m.return_value = _resp({"task": {"id": 3}})
            await tool.fn(action="update", release_id=10, task_id=3, status=3)
            payload = m.call_args[1]["json"]
            assert payload == {"status": 3}

    @pytest.mark.asyncio
    async def test_delete(self, tools):
        tool = _t(tools, "manage_release_task")
        with patch(f"{MOD}.api_delete", new_callable=AsyncMock) as m:
            m.return_value = _resp(status=204)
            result = await tool.fn(action="delete", release_id=10, task_id=3)
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_delete_requires_task_id(self, tools):
        tool = _t(tools, "manage_release_task")
        result = await tool.fn(action="delete", release_id=10)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_unknown_action(self, tools):
        tool = _t(tools, "manage_release_task")
        result = await tool.fn(action="bogus", release_id=10)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_create_api_error(self, tools):
        tool = _t(tools, "manage_release_task")
        with patch(f"{MOD}.api_post", new_callable=AsyncMock, side_effect=_raise):
            result = await tool.fn(action="create", release_id=10, title="T")
            assert "error" in result


# ═══════════════════════════════════════════════════════════════════════════
# Release Time Entries — verifies billable flag and optional fields
# ═══════════════════════════════════════════════════════════════════════════


class TestReleaseTimeEntry:
    @pytest.mark.asyncio
    async def test_create_with_all_fields(self, tools):
        """All optional fields including billable should appear in payload."""
        tool = _t(tools, "manage_release_time_entry")
        with patch(f"{MOD}.api_post", new_callable=AsyncMock) as m:
            m.return_value = _resp({"time_entry": {"id": 1}}, 201)
            result = await tool.fn(
                action="create", release_id=10,
                time_spent="03:30", agent_id=42, note="Deployment work",
                executed_at="2025-01-15T14:00:00Z", task_id=7, billable=True,
            )
            payload = m.call_args[1]["json"]
            assert payload["time_spent"] == "03:30"
            assert payload["agent_id"] == 42
            assert payload["note"] == "Deployment work"
            assert payload["executed_at"] == "2025-01-15T14:00:00Z"
            assert payload["task_id"] == 7
            assert payload["billable"] is True
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_create_requires_time_spent(self, tools):
        tool = _t(tools, "manage_release_time_entry")
        result = await tool.fn(action="create", release_id=10, note="Work")
        assert "error" in result
        assert "time_spent" in result["error"]

    @pytest.mark.asyncio
    async def test_list(self, tools):
        tool = _t(tools, "manage_release_time_entry")
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _resp({"time_entries": []})
            await tool.fn(action="list", release_id=10)
            m.assert_called_once_with("releases/10/time_entries")

    @pytest.mark.asyncio
    async def test_get(self, tools):
        tool = _t(tools, "manage_release_time_entry")
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _resp({"time_entry": {"id": 5}})
            await tool.fn(action="get", release_id=10, time_entry_id=5)
            m.assert_called_once_with("releases/10/time_entries/5")

    @pytest.mark.asyncio
    async def test_update_with_billable(self, tools):
        """Update should include billable when explicitly set."""
        tool = _t(tools, "manage_release_time_entry")
        with patch(f"{MOD}.api_put", new_callable=AsyncMock) as m:
            m.return_value = _resp({"time_entry": {"id": 5}})
            await tool.fn(
                action="update", release_id=10, time_entry_id=5,
                note="Updated note", billable=False,
            )
            payload = m.call_args[1]["json"]
            assert payload == {"note": "Updated note", "billable": False}

    @pytest.mark.asyncio
    async def test_delete(self, tools):
        tool = _t(tools, "manage_release_time_entry")
        with patch(f"{MOD}.api_delete", new_callable=AsyncMock) as m:
            m.return_value = _resp(status=204)
            result = await tool.fn(action="delete", release_id=10, time_entry_id=5)
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_delete_requires_id(self, tools):
        tool = _t(tools, "manage_release_time_entry")
        result = await tool.fn(action="delete", release_id=10)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_unknown_action(self, tools):
        tool = _t(tools, "manage_release_time_entry")
        result = await tool.fn(action="bogus", release_id=10)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_get_api_error(self, tools):
        tool = _t(tools, "manage_release_time_entry")
        with patch(f"{MOD}.api_get", new_callable=AsyncMock, side_effect=_raise):
            result = await tool.fn(action="get", release_id=10, time_entry_id=5)
            assert "error" in result
