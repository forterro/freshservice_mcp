"""Error handling tests for changes, problems, and projects tool modules.

Targets the uncovered except blocks across all CRUD actions and sub-tools.
Uses parametrized tests for efficiency — each test verifies that API failures
are caught and returned as {"error": "..."} dicts.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from mcp.server.fastmcp import FastMCP
from freshservice_mcp.tools.changes import register_changes_tools
from freshservice_mcp.tools.problems import register_problem_tools
from freshservice_mcp.tools.projects import register_project_tools

MOD_CHANGES = "freshservice_mcp.tools.changes"
MOD_PROBLEMS = "freshservice_mcp.tools.problems"
MOD_PROJECTS = "freshservice_mcp.tools.projects"


def _raise(*a, **kw):
    raise Exception("API error")


def _resp(data=None, status=200):
    r = MagicMock()
    r.status_code = status
    r.json.return_value = data or {}
    r.raise_for_status = MagicMock()
    r.headers = {"Link": ""}
    return r


def _t(mcp, name):
    return mcp._tool_manager._tools[name]


# ═══════════════════════════════════════════════════════════════════════════
# Changes — main CRUD + sub-tools error paths
# ═══════════════════════════════════════════════════════════════════════════


@pytest.fixture
def change_tools():
    mcp = FastMCP("test")
    register_changes_tools(mcp)
    return mcp


class TestChangeMainErrors:
    """Error paths in manage_change — list/get/create/update/delete/filter/get_fields."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("action,kwargs", [
        ("list", {}),
        ("get", {"change_id": 1}),
        ("filter", {"query": "status:1"}),
        ("get_fields", {}),
    ])
    async def test_get_actions_error(self, change_tools, action, kwargs):
        tool = _t(change_tools, "manage_change")
        with patch(f"{MOD_CHANGES}.api_get", new_callable=AsyncMock, side_effect=_raise):
            result = await tool.fn(action=action, **kwargs)
            assert "error" in result

    @pytest.mark.asyncio
    async def test_create_error(self, change_tools):
        tool = _t(change_tools, "manage_change")
        with patch(f"{MOD_CHANGES}.api_post", new_callable=AsyncMock, side_effect=_raise):
            result = await tool.fn(
                action="create", subject="C", description="D",
                planned_start_date="2025-01-01", planned_end_date="2025-01-02",
                change_type=1,
            )
            assert "error" in result

    @pytest.mark.asyncio
    async def test_update_error(self, change_tools):
        tool = _t(change_tools, "manage_change")
        with patch(f"{MOD_CHANGES}.api_put", new_callable=AsyncMock, side_effect=_raise):
            result = await tool.fn(action="update", change_id=1, subject="X")
            assert "error" in result

    @pytest.mark.asyncio
    async def test_delete_error(self, change_tools):
        tool = _t(change_tools, "manage_change")
        with patch(f"{MOD_CHANGES}.api_delete", new_callable=AsyncMock, side_effect=_raise):
            result = await tool.fn(action="delete", change_id=1)
            assert "error" in result


class TestChangeNoteErrors:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("action,kwargs", [
        ("list", {"change_id": 1}),
        ("get", {"change_id": 1, "note_id": 2}),
    ])
    async def test_get_error(self, change_tools, action, kwargs):
        tool = _t(change_tools, "manage_change_note")
        with patch(f"{MOD_CHANGES}.api_get", new_callable=AsyncMock, side_effect=_raise):
            result = await tool.fn(action=action, **kwargs)
            assert "error" in result

    @pytest.mark.asyncio
    async def test_create_error(self, change_tools):
        tool = _t(change_tools, "manage_change_note")
        with patch(f"{MOD_CHANGES}.api_post", new_callable=AsyncMock, side_effect=_raise):
            result = await tool.fn(action="create", change_id=1, body="<p>X</p>")
            assert "error" in result

    @pytest.mark.asyncio
    async def test_update_error(self, change_tools):
        tool = _t(change_tools, "manage_change_note")
        with patch(f"{MOD_CHANGES}.api_put", new_callable=AsyncMock, side_effect=_raise):
            result = await tool.fn(action="update", change_id=1, note_id=2, body="Y")
            assert "error" in result

    @pytest.mark.asyncio
    async def test_delete_error(self, change_tools):
        tool = _t(change_tools, "manage_change_note")
        with patch(f"{MOD_CHANGES}.api_delete", new_callable=AsyncMock, side_effect=_raise):
            result = await tool.fn(action="delete", change_id=1, note_id=2)
            assert "error" in result


