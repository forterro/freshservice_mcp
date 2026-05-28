"""Comprehensive tests for changes tool actions."""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from mcp.server.fastmcp import FastMCP


def _mcp():
    from freshservice_mcp.tools.changes import register_changes_tools
    mcp = FastMCP("test")
    register_changes_tools(mcp)
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


MOD = "freshservice_mcp.tools.changes"


class TestManageChange:
    @pytest.fixture
    def tool(self):
        return _mcp()._tool_manager._tools["manage_change"]

    @pytest.mark.asyncio
    async def test_get_fields(self, tool):
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"change_fields": []})
            result = await tool.fn(action="get_fields")
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_get(self, tool):
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"change": {"id": 1}})
            result = await tool.fn(action="get", change_id=1)
            assert "change" in result or "error" not in result

    @pytest.mark.asyncio
    async def test_get_missing_id(self, tool):
        result = await tool.fn(action="get")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_create(self, tool):
        with patch(f"{MOD}.api_post", new_callable=AsyncMock) as m:
            m.return_value = _ok({"change": {"id": 1}}, 201)
            result = await tool.fn(
                action="create", subject="Change 1",
                description="Desc", change_type=1, priority=2,
                status=1, planned_start_date="2026-01-01",
                planned_end_date="2026-01-15", requester_id=1
            )
            assert "change" in result or result.get("success")

    @pytest.mark.asyncio
    async def test_create_missing_fields(self, tool):
        result = await tool.fn(action="create")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_update(self, tool):
        with patch(f"{MOD}.api_put", new_callable=AsyncMock) as m:
            m.return_value = _ok({"change": {"id": 1}})
            result = await tool.fn(action="update", change_id=1, subject="Updated")
            assert "change" in result or "error" not in result

    @pytest.mark.asyncio
    async def test_update_missing_id(self, tool):
        result = await tool.fn(action="update")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_close(self, tool):
        with patch(f"{MOD}.api_put", new_callable=AsyncMock) as m:
            m.return_value = _ok({"change": {"id": 1}})
            result = await tool.fn(action="close", change_id=1)
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_close_missing_id(self, tool):
        result = await tool.fn(action="close")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_delete(self, tool):
        with patch(f"{MOD}.api_delete", new_callable=AsyncMock) as m:
            m.return_value = _no_content()
            result = await tool.fn(action="delete", change_id=1)
            assert result.get("success") is True

    @pytest.mark.asyncio
    async def test_delete_missing_id(self, tool):
        result = await tool.fn(action="delete")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_move(self, tool):
        with patch(f"{MOD}.api_put", new_callable=AsyncMock) as m:
            m.return_value = _ok({"change": {"id": 1}})
            result = await tool.fn(action="move", change_id=1, workspace_id=2)
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_move_missing(self, tool):
        result = await tool.fn(action="move", change_id=1)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_unknown_action(self, tool):
        result = await tool.fn(action="invalid")
        assert "error" in result


class TestManageChangeNote:
    @pytest.fixture
    def tool(self):
        return _mcp()._tool_manager._tools["manage_change_note"]

    @pytest.mark.asyncio
    async def test_list(self, tool):
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"notes": []})
            result = await tool.fn(action="list", change_id=1)
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_create(self, tool):
        with patch(f"{MOD}.api_post", new_callable=AsyncMock) as m:
            m.return_value = _ok({"note": {"id": 1}}, 201)
            result = await tool.fn(action="create", change_id=1, body="Note text")
            assert "note" in result or result.get("success")

    @pytest.mark.asyncio
    async def test_view(self, tool):
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"note": {"id": 1}})
            result = await tool.fn(action="view", change_id=1, note_id=1)
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_update(self, tool):
        with patch(f"{MOD}.api_put", new_callable=AsyncMock) as m:
            m.return_value = _ok({"note": {"id": 1}})
            result = await tool.fn(action="update", change_id=1, note_id=1, body="Updated")
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_delete(self, tool):
        with patch(f"{MOD}.api_delete", new_callable=AsyncMock) as m:
            m.return_value = _no_content()
            result = await tool.fn(action="delete", change_id=1, note_id=1)
            assert result.get("success") is True


