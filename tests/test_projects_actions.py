"""Comprehensive tests for projects tool actions."""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from mcp.server.fastmcp import FastMCP


def _mcp():
    from freshservice_mcp.tools.projects import register_project_tools
    mcp = FastMCP("test")
    register_project_tools(mcp)
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


MOD = "freshservice_mcp.tools.projects"


class TestManageProject:
    @pytest.fixture
    def tool(self):
        return _mcp()._tool_manager._tools["manage_project"]

    @pytest.mark.asyncio
    async def test_list(self, tool):
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"projects": [{"id": 1}]})
            result = await tool.fn(action="list")
            assert "projects" in result or "error" not in result

    @pytest.mark.asyncio
    async def test_get(self, tool):
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"project": {"id": 1}})
            result = await tool.fn(action="get", project_id=1)
            assert "project" in result or "error" not in result

    @pytest.mark.asyncio
    async def test_get_missing_id(self, tool):
        result = await tool.fn(action="get")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_create(self, tool):
        with patch(f"{MOD}.api_post", new_callable=AsyncMock) as m:
            m.return_value = _ok({"project": {"id": 1}}, 201)
            result = await tool.fn(
                action="create", name="My Project",
                description="Desc", project_type=1,
                start_date="2026-01-01", end_date="2026-06-30",
                manager_id=1
            )
            assert "project" in result or result.get("success")

    @pytest.mark.asyncio
    async def test_create_missing_fields(self, tool):
        result = await tool.fn(action="create")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_update(self, tool):
        with patch(f"{MOD}.api_put", new_callable=AsyncMock) as m:
            m.return_value = _ok({"project": {"id": 1}})
            result = await tool.fn(action="update", project_id=1, name="Updated")
            assert "project" in result or "error" not in result

    @pytest.mark.asyncio
    async def test_update_missing_id(self, tool):
        result = await tool.fn(action="update")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_delete(self, tool):
        with patch(f"{MOD}.api_delete", new_callable=AsyncMock) as m:
            m.return_value = _no_content()
            result = await tool.fn(action="delete", project_id=1)
            assert result.get("success") is True

    @pytest.mark.asyncio
    async def test_delete_missing_id(self, tool):
        result = await tool.fn(action="delete")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_archive(self, tool):
        with patch(f"{MOD}.api_post", new_callable=AsyncMock) as m:
            m.return_value = _ok({"success": True})
            result = await tool.fn(action="archive", project_id=1)
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_archive_missing_id(self, tool):
        result = await tool.fn(action="archive")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_restore(self, tool):
        with patch(f"{MOD}.api_post", new_callable=AsyncMock) as m:
            m.return_value = _ok({"success": True})
            result = await tool.fn(action="restore", project_id=1)
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_restore_missing_id(self, tool):
        result = await tool.fn(action="restore")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_get_fields(self, tool):
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"project_fields": []})
            result = await tool.fn(action="get_fields")
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_get_templates(self, tool):
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"project_templates": []})
            result = await tool.fn(action="get_templates")
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_add_members(self, tool):
        with patch(f"{MOD}.api_post", new_callable=AsyncMock) as m:
            m.return_value = _ok({"members": []}, 201)
            result = await tool.fn(action="add_members", project_id=1, members=[{"email": "u@test.com"}])
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_add_members_missing(self, tool):
        result = await tool.fn(action="add_members", project_id=1)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_get_memberships(self, tool):
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"members": []})
            result = await tool.fn(action="get_memberships", project_id=1)
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_create_association(self, tool):
        with patch(f"{MOD}.api_post", new_callable=AsyncMock) as m:
            m.return_value = _ok({"association": {"id": 1}}, 201)
            result = await tool.fn(
                action="create_association", project_id=1,
                module_name="tickets", ids=[42]
            )
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_create_association_missing(self, tool):
        result = await tool.fn(action="create_association", project_id=1)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_get_associations(self, tool):
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"associations": []})
            result = await tool.fn(action="get_associations", project_id=1, module_name="tickets")
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_delete_association(self, tool):
        with patch(f"{MOD}.api_delete", new_callable=AsyncMock) as m:
            m.return_value = _no_content()
            result = await tool.fn(action="delete_association", project_id=1, module_name="tickets", association_id=1)
            assert result.get("success") is True

    @pytest.mark.asyncio
    async def test_delete_association_missing(self, tool):
        result = await tool.fn(action="delete_association", project_id=1)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_get_versions(self, tool):
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"versions": []})
            result = await tool.fn(action="get_versions", project_id=1)
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_get_sprints(self, tool):
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"sprints": []})
            result = await tool.fn(action="get_sprints", project_id=1)
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_unknown_action(self, tool):
        result = await tool.fn(action="invalid")
        assert "error" in result