class TestChangeTaskErrors:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("action,kwargs", [
        ("list", {"change_id": 1}),
        ("get", {"change_id": 1, "task_id": 2}),
    ])
    async def test_get_error(self, change_tools, action, kwargs):
        tool = _t(change_tools, "manage_change_task")
        with patch(f"{MOD_CHANGES}.api_get", new_callable=AsyncMock, side_effect=_raise):
            result = await tool.fn(action=action, **kwargs)
            assert "error" in result

    @pytest.mark.asyncio
    async def test_create_error(self, change_tools):
        tool = _t(change_tools, "manage_change_task")
        with patch(f"{MOD_CHANGES}.api_post", new_callable=AsyncMock, side_effect=_raise):
            result = await tool.fn(action="create", change_id=1, title="T")
            assert "error" in result

    @pytest.mark.asyncio
    async def test_update_error(self, change_tools):
        tool = _t(change_tools, "manage_change_task")
        with patch(f"{MOD_CHANGES}.api_put", new_callable=AsyncMock, side_effect=_raise):
            result = await tool.fn(action="update", change_id=1, task_id=2, task_status=3)
            assert "error" in result

    @pytest.mark.asyncio
    async def test_delete_error(self, change_tools):
        tool = _t(change_tools, "manage_change_task")
        with patch(f"{MOD_CHANGES}.api_delete", new_callable=AsyncMock, side_effect=_raise):
            result = await tool.fn(action="delete", change_id=1, task_id=2)
            assert "error" in result


class TestChangeTimeEntryErrors:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("action,kwargs", [
        ("list", {"change_id": 1}),
        ("get", {"change_id": 1, "time_entry_id": 2}),
    ])
    async def test_get_error(self, change_tools, action, kwargs):
        tool = _t(change_tools, "manage_change_time_entry")
        with patch(f"{MOD_CHANGES}.api_get", new_callable=AsyncMock, side_effect=_raise):
            result = await tool.fn(action=action, **kwargs)
            assert "error" in result

    @pytest.mark.asyncio
    async def test_create_error(self, change_tools):
        tool = _t(change_tools, "manage_change_time_entry")
        with patch(f"{MOD_CHANGES}.api_post", new_callable=AsyncMock, side_effect=_raise):
            result = await tool.fn(action="create", change_id=1, time_spent="01:00")
            assert "error" in result

    @pytest.mark.asyncio
    async def test_update_error(self, change_tools):
        tool = _t(change_tools, "manage_change_time_entry")
        with patch(f"{MOD_CHANGES}.api_put", new_callable=AsyncMock, side_effect=_raise):
            result = await tool.fn(action="update", change_id=1, time_entry_id=2, note="X")
            assert "error" in result

    @pytest.mark.asyncio
    async def test_delete_error(self, change_tools):
        tool = _t(change_tools, "manage_change_time_entry")
        with patch(f"{MOD_CHANGES}.api_delete", new_callable=AsyncMock, side_effect=_raise):
            result = await tool.fn(action="delete", change_id=1, time_entry_id=2)
            assert "error" in result


class TestChangeApprovalErrors:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("action,kwargs", [
        ("list_groups", {"change_id": 1}),
        ("list", {"change_id": 1}),
    ])
    async def test_get_error(self, change_tools, action, kwargs):
        tool = _t(change_tools, "manage_change_approval")
        with patch(f"{MOD_CHANGES}.api_get", new_callable=AsyncMock, side_effect=_raise):
            result = await tool.fn(action=action, **kwargs)
            assert "error" in result

    @pytest.mark.asyncio
    async def test_create_group_error(self, change_tools):
        tool = _t(change_tools, "manage_change_approval")
        with patch(f"{MOD_CHANGES}.api_post", new_callable=AsyncMock, side_effect=_raise):
            result = await tool.fn(
                action="create_group", change_id=1, name="G", approver_ids=[5],
            )
            assert "error" in result

    @pytest.mark.asyncio
    async def test_update_group_error(self, change_tools):
        tool = _t(change_tools, "manage_change_approval")
        with patch(f"{MOD_CHANGES}.api_put", new_callable=AsyncMock, side_effect=_raise):
            result = await tool.fn(
                action="update_group", change_id=1, approval_group_id=2, name="H",
            )
            assert "error" in result

    @pytest.mark.asyncio
    async def test_cancel_group_error(self, change_tools):
        tool = _t(change_tools, "manage_change_approval")
        with patch(f"{MOD_CHANGES}.api_put", new_callable=AsyncMock, side_effect=_raise):
            result = await tool.fn(action="cancel_group", change_id=1, approval_group_id=2)
            assert "error" in result

    @pytest.mark.asyncio
    async def test_remind_error(self, change_tools):
        tool = _t(change_tools, "manage_change_approval")
        with patch(f"{MOD_CHANGES}.api_put", new_callable=AsyncMock, side_effect=_raise):
            result = await tool.fn(action="remind", change_id=1, approval_id=2)
            assert "error" in result

    @pytest.mark.asyncio
    async def test_cancel_error(self, change_tools):
        tool = _t(change_tools, "manage_change_approval")
        with patch(f"{MOD_CHANGES}.api_put", new_callable=AsyncMock, side_effect=_raise):
            result = await tool.fn(action="cancel", change_id=1, approval_id=2)
            assert "error" in result

    @pytest.mark.asyncio
    async def test_set_chain_rule_error(self, change_tools):
        tool = _t(change_tools, "manage_change_approval")
        with patch(f"{MOD_CHANGES}.api_put", new_callable=AsyncMock, side_effect=_raise):
            result = await tool.fn(
                action="set_chain_rule", change_id=1, approval_chain_type="parallel",
            )
            assert "error" in result