class TestManageChangeTask:
    @pytest.fixture
    def tool(self):
        return _mcp()._tool_manager._tools["manage_change_task"]

    @pytest.mark.asyncio
    async def test_list(self, tool):
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"tasks": []})
            result = await tool.fn(action="list", change_id=1)
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_create(self, tool):
        with patch(f"{MOD}.api_post", new_callable=AsyncMock) as m:
            m.return_value = _ok({"task": {"id": 1}}, 201)
            result = await tool.fn(action="create", change_id=1, title="Task 1", description="Do it")
            assert "task" in result or result.get("success")

    @pytest.mark.asyncio
    async def test_view(self, tool):
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"task": {"id": 1}})
            result = await tool.fn(action="view", change_id=1, task_id=1)
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_update(self, tool):
        with patch(f"{MOD}.api_put", new_callable=AsyncMock) as m:
            m.return_value = _ok({"task": {"id": 1}})
            result = await tool.fn(action="update", change_id=1, task_id=1, title="Updated")
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_delete(self, tool):
        with patch(f"{MOD}.api_delete", new_callable=AsyncMock) as m:
            m.return_value = _no_content()
            result = await tool.fn(action="delete", change_id=1, task_id=1)
            assert result.get("success") is True


class TestManageChangeTimeEntry:
    @pytest.fixture
    def tool(self):
        return _mcp()._tool_manager._tools["manage_change_time_entry"]

    @pytest.mark.asyncio
    async def test_list(self, tool):
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"time_entries": []})
            result = await tool.fn(action="list", change_id=1)
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_create(self, tool):
        with patch(f"{MOD}.api_post", new_callable=AsyncMock) as m:
            m.return_value = _ok({"time_entry": {"id": 1}}, 201)
            result = await tool.fn(action="create", change_id=1, te_agent_id=1, time_spent="01:00", note="Work done")
            assert "time_entry" in result or result.get("success")

    @pytest.mark.asyncio
    async def test_view(self, tool):
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"time_entry": {"id": 1}})
            result = await tool.fn(action="view", change_id=1, time_entry_id=1)
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_update(self, tool):
        with patch(f"{MOD}.api_put", new_callable=AsyncMock) as m:
            m.return_value = _ok({"time_entry": {"id": 1}})
            result = await tool.fn(action="update", change_id=1, time_entry_id=1, time_spent="02:00")
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_delete(self, tool):
        with patch(f"{MOD}.api_delete", new_callable=AsyncMock) as m:
            m.return_value = _no_content()
            result = await tool.fn(action="delete", change_id=1, time_entry_id=1)
            assert result.get("success") is True


class TestManageChangeApproval:
    @pytest.fixture
    def tool(self):
        return _mcp()._tool_manager._tools["manage_change_approval"]

    @pytest.mark.asyncio
    async def test_list_groups(self, tool):
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"approval_groups": []})
            result = await tool.fn(action="list_groups", change_id=1)
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_create_group(self, tool):
        with patch(f"{MOD}.api_post", new_callable=AsyncMock) as m:
            m.return_value = _ok({"approval_group": {"id": 1}}, 201)
            result = await tool.fn(action="create_group", change_id=1, name="Approvers", approver_ids=[10])
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_create_group_missing(self, tool):
        result = await tool.fn(action="create_group", change_id=1)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_update_group(self, tool):
        with patch(f"{MOD}.api_put", new_callable=AsyncMock) as m:
            m.return_value = _ok({"approval_group": {"id": 1}})
            result = await tool.fn(action="update_group", change_id=1, approval_group_id=1, approver_ids=[20])
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_update_group_missing(self, tool):
        result = await tool.fn(action="update_group", change_id=1)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_cancel_group(self, tool):
        with patch(f"{MOD}.api_put", new_callable=AsyncMock) as m:
            m.return_value = _ok({"success": True})
            result = await tool.fn(action="cancel_group", change_id=1, approval_group_id=1)
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_cancel_group_missing(self, tool):
        result = await tool.fn(action="cancel_group", change_id=1)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_list(self, tool):
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"approvals": []})
            result = await tool.fn(action="list", change_id=1)
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_view(self, tool):
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"approval": {"id": 1}})
            result = await tool.fn(action="view", change_id=1, approval_id=1)
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_remind(self, tool):
        with patch(f"{MOD}.api_put", new_callable=AsyncMock) as m:
            m.return_value = _ok({"success": True})
            result = await tool.fn(action="remind", change_id=1, approval_id=1)
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_remind_missing(self, tool):
        result = await tool.fn(action="remind", change_id=1)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_cancel(self, tool):
        with patch(f"{MOD}.api_put", new_callable=AsyncMock) as m:
            m.return_value = _ok({"success": True})
            result = await tool.fn(action="cancel", change_id=1, approval_id=1)
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_cancel_missing(self, tool):
        result = await tool.fn(action="cancel", change_id=1)
        assert "error" in result