class TestManageProjectTask:
    @pytest.fixture
    def tool(self):
        return _mcp()._tool_manager._tools["manage_project_task"]

    @pytest.mark.asyncio
    async def test_list(self, tool):
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"tasks": []})
            result = await tool.fn(action="list", project_id=1)
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_filter(self, tool):
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"tasks": []})
            result = await tool.fn(action="filter", project_id=1, query='"status:open"')
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_get(self, tool):
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"task": {"id": 1}})
            result = await tool.fn(action="get", project_id=1, task_id=1)
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_get_missing_id(self, tool):
        result = await tool.fn(action="get", project_id=1)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_create(self, tool):
        with patch(f"{MOD}.api_post", new_callable=AsyncMock) as m:
            m.return_value = _ok({"task": {"id": 1}}, 201)
            result = await tool.fn(
                action="create", project_id=1, title="Task 1",
                type_id=1, priority_id=1, status_id=1
            )
            assert "task" in result or result.get("success")

    @pytest.mark.asyncio
    async def test_create_missing(self, tool):
        result = await tool.fn(action="create", project_id=1)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_update(self, tool):
        with patch(f"{MOD}.api_put", new_callable=AsyncMock) as m:
            m.return_value = _ok({"task": {"id": 1}})
            result = await tool.fn(action="update", project_id=1, task_id=1, title="Updated")
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_update_missing_id(self, tool):
        result = await tool.fn(action="update", project_id=1)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_delete(self, tool):
        with patch(f"{MOD}.api_delete", new_callable=AsyncMock) as m:
            m.return_value = _no_content()
            result = await tool.fn(action="delete", project_id=1, task_id=1)
            assert result.get("success") is True

    @pytest.mark.asyncio
    async def test_delete_missing_id(self, tool):
        result = await tool.fn(action="delete", project_id=1)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_get_task_types(self, tool):
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"task_types": []})
            result = await tool.fn(action="get_task_types", project_id=1)
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_get_task_type_fields(self, tool):
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"fields": []})
            result = await tool.fn(action="get_task_type_fields", project_id=1, type_id=1)
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_get_task_type_fields_missing(self, tool):
        result = await tool.fn(action="get_task_type_fields", project_id=1)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_get_task_statuses(self, tool):
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"statuses": []})
            result = await tool.fn(action="get_task_statuses", project_id=1)
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_get_task_priorities(self, tool):
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"priorities": []})
            result = await tool.fn(action="get_task_priorities", project_id=1)
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_create_note(self, tool):
        with patch(f"{MOD}.api_post", new_callable=AsyncMock) as m:
            m.return_value = _ok({"note": {"id": 1}}, 201)
            result = await tool.fn(action="create_note", project_id=1, task_id=1, content="Note")
            assert "note" in result or result.get("success")

    @pytest.mark.asyncio
    async def test_create_note_missing(self, tool):
        result = await tool.fn(action="create_note", project_id=1, task_id=1)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_list_notes(self, tool):
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"notes": []})
            result = await tool.fn(action="list_notes", project_id=1, task_id=1)
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_update_note(self, tool):
        with patch(f"{MOD}.api_put", new_callable=AsyncMock) as m:
            m.return_value = _ok({"note": {"id": 1}})
            result = await tool.fn(action="update_note", project_id=1, task_id=1, note_id=1, content="Updated")
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_update_note_missing(self, tool):
        result = await tool.fn(action="update_note", project_id=1, task_id=1)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_delete_note(self, tool):
        with patch(f"{MOD}.api_delete", new_callable=AsyncMock) as m:
            m.return_value = _no_content()
            result = await tool.fn(action="delete_note", project_id=1, task_id=1, note_id=1)
            assert result.get("success") is True

    @pytest.mark.asyncio
    async def test_delete_note_missing(self, tool):
        result = await tool.fn(action="delete_note", project_id=1, task_id=1)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_create_association(self, tool):
        with patch(f"{MOD}.api_post", new_callable=AsyncMock) as m:
            m.return_value = _ok({"association": {"id": 1}}, 201)
            result = await tool.fn(
                action="create_association", project_id=1, task_id=1,
                module_name="tickets", ids=[42]
            )
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_create_association_missing(self, tool):
        result = await tool.fn(action="create_association", project_id=1, task_id=1)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_get_associations(self, tool):
        with patch(f"{MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"associations": []})
            result = await tool.fn(action="get_associations", project_id=1, task_id=1, module_name="tickets")
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_delete_association(self, tool):
        with patch(f"{MOD}.api_delete", new_callable=AsyncMock) as m:
            m.return_value = _no_content()
            result = await tool.fn(action="delete_association", project_id=1, task_id=1, module_name="tickets", association_id=1)
            assert result.get("success") is True

    @pytest.mark.asyncio
    async def test_delete_association_missing(self, tool):
        result = await tool.fn(action="delete_association", project_id=1, task_id=1)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_unknown_action(self, tool):
        result = await tool.fn(action="invalid", project_id=1)
        assert "error" in result