# ═══════════════════════════════════════════════════════════════════════════
# Problems — main CRUD + sub-tools error paths
# ═══════════════════════════════════════════════════════════════════════════


@pytest.fixture
def problem_tools():
    mcp = FastMCP("test")
    register_problem_tools(mcp)
    return mcp


class TestProblemMainErrors:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("action,kwargs", [
        ("list", {}),
        ("get", {"problem_id": 1}),
        ("filter", {"query": "status:1"}),
        ("get_fields", {}),
    ])
    async def test_get_actions_error(self, problem_tools, action, kwargs):
        tool = _t(problem_tools, "manage_problem")
        with patch(f"{MOD_PROBLEMS}.api_get", new_callable=AsyncMock, side_effect=_raise):
            result = await tool.fn(action=action, **kwargs)
            assert "error" in result

    @pytest.mark.asyncio
    async def test_create_error(self, problem_tools):
        tool = _t(problem_tools, "manage_problem")
        with patch(f"{MOD_PROBLEMS}.api_post", new_callable=AsyncMock, side_effect=_raise):
            result = await tool.fn(
                action="create", subject="P", description="D",
                priority=1, status=1, impact=1,
            )
            assert "error" in result

    @pytest.mark.asyncio
    async def test_update_error(self, problem_tools):
        tool = _t(problem_tools, "manage_problem")
        with patch(f"{MOD_PROBLEMS}.api_put", new_callable=AsyncMock, side_effect=_raise):
            result = await tool.fn(action="update", problem_id=1, subject="X")
            assert "error" in result

    @pytest.mark.asyncio
    async def test_delete_error(self, problem_tools):
        tool = _t(problem_tools, "manage_problem")
        with patch(f"{MOD_PROBLEMS}.api_delete", new_callable=AsyncMock, side_effect=_raise):
            result = await tool.fn(action="delete", problem_id=1)
            assert "error" in result

    @pytest.mark.asyncio
    async def test_restore_error(self, problem_tools):
        tool = _t(problem_tools, "manage_problem")
        with patch(f"{MOD_PROBLEMS}.api_put", new_callable=AsyncMock, side_effect=_raise):
            result = await tool.fn(action="restore", problem_id=1)
            assert "error" in result


class TestProblemNoteErrors:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("action,kwargs", [
        ("list", {"problem_id": 1}),
        ("get", {"problem_id": 1, "note_id": 2}),
    ])
    async def test_get_error(self, problem_tools, action, kwargs):
        tool = _t(problem_tools, "manage_problem_note")
        with patch(f"{MOD_PROBLEMS}.api_get", new_callable=AsyncMock, side_effect=_raise):
            result = await tool.fn(action=action, **kwargs)
            assert "error" in result

    @pytest.mark.asyncio
    async def test_create_error(self, problem_tools):
        tool = _t(problem_tools, "manage_problem_note")
        with patch(f"{MOD_PROBLEMS}.api_post", new_callable=AsyncMock, side_effect=_raise):
            result = await tool.fn(action="create", problem_id=1, body="<p>N</p>")
            assert "error" in result

    @pytest.mark.asyncio
    async def test_update_error(self, problem_tools):
        tool = _t(problem_tools, "manage_problem_note")
        with patch(f"{MOD_PROBLEMS}.api_put", new_callable=AsyncMock, side_effect=_raise):
            result = await tool.fn(action="update", problem_id=1, note_id=2, body="Y")
            assert "error" in result

    @pytest.mark.asyncio
    async def test_delete_error(self, problem_tools):
        tool = _t(problem_tools, "manage_problem_note")
        with patch(f"{MOD_PROBLEMS}.api_delete", new_callable=AsyncMock, side_effect=_raise):
            result = await tool.fn(action="delete", problem_id=1, note_id=2)
            assert "error" in result


