"""Comprehensive tests for problems tool actions."""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from mcp.server.fastmcp import FastMCP


def _mcp():
    from freshservice_mcp.tools.problems import register_problem_tools
    mcp = FastMCP("test")
    register_problem_tools(mcp)
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


MOD = "freshservice_mcp.tools.problems"


class TestManageProblem:
    @pytest.fixture
    def tool(self):
        return _mcp()._tool_manager._tools["manage_problem"]

    @pytest.mark.asyncio
    async def test_list(self, tool):
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"problems": [{"id": 1}]})
            result = await tool.fn(action="list")
            assert "problems" in result or "error" not in result

    @pytest.mark.asyncio
    async def test_get(self, tool):
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"problem": {"id": 1}})
            result = await tool.fn(action="get", problem_id=1)
            assert "problem" in result or "error" not in result

    @pytest.mark.asyncio
    async def test_get_missing_id(self, tool):
        result = await tool.fn(action="get")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_create(self, tool):
        with patch(f"{MOD}.api_post", new_callable=AsyncMock) as m:
            m.return_value = _ok({"problem": {"id": 1}}, 201)
            result = await tool.fn(
                action="create", subject="Problem 1",
                description="Desc", priority=2, status=1,
                requester_id=1, impact=1, due_by="2026-06-01"
            )
            assert "problem" in result or result.get("success")

    @pytest.mark.asyncio
    async def test_create_missing_fields(self, tool):
        result = await tool.fn(action="create")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_update(self, tool):
        with patch(f"{MOD}.api_put", new_callable=AsyncMock) as m:
            m.return_value = _ok({"problem": {"id": 1}})
            result = await tool.fn(action="update", problem_id=1, subject="Updated")
            assert "problem" in result or "error" not in result

    @pytest.mark.asyncio
    async def test_update_missing_id(self, tool):
        result = await tool.fn(action="update")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_delete(self, tool):
        with patch(f"{MOD}.api_delete", new_callable=AsyncMock) as m:
            m.return_value = _no_content()
            result = await tool.fn(action="delete", problem_id=1)
            assert result.get("success") is True

    @pytest.mark.asyncio
    async def test_delete_missing_id(self, tool):
        result = await tool.fn(action="delete")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_close(self, tool):
        with patch(f"{MOD}.api_put", new_callable=AsyncMock) as m:
            m.return_value = _ok({"problem": {"id": 1}})
            result = await tool.fn(action="close", problem_id=1)
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_close_missing_id(self, tool):
        result = await tool.fn(action="close")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_restore(self, tool):
        with patch(f"{MOD}.api_put", new_callable=AsyncMock) as m:
            m.return_value = _ok({"problem": {"id": 1}})
            result = await tool.fn(action="restore", problem_id=1)
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_restore_missing_id(self, tool):
        result = await tool.fn(action="restore")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_filter(self, tool):
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"problems": []})
            result = await tool.fn(action="filter", query='"status:1"')
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_filter_missing_query(self, tool):
        result = await tool.fn(action="filter")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_get_fields(self, tool):
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"problem_fields": []})
            result = await tool.fn(action="get_fields")
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_unknown_action(self, tool):
        result = await tool.fn(action="invalid")
        assert "error" in result


class TestManageProblemNote:
    @pytest.fixture
    def tool(self):
        return _mcp()._tool_manager._tools["manage_problem_note"]

    @pytest.mark.asyncio
    async def test_list(self, tool):
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"notes": []})
            result = await tool.fn(action="list", problem_id=1)
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_get(self, tool):
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"note": {"id": 1}})
            result = await tool.fn(action="get", problem_id=1, note_id=1)
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_create(self, tool):
        with patch(f"{MOD}.api_post", new_callable=AsyncMock) as m:
            m.return_value = _ok({"note": {"id": 1}}, 201)
            result = await tool.fn(action="create", problem_id=1, body="Note text")
            assert "note" in result or result.get("success")

    @pytest.mark.asyncio
    async def test_create_missing_body(self, tool):
        result = await tool.fn(action="create", problem_id=1)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_update(self, tool):
        with patch(f"{MOD}.api_put", new_callable=AsyncMock) as m:
            m.return_value = _ok({"note": {"id": 1}})
            result = await tool.fn(action="update", problem_id=1, note_id=1, body="Updated")
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_delete(self, tool):
        with patch(f"{MOD}.api_delete", new_callable=AsyncMock) as m:
            m.return_value = _no_content()
            result = await tool.fn(action="delete", problem_id=1, note_id=1)
            assert result.get("success") is True


class TestManageProblemTask:
    @pytest.fixture
    def tool(self):
        return _mcp()._tool_manager._tools["manage_problem_task"]

    @pytest.mark.asyncio
    async def test_list(self, tool):
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"tasks": []})
            result = await tool.fn(action="list", problem_id=1)
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_get(self, tool):
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"task": {"id": 1}})
            result = await tool.fn(action="get", problem_id=1, task_id=1)
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_create(self, tool):
        with patch(f"{MOD}.api_post", new_callable=AsyncMock) as m:
            m.return_value = _ok({"task": {"id": 1}}, 201)
            result = await tool.fn(action="create", problem_id=1, title="Fix root cause")
            assert "task" in result or result.get("success")

    @pytest.mark.asyncio
    async def test_create_missing(self, tool):
        result = await tool.fn(action="create", problem_id=1)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_update(self, tool):
        with patch(f"{MOD}.api_put", new_callable=AsyncMock) as m:
            m.return_value = _ok({"task": {"id": 1}})
            result = await tool.fn(action="update", problem_id=1, task_id=1, title="Updated")
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_delete(self, tool):
        with patch(f"{MOD}.api_delete", new_callable=AsyncMock) as m:
            m.return_value = _no_content()
            result = await tool.fn(action="delete", problem_id=1, task_id=1)
            assert result.get("success") is True


class TestManageProblemTimeEntry:
    @pytest.fixture
    def tool(self):
        return _mcp()._tool_manager._tools["manage_problem_time_entry"]

    @pytest.mark.asyncio
    async def test_list(self, tool):
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"time_entries": []})
            result = await tool.fn(action="list", problem_id=1)
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_get(self, tool):
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"time_entry": {"id": 1}})
            result = await tool.fn(action="get", problem_id=1, time_entry_id=1)
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_create(self, tool):
        with patch(f"{MOD}.api_post", new_callable=AsyncMock) as m:
            m.return_value = _ok({"time_entry": {"id": 1}}, 201)
            result = await tool.fn(
                action="create", problem_id=1,
                agent_id=1, time_spent="01:00"
            )
            assert "time_entry" in result or result.get("success")

    @pytest.mark.asyncio
    async def test_update(self, tool):
        with patch(f"{MOD}.api_put", new_callable=AsyncMock) as m:
            m.return_value = _ok({"time_entry": {"id": 1}})
            result = await tool.fn(
                action="update", problem_id=1, time_entry_id=1,
                time_spent="02:00"
            )
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_delete(self, tool):
        with patch(f"{MOD}.api_delete", new_callable=AsyncMock) as m:
            m.return_value = _no_content()
            result = await tool.fn(action="delete", problem_id=1, time_entry_id=1)
            assert result.get("success") is True