class TestProblemTaskErrors:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("action,kwargs", [
        ("list", {"problem_id": 1}),
        ("get", {"problem_id": 1, "task_id": 2}),
    ])
    async def test_get_error(self, problem_tools, action, kwargs):
        tool = _t(problem_tools, "manage_problem_task")
        with patch(f"{MOD_PROBLEMS}.api_get", new_callable=AsyncMock, side_effect=_raise):
            result = await tool.fn(action=action, **kwargs)
            assert "error" in result

    @pytest.mark.asyncio
    async def test_create_error(self, problem_tools):
        tool = _t(problem_tools, "manage_problem_task")
        with patch(f"{MOD_PROBLEMS}.api_post", new_callable=AsyncMock, side_effect=_raise):
            result = await tool.fn(action="create", problem_id=1, title="T")
            assert "error" in result

    @pytest.mark.asyncio
    async def test_update_error(self, problem_tools):
        tool = _t(problem_tools, "manage_problem_task")
        with patch(f"{MOD_PROBLEMS}.api_put", new_callable=AsyncMock, side_effect=_raise):
            result = await tool.fn(action="update", problem_id=1, task_id=2, status=3)
            assert "error" in result

    @pytest.mark.asyncio
    async def test_delete_error(self, problem_tools):
        tool = _t(problem_tools, "manage_problem_task")
        with patch(f"{MOD_PROBLEMS}.api_delete", new_callable=AsyncMock, side_effect=_raise):
            result = await tool.fn(action="delete", problem_id=1, task_id=2)
            assert "error" in result


class TestProblemTimeEntryErrors:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("action,kwargs", [
        ("list", {"problem_id": 1}),
        ("get", {"problem_id": 1, "time_entry_id": 2}),
    ])
    async def test_get_error(self, problem_tools, action, kwargs):
        tool = _t(problem_tools, "manage_problem_time_entry")
        with patch(f"{MOD_PROBLEMS}.api_get", new_callable=AsyncMock, side_effect=_raise):
            result = await tool.fn(action=action, **kwargs)
            assert "error" in result

    @pytest.mark.asyncio
    async def test_create_error(self, problem_tools):
        tool = _t(problem_tools, "manage_problem_time_entry")
        with patch(f"{MOD_PROBLEMS}.api_post", new_callable=AsyncMock, side_effect=_raise):
            result = await tool.fn(action="create", problem_id=1, time_spent="01:00")
            assert "error" in result

    @pytest.mark.asyncio
    async def test_update_error(self, problem_tools):
        tool = _t(problem_tools, "manage_problem_time_entry")
        with patch(f"{MOD_PROBLEMS}.api_put", new_callable=AsyncMock, side_effect=_raise):
            result = await tool.fn(action="update", problem_id=1, time_entry_id=2, note="Y")
            assert "error" in result

    @pytest.mark.asyncio
    async def test_delete_error(self, problem_tools):
        tool = _t(problem_tools, "manage_problem_time_entry")
        with patch(f"{MOD_PROBLEMS}.api_delete", new_callable=AsyncMock, side_effect=_raise):
            result = await tool.fn(action="delete", problem_id=1, time_entry_id=2)
            assert "error" in result


# ═══════════════════════════════════════════════════════════════════════════
# Projects — main CRUD + sub-tools error paths
# ═══════════════════════════════════════════════════════════════════════════


@pytest.fixture
def project_tools():
    mcp = FastMCP("test")
    register_project_tools(mcp)
    return mcp


class TestProjectMainErrors:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("action,kwargs", [
        ("list", {}),
        ("get", {"project_id": 1}),
        ("get_fields", {}),
    ])
    async def test_get_actions_error(self, project_tools, action, kwargs):
        tool = _t(project_tools, "manage_project")
        with patch(f"{MOD_PROJECTS}.api_get", new_callable=AsyncMock, side_effect=_raise):
            result = await tool.fn(action=action, **kwargs)
            assert "error" in result

    @pytest.mark.asyncio
    async def test_create_error(self, project_tools):
        tool = _t(project_tools, "manage_project")
        with patch(f"{MOD_PROJECTS}.api_post", new_callable=AsyncMock, side_effect=_raise):
            result = await tool.fn(
                action="create", name="P", description="D",
                project_type=1, start_date="2025-01-01", end_date="2025-12-31",
            )
            assert "error" in result

    @pytest.mark.asyncio
    async def test_update_error(self, project_tools):
        tool = _t(project_tools, "manage_project")
        with patch(f"{MOD_PROJECTS}.api_put", new_callable=AsyncMock, side_effect=_raise):
            result = await tool.fn(action="update", project_id=1, name="X")
            assert "error" in result

    @pytest.mark.asyncio
    async def test_delete_error(self, project_tools):
        tool = _t(project_tools, "manage_project")
        with patch(f"{MOD_PROJECTS}.api_delete", new_callable=AsyncMock, side_effect=_raise):
            result = await tool.fn(action="delete", project_id=1)
            assert "error" in result

    @pytest.mark.asyncio
    async def test_archive_error(self, project_tools):
        tool = _t(project_tools, "manage_project")
        with patch(f"{MOD_PROJECTS}.api_post", new_callable=AsyncMock, side_effect=_raise):
            result = await tool.fn(action="archive", project_id=1)
            assert "error" in result


class TestProjectTaskErrors:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("action,kwargs", [
        ("list", {"project_id": 1}),
        ("get", {"project_id": 1, "task_id": 2}),
    ])
    async def test_get_error(self, project_tools, action, kwargs):
        tool = _t(project_tools, "manage_project_task")
        with patch(f"{MOD_PROJECTS}.api_get", new_callable=AsyncMock, side_effect=_raise):
            result = await tool.fn(action=action, **kwargs)
            assert "error" in result

    @pytest.mark.asyncio
    async def test_create_error(self, project_tools):
        tool = _t(project_tools, "manage_project_task")
        with patch(f"{MOD_PROJECTS}.api_post", new_callable=AsyncMock, side_effect=_raise):
            result = await tool.fn(action="create", project_id=1, title="T", version_id=1)
            assert "error" in result

    @pytest.mark.asyncio
    async def test_update_error(self, project_tools):
        tool = _t(project_tools, "manage_project_task")
        with patch(f"{MOD_PROJECTS}.api_put", new_callable=AsyncMock, side_effect=_raise):
            result = await tool.fn(action="update", project_id=1, task_id=2, title="X")
            assert "error" in result

    @pytest.mark.asyncio
    async def test_delete_error(self, project_tools):
        tool = _t(project_tools, "manage_project_task")
        with patch(f"{MOD_PROJECTS}.api_delete", new_callable=AsyncMock, side_effect=_raise):
            result = await tool.fn(action="delete", project_id=1, task_id=2)
            assert "error" in result


class TestProjectNoteErrors:
    """Notes are actions within manage_project_task."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("action,kwargs", [
        ("list_notes", {"project_id": 1, "task_id": 2}),
    ])
    async def test_get_error(self, project_tools, action, kwargs):
        tool = _t(project_tools, "manage_project_task")
        with patch(f"{MOD_PROJECTS}.api_get", new_callable=AsyncMock, side_effect=_raise):
            result = await tool.fn(action=action, **kwargs)
            assert "error" in result

    @pytest.mark.asyncio
    async def test_create_error(self, project_tools):
        tool = _t(project_tools, "manage_project_task")
        with patch(f"{MOD_PROJECTS}.api_post", new_callable=AsyncMock, side_effect=_raise):
            result = await tool.fn(action="create_note", project_id=1, task_id=2, content="N")
            assert "error" in result

    @pytest.mark.asyncio
    async def test_update_error(self, project_tools):
        tool = _t(project_tools, "manage_project_task")
        with patch(f"{MOD_PROJECTS}.api_put", new_callable=AsyncMock, side_effect=_raise):
            result = await tool.fn(action="update_note", project_id=1, task_id=2, note_id=3, content="Y")
            assert "error" in result

    @pytest.mark.asyncio
    async def test_delete_error(self, project_tools):
        tool = _t(project_tools, "manage_project_task")
        with patch(f"{MOD_PROJECTS}.api_delete", new_callable=AsyncMock, side_effect=_raise):
            result = await tool.fn(action="delete_note", project_id=1, task_id=2, note_id=3)
            assert "error" in result
