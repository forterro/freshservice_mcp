"""Comprehensive functional tests covering all remaining uncovered branches.

Tests verify:
- Correct API endpoints called with correct parameters
- Correct payload construction from optional fields
- Validation error messages for missing required fields
- Correct response structure on success/failure
- Multi-step flows (create + deferred planning update)
- Edge cases (cache TTL, disk promotion, non-HTTP ASGI scope)
"""
import base64
import json
import time
import pytest
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock, AsyncMock as AM

from mcp.server.fastmcp import FastMCP


# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════
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


def _error_response(status_code=500, body="Server Error"):
    """Simulate an httpx.HTTPStatusError."""
    import httpx
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = {"error": body}
    resp.text = body
    request = MagicMock()
    return httpx.HTTPStatusError(body, request=request, response=resp)


def _mcp_with_tool(register_func):
    mcp = FastMCP("test")
    register_func(mcp)
    return mcp


# ═══════════════════════════════════════════════════════════════════════════
# 1. cache.py — _build_redis_url logic
# ═══════════════════════════════════════════════════════════════════════════
class TestBuildRedisUrl:
    """Test cache._build_redis_url constructs URL with injected password."""

    def test_no_url_returns_empty(self):
        with patch.dict("os.environ", {"REDIS_URL": "", "REDIS_PASSWORD": "secret"}, clear=False):
            # Re-import to trigger module-level code
            import importlib
            import freshservice_mcp.cache as cache_mod
            # Call function directly
            from freshservice_mcp.cache import _build_redis_url
            # patch the module-level vars
            with patch.object(cache_mod, "_REDIS_URL_RAW", ""):
                with patch.object(cache_mod, "_REDIS_PASSWORD", "secret"):
                    result = cache_mod._build_redis_url()
                    assert result == ""

    def test_no_password_returns_url_unchanged(self):
        import freshservice_mcp.cache as cache_mod
        with patch.object(cache_mod, "_REDIS_URL_RAW", "redis://localhost:6379/0"):
            with patch.object(cache_mod, "_REDIS_PASSWORD", ""):
                result = cache_mod._build_redis_url()
                assert result == "redis://localhost:6379/0"

    def test_injects_password_into_url_without_port(self):
        import freshservice_mcp.cache as cache_mod
        with patch.object(cache_mod, "_REDIS_URL_RAW", "redis://myhost/0"):
            with patch.object(cache_mod, "_REDIS_PASSWORD", "s3cr3t"):
                result = cache_mod._build_redis_url()
                assert "s3cr3t" in result
                assert "myhost" in result
                assert result.startswith("redis://")

    def test_injects_password_into_url_with_port(self):
        import freshservice_mcp.cache as cache_mod
        with patch.object(cache_mod, "_REDIS_URL_RAW", "redis://myhost:6380/2"):
            with patch.object(cache_mod, "_REDIS_PASSWORD", "p@ss"):
                result = cache_mod._build_redis_url()
                # Should include password and port
                assert "myhost" in result
                assert ":6380" in result
                assert "p%40ss" in result  # URL-encoded @

    def test_url_already_has_password_unchanged(self):
        import freshservice_mcp.cache as cache_mod
        with patch.object(cache_mod, "_REDIS_URL_RAW", "redis://:existing@myhost:6379/0"):
            with patch.object(cache_mod, "_REDIS_PASSWORD", "new_pass"):
                result = cache_mod._build_redis_url()
                # Should NOT replace existing password
                assert "existing" in result
                assert "new_pass" not in result


# ═══════════════════════════════════════════════════════════════════════════
# 2. telemetry.py — get_tracer and trace_span with active tracer
# ═══════════════════════════════════════════════════════════════════════════
class TestTelemetryTracing:
    """Test tracer usage when OTel is enabled."""

    def test_get_tracer_returns_none_by_default(self):
        from freshservice_mcp.telemetry import get_tracer
        # Default state — no tracer configured
        result = get_tracer()
        assert result is None

    @pytest.mark.asyncio
    async def test_trace_span_yields_none_when_no_tracer(self):
        from freshservice_mcp.telemetry import trace_span
        async with trace_span("test_op") as span:
            assert span is None

    @pytest.mark.asyncio
    async def test_trace_span_creates_span_when_tracer_active(self):
        import freshservice_mcp.telemetry as tel_mod
        mock_span = MagicMock()
        mock_tracer = MagicMock()
        mock_tracer.start_as_current_span.return_value.__enter__ = MagicMock(return_value=mock_span)
        mock_tracer.start_as_current_span.return_value.__exit__ = MagicMock(return_value=False)

        original = tel_mod._tracer
        tel_mod._tracer = mock_tracer
        try:
            from freshservice_mcp.telemetry import trace_span
            async with trace_span("test_operation", {"key": "val"}) as span:
                assert span is mock_span
            mock_tracer.start_as_current_span.assert_called_once_with(
                "test_operation", attributes={"key": "val"}
            )
        finally:
            tel_mod._tracer = original

    def test_get_tracer_returns_tracer_when_set(self):
        import freshservice_mcp.telemetry as tel_mod
        from freshservice_mcp.telemetry import get_tracer
        mock_tracer = MagicMock()
        original = tel_mod._tracer
        tel_mod._tracer = mock_tracer
        try:
            assert get_tracer() is mock_tracer
        finally:
            tel_mod._tracer = original


# ═══════════════════════════════════════════════════════════════════════════
# 3. auth.py — non-HTTP ASGI scope (line 70)
# ═══════════════════════════════════════════════════════════════════════════
class TestAuthMiddlewareNonHttp:
    """Test middleware passes through non-HTTP scopes (websocket, lifespan)."""

    @pytest.mark.asyncio
    async def test_websocket_scope_passes_through(self):
        from freshservice_mcp.auth import ForwardedAuthMiddleware

        inner_app = AsyncMock()
        middleware = ForwardedAuthMiddleware(inner_app)

        scope = {"type": "websocket", "path": "/ws"}
        receive = AsyncMock()
        send = AsyncMock()

        await middleware(scope, receive, send)
        inner_app.assert_called_once_with(scope, receive, send)

    @pytest.mark.asyncio
    async def test_lifespan_scope_passes_through(self):
        from freshservice_mcp.auth import ForwardedAuthMiddleware

        inner_app = AsyncMock()
        middleware = ForwardedAuthMiddleware(inner_app)

        scope = {"type": "lifespan"}
        receive = AsyncMock()
        send = AsyncMock()

        await middleware(scope, receive, send)
        inner_app.assert_called_once_with(scope, receive, send)


# ═══════════════════════════════════════════════════════════════════════════
# 4. http_client.py — Basic auth fallback (line 27)
# ═══════════════════════════════════════════════════════════════════════════
class TestHttpClientAuthFallback:
    """Test _auth_header falls back to Basic auth when no forwarded creds."""

    def test_fallback_to_basic_auth_when_no_forwarded(self):
        from freshservice_mcp.http_client import _auth_header
        from freshservice_mcp.auth import forwarded_auth_var

        # Clear any forwarded token
        token = forwarded_auth_var.set(None)
        try:
            result = _auth_header()
            assert result.startswith("Basic ")
            # Decode and verify format is "apikey:X"
            decoded = base64.b64decode(result.split(" ")[1]).decode()
            assert decoded.endswith(":X")
        finally:
            forwarded_auth_var.reset(token)

    def test_uses_forwarded_bearer_when_available(self):
        from freshservice_mcp.http_client import _auth_header
        from freshservice_mcp.auth import forwarded_auth_var

        token = forwarded_auth_var.set("Bearer eyJhbGciOiJSUzI1NiJ9.test.sig")
        try:
            result = _auth_header()
            assert result == "Bearer eyJhbGciOiJSUzI1NiJ9.test.sig"
        finally:
            forwarded_auth_var.reset(token)


# ═══════════════════════════════════════════════════════════════════════════
# 5. discovery.py — disk cache, TTL expiry, tool registration
# ═══════════════════════════════════════════════════════════════════════════
class TestDiscoveryDiskCache:
    """Test cache disk I/O and TTL validation."""

    def test_read_cache_disk_promotion(self, tmp_path):
        """Valid disk cache gets promoted to memory."""
        from freshservice_mcp.discovery import _read_cache, _write_cache, _mem_cache
        import freshservice_mcp.discovery as disc_mod

        original_dir = disc_mod._CACHE_DIR
        disc_mod._CACHE_DIR = tmp_path
        _mem_cache.clear()
        try:
            # Write to disk directly (bypassing memory)
            entry = {"ts": time.time(), "data": {"fields": ["x"]}}
            cache_file = tmp_path / "disk_test.json"
            cache_file.write_text(json.dumps(entry))

            # Read should find on disk and promote to memory
            result = _read_cache("disk_test")
            assert result == {"fields": ["x"]}
            assert "disk_test" in _mem_cache
        finally:
            disc_mod._CACHE_DIR = original_dir
            _mem_cache.clear()

    def test_read_cache_expired_disk(self, tmp_path):
        """Expired disk cache returns None."""
        from freshservice_mcp.discovery import _read_cache, _mem_cache
        import freshservice_mcp.discovery as disc_mod

        original_dir = disc_mod._CACHE_DIR
        disc_mod._CACHE_DIR = tmp_path
        _mem_cache.clear()
        try:
            # Write expired entry to disk
            entry = {"ts": time.time() - 99999, "data": {"old": True}}
            cache_file = tmp_path / "expired.json"
            cache_file.write_text(json.dumps(entry))

            result = _read_cache("expired")
            assert result is None
        finally:
            disc_mod._CACHE_DIR = original_dir
            _mem_cache.clear()

    def test_read_cache_corrupted_disk(self, tmp_path):
        """Corrupted disk cache returns None gracefully."""
        from freshservice_mcp.discovery import _read_cache, _mem_cache
        import freshservice_mcp.discovery as disc_mod

        original_dir = disc_mod._CACHE_DIR
        disc_mod._CACHE_DIR = tmp_path
        _mem_cache.clear()
        try:
            cache_file = tmp_path / "corrupt.json"
            cache_file.write_text("not valid json{{{")

            result = _read_cache("corrupt")
            assert result is None
        finally:
            disc_mod._CACHE_DIR = original_dir
            _mem_cache.clear()

    def test_read_cache_memory_expired(self):
        """Memory cache entry expired is evicted."""
        from freshservice_mcp.discovery import _read_cache, _mem_cache

        _mem_cache.clear()
        _mem_cache["stale"] = {"ts": time.time() - 99999, "data": {"old": True}}

        result = _read_cache("stale")
        assert result is None
        assert "stale" not in _mem_cache

    def test_write_cache_disk_failure_non_fatal(self, tmp_path):
        """Write to disk failing doesn't crash — memory still works."""
        from freshservice_mcp.discovery import _write_cache, _read_cache, _mem_cache
        import freshservice_mcp.discovery as disc_mod

        _mem_cache.clear()
        original_dir = disc_mod._CACHE_DIR
        # Point to a non-writable path
        disc_mod._CACHE_DIR = Path("/proc/impossible_write_dir")
        try:
            _write_cache("fail_disk", {"test": True})
            # Memory cache should still work
            assert _read_cache("fail_disk") == {"test": True}
        finally:
            disc_mod._CACHE_DIR = original_dir
            _mem_cache.clear()


class TestDiscoveryToolRegistration:
    """Test discover_form_fields and clear_field_cache registered tools."""

    @pytest.fixture
    def tools(self):
        from freshservice_mcp.discovery import register_discovery_tools, _mem_cache
        _mem_cache.clear()
        mcp = FastMCP("test")
        register_discovery_tools(mcp)
        return mcp._tool_manager._tools

    @pytest.mark.asyncio
    async def test_discover_form_fields_from_cache(self, tools):
        from freshservice_mcp.discovery import _write_cache, _mem_cache
        _mem_cache.clear()
        _write_cache("fields_ticket", [{"name": "subject", "type": "text"}])
        result = await tools["discover_form_fields"].fn(entity_type="ticket")
        assert result["source"] == "cache"
        assert result["fields"] == [{"name": "subject", "type": "text"}]

    @pytest.mark.asyncio
    async def test_discover_form_fields_force_refresh(self, tools):
        """force_refresh invalidates cache before fetching."""
        from freshservice_mcp.discovery import _write_cache, _mem_cache
        _mem_cache.clear()
        _write_cache("fields_change", [{"name": "old"}])

        with patch("freshservice_mcp.discovery.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"change_fields": [{"name": "new"}]})
            result = await tools["discover_form_fields"].fn(
                entity_type="change", force_refresh=True
            )
            assert result["source"] == "api"
            m.assert_called_once_with("change_form_fields")

    @pytest.mark.asyncio
    async def test_discover_form_fields_asset_type(self, tools):
        """asset_type goes through _fetch_asset_types path."""
        from freshservice_mcp.discovery import _mem_cache, invalidate_cache
        _mem_cache.clear()
        invalidate_cache("asset_types")
        with patch("freshservice_mcp.discovery.api_get", new_callable=AsyncMock) as m:
            page1 = _ok({"asset_types": [{"id": 1, "name": "Laptop"}]})
            page2 = _ok({"asset_types": []})
            m.side_effect = [page1, page2]
            result = await tools["discover_form_fields"].fn(entity_type="asset_type")
            assert result["source"] == "api"
            assert result["asset_types"] == [{"id": 1, "name": "Laptop"}]

    @pytest.mark.asyncio
    async def test_clear_field_cache_specific(self, tools):
        from freshservice_mcp.discovery import _write_cache, _mem_cache
        _mem_cache.clear()
        _write_cache("fields_agent", [{"name": "email"}])
        result = await tools["clear_field_cache"].fn(entity_type="agent")
        assert result["success"] is True
        assert "agent" in result["message"]

    @pytest.mark.asyncio
    async def test_clear_field_cache_all(self, tools):
        from freshservice_mcp.discovery import _write_cache, _mem_cache
        _mem_cache.clear()
        _write_cache("fields_ticket", [])
        _write_cache("fields_change", [])
        result = await tools["clear_field_cache"].fn()
        assert result["success"] is True
        assert "All" in result["message"]

    @pytest.mark.asyncio
    async def test_fetch_fields_api_error(self, tools):
        from freshservice_mcp.discovery import _mem_cache
        _mem_cache.clear()
        with patch("freshservice_mcp.discovery.api_get", new_callable=AsyncMock) as m:
            m.side_effect = Exception("Connection refused")
            result = await tools["discover_form_fields"].fn(entity_type="ticket")
            assert "error" in result

    @pytest.mark.asyncio
    async def test_fetch_asset_types_api_error(self, tools):
        from freshservice_mcp.discovery import _mem_cache
        _mem_cache.clear()
        with patch("freshservice_mcp.discovery.api_get", new_callable=AsyncMock) as m:
            m.side_effect = Exception("Timeout")
            result = await tools["discover_form_fields"].fn(entity_type="asset_type")
            assert "error" in result


# ═══════════════════════════════════════════════════════════════════════════
# 6. tools/misc.py — all actions (canned_responses)
# ═══════════════════════════════════════════════════════════════════════════
class TestMiscCannedResponses:
    """Test canned_responses tool: list, get, list_folders, get_folder."""

    @pytest.fixture
    def tool(self):
        from freshservice_mcp.tools.misc import register_misc_tools
        mcp = FastMCP("test")
        register_misc_tools(mcp)
        return mcp._tool_manager._tools["manage_canned_response"]

    MOD = "freshservice_mcp.tools.misc"

    @pytest.mark.asyncio
    async def test_list(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"canned_responses": [{"id": 1, "title": "Welcome"}]})
            result = await tool.fn(action="list")
            assert "canned_responses" in result
            m.assert_called_once_with("canned_responses")

    @pytest.mark.asyncio
    async def test_get(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"canned_response": {"id": 5, "title": "Thanks"}})
            result = await tool.fn(action="get", response_id=5)
            assert "canned_response" in result
            m.assert_called_once_with("canned_responses/5")

    @pytest.mark.asyncio
    async def test_get_missing_id(self, tool):
        result = await tool.fn(action="get")
        assert result == {"error": "response_id required for get"}

    @pytest.mark.asyncio
    async def test_list_folders(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"folders": [{"id": 1}]})
            result = await tool.fn(action="list_folders")
            assert "folders" in result
            m.assert_called_once_with("canned_response_folders")

    @pytest.mark.asyncio
    async def test_get_folder(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"folder": {"id": 3}})
            result = await tool.fn(action="get_folder", folder_id=3)
            assert "folder" in result
            m.assert_called_once_with("canned_response_folders/3")

    @pytest.mark.asyncio
    async def test_get_folder_missing_id(self, tool):
        result = await tool.fn(action="get_folder")
        assert result == {"error": "folder_id required for get_folder"}

    @pytest.mark.asyncio
    async def test_unknown_action(self, tool):
        result = await tool.fn(action="invalid_action")
        assert "Unknown action" in result["error"]

    @pytest.mark.asyncio
    async def test_list_error(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.side_effect = Exception("Network error")
            result = await tool.fn(action="list")
            assert "error" in result

    @pytest.mark.asyncio
    async def test_list_folders_error(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.side_effect = Exception("Timeout")
            result = await tool.fn(action="list_folders")
            assert "error" in result

    @pytest.mark.asyncio
    async def test_get_folder_error(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.side_effect = Exception("Fail")
            result = await tool.fn(action="get_folder", folder_id=1)
            assert "error" in result

    @pytest.mark.asyncio
    async def test_get_error(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.side_effect = Exception("Bad gateway")
            result = await tool.fn(action="get", response_id=1)
            assert "error" in result


# ═══════════════════════════════════════════════════════════════════════════
# 7. tools/products.py — all actions
# ═══════════════════════════════════════════════════════════════════════════
class TestProductsActions:
    """Test manage_product: create with all fields, update validation, errors."""

    @pytest.fixture
    def tool(self):
        from freshservice_mcp.tools.products import register_products_tools
        mcp = FastMCP("test")
        register_products_tools(mcp)
        return mcp._tool_manager._tools["manage_product"]

    MOD = "freshservice_mcp.tools.products"

    @pytest.mark.asyncio
    async def test_get_missing_id(self, tool):
        result = await tool.fn(action="get")
        assert result == {"error": "product_id required for get"}

    @pytest.mark.asyncio
    async def test_get_success(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"product": {"id": 1, "name": "Laptop Pro"}})
            result = await tool.fn(action="get", product_id=1)
            assert result["product"]["name"] == "Laptop Pro"
            m.assert_called_once_with("products/1")

    @pytest.mark.asyncio
    async def test_create_missing_fields(self, tool):
        result = await tool.fn(action="create", name="Test")
        assert "name and asset_type_id required" in result["error"]

    @pytest.mark.asyncio
    async def test_create_with_all_optional_fields(self, tool):
        """Verify all optional fields are included in the payload."""
        with patch(f"{self.MOD}.api_post", new_callable=AsyncMock) as m:
            m.return_value = _ok({"product": {"id": 1}}, 201)
            result = await tool.fn(
                action="create", name="Dell XPS", asset_type_id=5,
                manufacturer="Dell", status="In Production",
                mode_of_procurement="Buy", depreciation_type_id=2,
                description="<p>High-end laptop</p>",
                description_text="High-end laptop"
            )
            assert result["success"] is True
            payload = m.call_args.kwargs["json"]
            assert payload["name"] == "Dell XPS"
            assert payload["asset_type_id"] == 5
            assert payload["manufacturer"] == "Dell"
            assert payload["mode_of_procurement"] == "Buy"
            assert payload["depreciation_type_id"] == 2

    @pytest.mark.asyncio
    async def test_update_missing_id(self, tool):
        result = await tool.fn(action="update")
        assert result == {"error": "product_id required for update"}

    @pytest.mark.asyncio
    async def test_update_no_fields(self, tool):
        result = await tool.fn(action="update", product_id=1)
        assert result == {"error": "No fields provided for update"}

    @pytest.mark.asyncio
    async def test_update_success(self, tool):
        with patch(f"{self.MOD}.api_put", new_callable=AsyncMock) as m:
            m.return_value = _ok({"product": {"id": 1, "name": "Updated"}})
            result = await tool.fn(action="update", product_id=1, name="Updated")
            assert result["success"] is True
            m.assert_called_once_with("products/1", json={"name": "Updated"})

    @pytest.mark.asyncio
    async def test_unknown_action(self, tool):
        result = await tool.fn(action="invalid")
        assert "Unknown action" in result["error"]

    @pytest.mark.asyncio
    async def test_create_api_error(self, tool):
        with patch(f"{self.MOD}.api_post", new_callable=AsyncMock) as m:
            m.side_effect = Exception("Forbidden")
            result = await tool.fn(action="create", name="X", asset_type_id=1)
            assert "error" in result

    @pytest.mark.asyncio
    async def test_get_api_error(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.side_effect = Exception("Not found")
            result = await tool.fn(action="get", product_id=999)
            assert "error" in result


# ═══════════════════════════════════════════════════════════════════════════
# 8. tools/departments.py — create, update, delete, filter, locations
# ═══════════════════════════════════════════════════════════════════════════
class TestDepartmentsFull:
    """Test all department actions including payload construction."""

    @pytest.fixture
    def dept_tool(self):
        from freshservice_mcp.tools.departments import register_department_tools
        mcp = FastMCP("test")
        register_department_tools(mcp)
        return mcp._tool_manager._tools["manage_department"]

    @pytest.fixture
    def loc_tool(self):
        from freshservice_mcp.tools.departments import register_department_tools
        mcp = FastMCP("test")
        register_department_tools(mcp)
        return mcp._tool_manager._tools["manage_location"]

    MOD = "freshservice_mcp.tools.departments"

    @pytest.mark.asyncio
    async def test_create_with_all_fields(self, dept_tool):
        """Verify all optional fields are sent in the create payload."""
        with patch(f"{self.MOD}.api_post", new_callable=AsyncMock) as m:
            m.return_value = _ok({"department": {"id": 1}}, 201)
            result = await dept_tool.fn(
                action="create", name="Engineering",
                description="Core eng team",
                head_user_id=100, prime_user_id=200,
                domains=["eng.company.com"],
                custom_fields={"cost_center": "CC001"}
            )
            assert result["success"] is True
            payload = m.call_args.kwargs["json"]
            assert payload["name"] == "Engineering"
            assert payload["description"] == "Core eng team"
            assert payload["head_user_id"] == 100
            assert payload["prime_user_id"] == 200
            assert payload["domains"] == ["eng.company.com"]
            assert payload["custom_fields"] == {"cost_center": "CC001"}

    @pytest.mark.asyncio
    async def test_create_missing_name(self, dept_tool):
        result = await dept_tool.fn(action="create")
        assert result == {"error": "name required for create"}

    @pytest.mark.asyncio
    async def test_update_with_fields(self, dept_tool):
        with patch(f"{self.MOD}.api_put", new_callable=AsyncMock) as m:
            m.return_value = _ok({"department": {"id": 1}})
            result = await dept_tool.fn(
                action="update", department_id=1,
                name="Eng Updated", description="New desc"
            )
            assert result["success"] is True
            payload = m.call_args.kwargs["json"]
            assert payload["name"] == "Eng Updated"
            assert payload["description"] == "New desc"

    @pytest.mark.asyncio
    async def test_update_missing_id(self, dept_tool):
        result = await dept_tool.fn(action="update")
        assert "department_id required" in result["error"]

    @pytest.mark.asyncio
    async def test_delete_success(self, dept_tool):
        with patch(f"{self.MOD}.api_delete", new_callable=AsyncMock) as m:
            m.return_value = _no_content()
            result = await dept_tool.fn(action="delete", department_id=5)
            assert result["success"] is True
            assert "5" in result["message"]

    @pytest.mark.asyncio
    async def test_delete_missing_id(self, dept_tool):
        result = await dept_tool.fn(action="delete")
        assert "department_id required" in result["error"]

    @pytest.mark.asyncio
    async def test_filter_success(self, dept_tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"departments": [{"id": 1}]})
            result = await dept_tool.fn(action="filter", query="name:'IT'")
            assert "departments" in result
            # Verify the query is wrapped in quotes
            call_params = m.call_args.kwargs["params"]
            assert '"name:\'IT\'"' == call_params["query"]

    @pytest.mark.asyncio
    async def test_filter_missing_query(self, dept_tool):
        result = await dept_tool.fn(action="filter")
        assert "query required" in result["error"]

    @pytest.mark.asyncio
    async def test_get_fields(self, dept_tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"department_fields": [{"name": "name"}]})
            result = await dept_tool.fn(action="get_fields")
            assert "department_fields" in result
            m.assert_called_once_with("department_fields")

    # ── Location tool ──
    @pytest.mark.asyncio
    async def test_location_create_with_address(self, loc_tool):
        """Verify address fields are nested correctly in payload."""
        with patch(f"{self.MOD}.api_post", new_callable=AsyncMock) as m:
            m.return_value = _ok({"location": {"id": 1}}, 201)
            result = await loc_tool.fn(
                action="create", name="Paris Office",
                line1="10 Rue de Rivoli", city="Paris",
                country="France", zipcode="75001",
                contact_name="Jean", email="jean@co.com"
            )
            assert result["success"] is True
            payload = m.call_args.kwargs["json"]
            assert payload["name"] == "Paris Office"
            assert payload["address"]["line1"] == "10 Rue de Rivoli"
            assert payload["address"]["city"] == "Paris"
            assert payload["contact_name"] == "Jean"

    @pytest.mark.asyncio
    async def test_location_create_missing_name(self, loc_tool):
        result = await loc_tool.fn(action="create")
        assert result == {"error": "name required for create"}

    @pytest.mark.asyncio
    async def test_location_get_missing_id(self, loc_tool):
        result = await loc_tool.fn(action="get")
        assert "location_id required" in result["error"]

    @pytest.mark.asyncio
    async def test_location_update(self, loc_tool):
        with patch(f"{self.MOD}.api_put", new_callable=AsyncMock) as m:
            m.return_value = _ok({"location": {"id": 1}})
            result = await loc_tool.fn(
                action="update", location_id=1, name="Updated Office",
                city="Lyon"
            )
            assert result["success"] is True
            payload = m.call_args.kwargs["json"]
            assert payload["name"] == "Updated Office"
            assert payload["address"]["city"] == "Lyon"

    @pytest.mark.asyncio
    async def test_location_update_missing_id(self, loc_tool):
        result = await loc_tool.fn(action="update")
        assert "location_id required" in result["error"]

    @pytest.mark.asyncio
    async def test_location_delete(self, loc_tool):
        with patch(f"{self.MOD}.api_delete", new_callable=AsyncMock) as m:
            m.return_value = _no_content()
            result = await loc_tool.fn(action="delete", location_id=3)
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_location_delete_missing_id(self, loc_tool):
        result = await loc_tool.fn(action="delete")
        assert "location_id required" in result["error"]

    @pytest.mark.asyncio
    async def test_location_filter(self, loc_tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"locations": []})
            result = await loc_tool.fn(action="filter", query="name:'NY'")
            assert "locations" in result

    @pytest.mark.asyncio
    async def test_location_filter_missing_query(self, loc_tool):
        result = await loc_tool.fn(action="filter")
        assert "query required" in result["error"]

    @pytest.mark.asyncio
    async def test_location_unknown_action(self, loc_tool):
        result = await loc_tool.fn(action="xyz")
        assert "Unknown action" in result["error"]


# ═══════════════════════════════════════════════════════════════════════════
# 9. tools/changes.py — create with planning, close, move, enum validation
# ═══════════════════════════════════════════════════════════════════════════
class TestChangesFull:
    """Test change create with deferred planning_fields, close, move."""

    @pytest.fixture
    def tool(self):
        from freshservice_mcp.tools.changes import register_changes_tools
        mcp = FastMCP("test")
        register_changes_tools(mcp)
        return mcp._tool_manager._tools["manage_change"]

    MOD = "freshservice_mcp.tools.changes"

    @pytest.mark.asyncio
    async def test_create_with_planning_fields(self, tool):
        """Create change then apply planning_fields in follow-up PUT."""
        with patch(f"{self.MOD}.api_post", new_callable=AsyncMock) as mp, \
             patch(f"{self.MOD}.api_put", new_callable=AsyncMock) as mu:
            mp.return_value = _ok({"change": {"id": 42}}, 201)
            mu.return_value = _ok({"change": {"id": 42, "planning_fields": {}}})
            result = await tool.fn(
                action="create",
                requester_id=1, subject="Deploy v2",
                description="Rolling deploy",
                reason_for_change="Performance improvement",
                rollout_plan="Phase 1: staging, Phase 2: prod"
            )
            assert result["success"] is True
            # Verify planning_fields PUT was called
            mu.assert_called_once()
            put_payload = mu.call_args.kwargs["json"]
            assert "planning_fields" in put_payload
            assert "reason_for_change" in put_payload["planning_fields"]
            assert put_payload["planning_fields"]["reason_for_change"]["description"] == "Performance improvement"

    @pytest.mark.asyncio
    async def test_create_planning_put_failure_returns_warning(self, tool):
        """If planning PUT fails, return success with warning."""
        with patch(f"{self.MOD}.api_post", new_callable=AsyncMock) as mp, \
             patch(f"{self.MOD}.api_put", new_callable=AsyncMock) as mu:
            mp.return_value = _ok({"change": {"id": 42}}, 201)
            mu.side_effect = Exception("Timeout")
            result = await tool.fn(
                action="create",
                requester_id=1, subject="Deploy v3",
                description="Deploy",
                backout_plan="Rollback to v2"
            )
            assert result["success"] is True
            assert "warning" in result
            assert "planning fields could not be set" in result["warning"]

    @pytest.mark.asyncio
    async def test_create_with_maintenance_window(self, tool):
        """Create change then associate maintenance window."""
        with patch(f"{self.MOD}.api_post", new_callable=AsyncMock) as mp, \
             patch(f"{self.MOD}.api_put", new_callable=AsyncMock) as mu:
            mp.return_value = _ok({"change": {"id": 42}}, 201)
            mu.return_value = _ok({"change": {"id": 42}})
            result = await tool.fn(
                action="create",
                requester_id=1, subject="MW Change",
                description="With MW", maintenance_window_id=99
            )
            assert result["success"] is True
            # Verify MW PUT
            put_payload = mu.call_args.kwargs["json"]
            assert put_payload == {"maintenance_window": {"id": 99}}

    @pytest.mark.asyncio
    async def test_create_mw_association_failure_http_error(self, tool):
        """MW association failure returns success with warning."""
        import httpx
        with patch(f"{self.MOD}.api_post", new_callable=AsyncMock) as mp, \
             patch(f"{self.MOD}.api_put", new_callable=AsyncMock) as mu:
            mp.return_value = _ok({"change": {"id": 42}}, 201)
            # MW PUT raises HTTPStatusError
            err_resp = MagicMock()
            err_resp.status_code = 400
            err_resp.json.return_value = {"description": "Invalid MW"}
            err_resp.text = "Invalid MW"
            mu.side_effect = httpx.HTTPStatusError(
                "Bad Request", request=MagicMock(), response=err_resp
            )
            result = await tool.fn(
                action="create",
                requester_id=1, subject="MW Fail",
                description="MW fail test",
                maintenance_window_id=999
            )
            assert result["success"] is True
            assert "warning" in result
            assert "MW association failed" in result["warning"]

    @pytest.mark.asyncio
    async def test_create_invalid_enum_value(self, tool):
        """Invalid priority/status values return error."""
        result = await tool.fn(
            action="create",
            requester_id=1, subject="Test",
            description="Test", priority="invalid"
        )
        assert "Invalid value" in result["error"]

    @pytest.mark.asyncio
    async def test_create_missing_fields(self, tool):
        result = await tool.fn(action="create")
        assert "requester_id, subject, and description" in result["error"]

    @pytest.mark.asyncio
    async def test_update_with_planning_fields(self, tool):
        """Update with planning_fields includes them in payload."""
        with patch(f"{self.MOD}.api_put", new_callable=AsyncMock) as m:
            m.return_value = _ok({"change": {"id": 10}})
            result = await tool.fn(
                action="update", change_id=10,
                reason_for_change="New reason",
                change_impact="Minimal"
            )
            assert result["success"] is True
            payload = m.call_args.kwargs["json"]
            assert "planning_fields" in payload
            assert payload["planning_fields"]["reason_for_change"]["description"] == "New reason"

    @pytest.mark.asyncio
    async def test_update_no_fields(self, tool):
        result = await tool.fn(action="update", change_id=10)
        assert result == {"error": "No fields provided for update"}

    @pytest.mark.asyncio
    async def test_update_invalid_enum(self, tool):
        result = await tool.fn(action="update", change_id=10, priority="abc")
        assert "Invalid" in result["error"]

    @pytest.mark.asyncio
    async def test_close(self, tool):
        with patch(f"{self.MOD}.api_put", new_callable=AsyncMock) as m:
            m.return_value = _ok({"change": {"id": 10, "status": 4}})
            result = await tool.fn(action="close", change_id=10)
            assert result["success"] is True
            # Verify status is set to CLOSED value
            payload = m.call_args.kwargs["json"]
            assert "status" in payload

    @pytest.mark.asyncio
    async def test_close_with_explanation(self, tool):
        with patch(f"{self.MOD}.api_put", new_callable=AsyncMock) as m:
            m.return_value = _ok({"change": {"id": 10}})
            result = await tool.fn(
                action="close", change_id=10,
                change_result_explanation="Successful deployment"
            )
            assert result["success"] is True
            payload = m.call_args.kwargs["json"]
            assert payload["custom_fields"]["change_result_explanation"] == "Successful deployment"

    @pytest.mark.asyncio
    async def test_close_missing_id(self, tool):
        result = await tool.fn(action="close")
        assert "change_id required" in result["error"]

    @pytest.mark.asyncio
    async def test_delete(self, tool):
        with patch(f"{self.MOD}.api_delete", new_callable=AsyncMock) as m:
            m.return_value = _no_content()
            result = await tool.fn(action="delete", change_id=10)
            assert result["success"] is True
            assert result["message"] == "Change deleted"

    @pytest.mark.asyncio
    async def test_delete_unexpected_status(self, tool):
        with patch(f"{self.MOD}.api_delete", new_callable=AsyncMock) as m:
            m.return_value = _ok({"error": "conflict"}, 409)
            result = await tool.fn(action="delete", change_id=10)
            assert "Unexpected status" in result["error"]

    @pytest.mark.asyncio
    async def test_move(self, tool):
        with patch(f"{self.MOD}.api_put", new_callable=AsyncMock) as m:
            m.return_value = _ok({"change": {"id": 10}})
            result = await tool.fn(action="move", change_id=10, workspace_id=2)
            assert "error" not in result
            m.assert_called_once_with(
                "changes/10/move_workspace", json={"workspace_id": 2}
            )

    @pytest.mark.asyncio
    async def test_move_missing_fields(self, tool):
        result = await tool.fn(action="move", change_id=10)
        assert "workspace_id required" in result["error"]

    @pytest.mark.asyncio
    async def test_get_fields(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"change_fields": []})
            result = await tool.fn(action="get_fields")
            assert "change_fields" in result
            m.assert_called_once_with("change_form_fields")

    @pytest.mark.asyncio
    async def test_list_with_all_params(self, tool):
        """Verify list passes sort, order_by, view, workspace_id, updated_since."""
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            resp = _ok({"changes": []})
            resp.headers = {"Link": ""}
            m.return_value = resp
            result = await tool.fn(
                action="list", sort="asc", order_by="created_at",
                view="open", workspace_id=3, updated_since="2025-01-01"
            )
            params = m.call_args.kwargs["params"]
            assert params["sort"] == "asc"
            assert params["order_by"] == "created_at"
            assert params["view"] == "open"
            assert params["workspace_id"] == 3
            assert params["updated_since"] == "2025-01-01"


# ═══════════════════════════════════════════════════════════════════════════
# 10. tools/releases.py — deferred planning, restore, filter, get_fields
# ═══════════════════════════════════════════════════════════════════════════
class TestReleasesFull:
    """Test release create with deferred planning, restore, filter."""

    @pytest.fixture
    def tool(self):
        from freshservice_mcp.tools.releases import register_release_tools
        mcp = FastMCP("test")
        register_release_tools(mcp)
        return mcp._tool_manager._tools["manage_release"]

    MOD = "freshservice_mcp.tools.releases"

    @pytest.mark.asyncio
    async def test_create_with_planning_fields(self, tool):
        """Create release then apply planning_fields via PUT."""
        with patch(f"{self.MOD}.api_post", new_callable=AsyncMock) as mp, \
             patch(f"{self.MOD}.api_put", new_callable=AsyncMock) as mu:
            mp.return_value = _ok({"release": {"id": 7}}, 201)
            mu.return_value = _ok({"release": {"id": 7, "planning_fields": {}}})
            result = await tool.fn(
                action="create", subject="Release 3.0",
                description="Major", release_type=1,
                priority=2, status=1,
                planned_start_date="2026-07-01",
                planned_end_date="2026-07-15",
                planning_fields={"build_plan": {"description": "CI/CD pipeline"}}
            )
            assert result["success"] is True
            # Verify planning PUT
            mu.assert_called_once()
            assert "planning_fields" in mu.call_args.kwargs["json"]

    @pytest.mark.asyncio
    async def test_create_planning_put_failure_returns_warning(self, tool):
        """Planning PUT failure adds _warning to result."""
        with patch(f"{self.MOD}.api_post", new_callable=AsyncMock) as mp, \
             patch(f"{self.MOD}.api_put", new_callable=AsyncMock) as mu:
            mp.return_value = _ok({"release": {"id": 7}}, 201)
            mu.side_effect = Exception("Timeout")
            result = await tool.fn(
                action="create", subject="Release 3.1",
                description="Minor", release_type=1,
                priority=1, status=1,
                planned_start_date="2026-08-01",
                planned_end_date="2026-08-15",
                planning_fields={"test_plan": {"description": "Unit tests"}}
            )
            assert result["success"] is True
            # Warning in either release._warning or top-level
            release = result.get("release", {})
            assert "_warning" in release or "_warning" in str(result)

    @pytest.mark.asyncio
    async def test_create_api_error(self, tool):
        with patch(f"{self.MOD}.api_post", new_callable=AsyncMock) as m:
            m.side_effect = Exception("Server error")
            result = await tool.fn(
                action="create", subject="Fail",
                description="Fail", release_type=1,
                priority=1, status=1,
                planned_start_date="2026-01-01",
                planned_end_date="2026-01-02"
            )
            assert "error" in result

    @pytest.mark.asyncio
    async def test_restore(self, tool):
        with patch(f"{self.MOD}.api_put", new_callable=AsyncMock) as m:
            m.return_value = _ok({"release": {"id": 1}})
            result = await tool.fn(action="restore", release_id=1)
            assert result["success"] is True
            m.assert_called_once_with("releases/1/restore", json={})

    @pytest.mark.asyncio
    async def test_restore_missing_id(self, tool):
        result = await tool.fn(action="restore")
        assert "release_id required" in result["error"]

    @pytest.mark.asyncio
    async def test_filter(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"releases": [{"id": 1}]})
            result = await tool.fn(action="filter", query="status:1")
            assert "releases" in result
            params = m.call_args.kwargs["params"]
            assert '"status:1"' == params["query"]

    @pytest.mark.asyncio
    async def test_filter_missing_query(self, tool):
        result = await tool.fn(action="filter")
        assert "query required" in result["error"]

    @pytest.mark.asyncio
    async def test_get_fields(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"release_form_fields": []})
            result = await tool.fn(action="get_fields")
            assert "release_form_fields" in result
            m.assert_called_once_with("release_form_fields")

    @pytest.mark.asyncio
    async def test_update_api_error(self, tool):
        with patch(f"{self.MOD}.api_put", new_callable=AsyncMock) as m:
            m.side_effect = Exception("Server error")
            result = await tool.fn(action="update", release_id=1, subject="X")
            assert "error" in result

    @pytest.mark.asyncio
    async def test_delete_api_error(self, tool):
        with patch(f"{self.MOD}.api_delete", new_callable=AsyncMock) as m:
            m.side_effect = Exception("Server error")
            result = await tool.fn(action="delete", release_id=1)
            assert "error" in result


# ═══════════════════════════════════════════════════════════════════════════
# 11. tools/agents.py — groups, get_fields, filter pagination
# ═══════════════════════════════════════════════════════════════════════════
class TestAgentsFull:
    """Test agent group CRUD and filter pagination."""

    @pytest.fixture
    def tools(self):
        from freshservice_mcp.tools.agents import register_agents_tools
        mcp = FastMCP("test")
        register_agents_tools(mcp)
        return mcp._tool_manager._tools

    MOD = "freshservice_mcp.tools.agents"

    @pytest.mark.asyncio
    async def test_agent_get_fields(self, tools):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"agent_fields": [{"name": "email"}]})
            result = await tools["manage_agent"].fn(action="get_fields")
            assert "agent_fields" in result
            m.assert_called_once_with("agent_fields")

    @pytest.mark.asyncio
    async def test_agent_filter_pagination(self, tools):
        """Filter with pagination — follows Link header."""
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            page1 = _ok({"agents": [{"id": 1}]})
            page1.headers = {"Link": '<url>; rel="next"'}
            page2 = _ok({"agents": [{"id": 2}]})
            page2.headers = {"Link": ""}
            m.side_effect = [page1, page2]
            result = await tools["manage_agent"].fn(action="filter", query="active:true")
            assert result["total"] == 2
            assert len(result["agents"]) == 2

    @pytest.mark.asyncio
    async def test_agent_list_with_pagination(self, tools):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            resp = _ok({"agents": [{"id": 1}]})
            resp.headers = {"Link": '<next>; rel="next"'}
            m.return_value = resp
            result = await tools["manage_agent"].fn(action="list", page=1, per_page=10)
            assert "agents" in result
            assert "pagination" in result

    @pytest.mark.asyncio
    async def test_agent_get(self, tools):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"agent": {"id": 5}})
            result = await tools["manage_agent"].fn(action="get", agent_id=5)
            m.assert_called_once_with("agents/5")

    @pytest.mark.asyncio
    async def test_agent_get_missing_id(self, tools):
        result = await tools["manage_agent"].fn(action="get")
        assert "agent_id required" in result["error"]

    @pytest.mark.asyncio
    async def test_agent_update_no_fields(self, tools):
        result = await tools["manage_agent"].fn(action="update", agent_id=1)
        assert result == {"error": "No fields provided for update"}

    @pytest.mark.asyncio
    async def test_agent_unknown_action(self, tools):
        result = await tools["manage_agent"].fn(action="xyz")
        assert "Unknown action" in result["error"]

    # ── Groups ──
    @pytest.mark.asyncio
    async def test_group_list(self, tools):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"groups": [{"id": 1, "name": "IT"}]})
            result = await tools["manage_agent_group"].fn(action="list")
            assert "groups" in result

    @pytest.mark.asyncio
    async def test_group_get(self, tools):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"group": {"id": 1}})
            result = await tools["manage_agent_group"].fn(action="get", group_id=1)
            m.assert_called_once_with("groups/1")

    @pytest.mark.asyncio
    async def test_group_get_missing_id(self, tools):
        result = await tools["manage_agent_group"].fn(action="get")
        assert "group_id required" in result["error"]

    @pytest.mark.asyncio
    async def test_group_create(self, tools):
        with patch(f"{self.MOD}.api_post", new_callable=AsyncMock) as m:
            m.return_value = _ok({"group": {"id": 1}}, 201)
            result = await tools["manage_agent_group"].fn(
                action="create", name="DevOps",
                description="DevOps team", agent_ids=[1, 2, 3]
            )
            assert result["success"] is True
            payload = m.call_args.kwargs["json"]
            assert payload["name"] == "DevOps"
            assert payload["agent_ids"] == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_group_create_missing_name(self, tools):
        result = await tools["manage_agent_group"].fn(action="create")
        assert "name required" in result["error"]

    @pytest.mark.asyncio
    async def test_group_update(self, tools):
        with patch(f"{self.MOD}.api_put", new_callable=AsyncMock) as m:
            m.return_value = _ok({"group": {"id": 1}})
            result = await tools["manage_agent_group"].fn(
                action="update", group_id=1, name="DevOps Updated"
            )
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_group_update_missing_id(self, tools):
        result = await tools["manage_agent_group"].fn(action="update")
        assert "group_id required" in result["error"]

    @pytest.mark.asyncio
    async def test_group_update_no_fields(self, tools):
        result = await tools["manage_agent_group"].fn(action="update", group_id=1)
        assert result == {"error": "No fields provided for update"}

    @pytest.mark.asyncio
    async def test_group_unknown_action(self, tools):
        result = await tools["manage_agent_group"].fn(action="xyz")
        assert "Unknown action" in result["error"]


# ═══════════════════════════════════════════════════════════════════════════
# 12. tools/requesters.py — group, add_to_group, filter with include_agents
# ═══════════════════════════════════════════════════════════════════════════
class TestRequestersFull:
    """Test requester group CRUD and add_to_group."""

    @pytest.fixture
    def tools(self):
        from freshservice_mcp.tools.requesters import register_requesters_tools
        mcp = FastMCP("test")
        register_requesters_tools(mcp)
        return mcp._tool_manager._tools

    MOD = "freshservice_mcp.tools.requesters"

    @pytest.mark.asyncio
    async def test_get_fields(self, tools):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"requester_fields": []})
            result = await tools["manage_requester"].fn(action="get_fields")
            assert "requester_fields" in result

    @pytest.mark.asyncio
    async def test_get_missing_id(self, tools):
        result = await tools["manage_requester"].fn(action="get")
        assert "requester_id required" in result["error"]

    @pytest.mark.asyncio
    async def test_filter_with_include_agents(self, tools):
        """include_agents=True adds param to API call."""
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"requesters": [{"id": 1}]})
            result = await tools["manage_requester"].fn(
                action="filter", query='"email:test@co.com"',
                include_agents=True
            )
            params = m.call_args.kwargs["params"]
            assert params["include_agents"] == "true"

    @pytest.mark.asyncio
    async def test_filter_missing_query(self, tools):
        result = await tools["manage_requester"].fn(action="filter")
        assert "query required" in result["error"]

    @pytest.mark.asyncio
    async def test_create_missing_first_name(self, tools):
        result = await tools["manage_requester"].fn(action="create")
        assert "first_name required" in result["error"]

    @pytest.mark.asyncio
    async def test_create_with_all_fields(self, tools):
        with patch(f"{self.MOD}.api_post", new_callable=AsyncMock) as m:
            m.return_value = _ok({"requester": {"id": 1}}, 201)
            result = await tools["manage_requester"].fn(
                action="create", first_name="Alice",
                last_name="Smith", primary_email="alice@co.com",
                job_title="Engineer", department_ids=[1, 2]
            )
            assert result["success"] is True
            payload = m.call_args.kwargs["json"]
            assert payload["first_name"] == "Alice"
            assert payload["primary_email"] == "alice@co.com"
            assert payload["department_ids"] == [1, 2]

    @pytest.mark.asyncio
    async def test_update_no_fields(self, tools):
        result = await tools["manage_requester"].fn(action="update", requester_id=1)
        assert result == {"error": "No fields provided for update"}

    @pytest.mark.asyncio
    async def test_add_to_group(self, tools):
        with patch(f"{self.MOD}.api_post", new_callable=AsyncMock) as m:
            m.return_value = _ok({}, 200)
            result = await tools["manage_requester"].fn(
                action="add_to_group", requester_id=10, group_id=5
            )
            assert result["success"] is True
            m.assert_called_once_with("requester_groups/5/members/10")

    @pytest.mark.asyncio
    async def test_add_to_group_missing_fields(self, tools):
        result = await tools["manage_requester"].fn(action="add_to_group", requester_id=1)
        assert "group_id required" in result["error"]

    @pytest.mark.asyncio
    async def test_unknown_action(self, tools):
        result = await tools["manage_requester"].fn(action="xyz")
        assert "Unknown action" in result["error"]

    # ── Requester Groups ──
    @pytest.mark.asyncio
    async def test_group_list(self, tools):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            resp = _ok({"requester_groups": [{"id": 1}]})
            resp.headers = {"Link": ""}
            m.return_value = resp
            result = await tools["manage_requester_group"].fn(action="list")
            assert "requester_groups" in result

    @pytest.mark.asyncio
    async def test_group_get(self, tools):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"requester_group": {"id": 1}})
            result = await tools["manage_requester_group"].fn(action="get", group_id=1)
            m.assert_called_once_with("requester_groups/1")

    @pytest.mark.asyncio
    async def test_group_get_missing_id(self, tools):
        result = await tools["manage_requester_group"].fn(action="get")
        assert "group_id required" in result["error"]

    @pytest.mark.asyncio
    async def test_group_create(self, tools):
        with patch(f"{self.MOD}.api_post", new_callable=AsyncMock) as m:
            m.return_value = _ok({"requester_group": {"id": 1}}, 201)
            result = await tools["manage_requester_group"].fn(
                action="create", name="VIP Users", description="Top clients"
            )
            assert result["success"] is True
            payload = m.call_args.kwargs["json"]
            assert payload["name"] == "VIP Users"
            assert payload["description"] == "Top clients"

    @pytest.mark.asyncio
    async def test_group_create_missing_name(self, tools):
        result = await tools["manage_requester_group"].fn(action="create")
        assert "name required" in result["error"]

    @pytest.mark.asyncio
    async def test_group_update(self, tools):
        with patch(f"{self.MOD}.api_put", new_callable=AsyncMock) as m:
            m.return_value = _ok({"requester_group": {"id": 1}})
            result = await tools["manage_requester_group"].fn(
                action="update", group_id=1, name="Updated"
            )
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_group_update_missing_id(self, tools):
        result = await tools["manage_requester_group"].fn(action="update")
        assert "group_id required" in result["error"]

    @pytest.mark.asyncio
    async def test_group_update_no_fields(self, tools):
        result = await tools["manage_requester_group"].fn(action="update", group_id=1)
        assert result == {"error": "No fields provided for update"}

    @pytest.mark.asyncio
    async def test_group_list_members(self, tools):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"members": [{"id": 1}]})
            result = await tools["manage_requester_group"].fn(action="list_members", group_id=1)
            assert "members" in result

    @pytest.mark.asyncio
    async def test_group_list_members_missing_id(self, tools):
        result = await tools["manage_requester_group"].fn(action="list_members")
        assert "group_id required" in result["error"]

    @pytest.mark.asyncio
    async def test_group_unknown_action(self, tools):
        result = await tools["manage_requester_group"].fn(action="xyz")
        assert "Unknown action" in result["error"]


# ═══════════════════════════════════════════════════════════════════════════
# 13. tools/solutions.py — all CRUD actions
# ═══════════════════════════════════════════════════════════════════════════
class TestSolutionsFull:
    """Test solutions CRUD: categories, folders, articles."""

    @pytest.fixture
    def tool(self):
        from freshservice_mcp.tools.solutions import register_solutions_tools
        mcp = FastMCP("test")
        register_solutions_tools(mcp)
        return mcp._tool_manager._tools["manage_solution"]

    MOD = "freshservice_mcp.tools.solutions"

    # ── Categories ──
    @pytest.mark.asyncio
    async def test_create_category(self, tool):
        with patch(f"{self.MOD}.api_post", new_callable=AsyncMock) as m:
            m.return_value = _ok({"category": {"id": 1}}, 201)
            result = await tool.fn(
                action="create_category", name="FAQ",
                description="Frequently asked", workspace_id=1
            )
            assert result["success"] is True
            payload = m.call_args.kwargs["json"]
            assert payload["name"] == "FAQ"
            assert payload["workspace_id"] == 1

    @pytest.mark.asyncio
    async def test_create_category_missing_name(self, tool):
        result = await tool.fn(action="create_category")
        assert "name required" in result["error"]

    @pytest.mark.asyncio
    async def test_update_category(self, tool):
        with patch(f"{self.MOD}.api_put", new_callable=AsyncMock) as m:
            m.return_value = _ok({"category": {"id": 1}})
            result = await tool.fn(
                action="update_category", category_id=1, name="Updated FAQ"
            )
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_update_category_missing_id(self, tool):
        result = await tool.fn(action="update_category")
        assert "category_id required" in result["error"]

    @pytest.mark.asyncio
    async def test_update_category_no_fields(self, tool):
        result = await tool.fn(action="update_category", category_id=1)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_get_category(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"category": {"id": 1}})
            result = await tool.fn(action="get_category", category_id=1)
            m.assert_called_once_with("solutions/categories/1")

    # ── Folders ──
    @pytest.mark.asyncio
    async def test_list_folders(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"folders": []})
            result = await tool.fn(action="list_folders", category_id=1)
            assert "folders" in result

    @pytest.mark.asyncio
    async def test_list_folders_missing_id(self, tool):
        result = await tool.fn(action="list_folders")
        assert "category_id required" in result["error"]

    @pytest.mark.asyncio
    async def test_get_folder(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"folder": {"id": 1}})
            result = await tool.fn(action="get_folder", folder_id=1)
            m.assert_called_once_with("solutions/folders/1")

    @pytest.mark.asyncio
    async def test_get_folder_missing_id(self, tool):
        result = await tool.fn(action="get_folder")
        assert "folder_id required" in result["error"]

    @pytest.mark.asyncio
    async def test_create_folder(self, tool):
        with patch(f"{self.MOD}.api_post", new_callable=AsyncMock) as m:
            m.return_value = _ok({"folder": {"id": 1}}, 201)
            result = await tool.fn(
                action="create_folder", name="How-to",
                category_id=1, department_ids=[10, 20],
                description="How-to guides"
            )
            assert result["success"] is True
            payload = m.call_args.kwargs["json"]
            assert payload["name"] == "How-to"
            assert payload["category_id"] == 1
            assert payload["department_ids"] == [10, 20]
            assert payload["visibility"] == 4  # default

    @pytest.mark.asyncio
    async def test_create_folder_missing_fields(self, tool):
        result = await tool.fn(action="create_folder", name="X")
        assert "category_id and department_ids" in result["error"]

    @pytest.mark.asyncio
    async def test_update_folder(self, tool):
        with patch(f"{self.MOD}.api_put", new_callable=AsyncMock) as m:
            m.return_value = _ok({"folder": {"id": 1}})
            result = await tool.fn(
                action="update_folder", folder_id=1, name="Updated"
            )
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_update_folder_missing_id(self, tool):
        result = await tool.fn(action="update_folder")
        assert "folder_id required" in result["error"]

    @pytest.mark.asyncio
    async def test_update_folder_no_fields(self, tool):
        result = await tool.fn(action="update_folder", folder_id=1)
        assert "error" in result

    # ── Articles ──
    @pytest.mark.asyncio
    async def test_list_articles(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"articles": []})
            result = await tool.fn(action="list_articles", folder_id=1)
            assert "articles" in result

    @pytest.mark.asyncio
    async def test_list_articles_missing_folder(self, tool):
        result = await tool.fn(action="list_articles")
        assert "folder_id required" in result["error"]

    @pytest.mark.asyncio
    async def test_get_article(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"article": {"id": 1}})
            result = await tool.fn(action="get_article", article_id=1)
            m.assert_called_once_with("solutions/articles/1")

    @pytest.mark.asyncio
    async def test_get_article_missing_id(self, tool):
        result = await tool.fn(action="get_article")
        assert "article_id required" in result["error"]

    @pytest.mark.asyncio
    async def test_create_article(self, tool):
        with patch(f"{self.MOD}.api_post", new_callable=AsyncMock) as m:
            m.return_value = _ok({"article": {"id": 1}}, 201)
            result = await tool.fn(
                action="create_article", title="How to reset password",
                description="<p>Steps...</p>", folder_id=5,
                tags=["password", "reset"], keywords=["auth"]
            )
            assert result["success"] is True
            payload = m.call_args.kwargs["json"]
            assert payload["title"] == "How to reset password"
            assert payload["folder_id"] == 5
            assert payload["tags"] == ["password", "reset"]

    @pytest.mark.asyncio
    async def test_create_article_missing_fields(self, tool):
        result = await tool.fn(action="create_article", title="X")
        assert "description and folder_id" in result["error"]

    @pytest.mark.asyncio
    async def test_update_article(self, tool):
        with patch(f"{self.MOD}.api_put", new_callable=AsyncMock) as m:
            m.return_value = _ok({"article": {"id": 1}})
            result = await tool.fn(
                action="update_article", article_id=1, title="Updated title"
            )
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_update_article_missing_id(self, tool):
        result = await tool.fn(action="update_article")
        assert "article_id required" in result["error"]

    @pytest.mark.asyncio
    async def test_update_article_no_fields(self, tool):
        result = await tool.fn(action="update_article", article_id=1)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_publish_article(self, tool):
        with patch(f"{self.MOD}.api_put", new_callable=AsyncMock) as m:
            m.return_value = _ok({"article": {"id": 1, "status": 2}})
            result = await tool.fn(action="publish_article", article_id=1)
            assert result["success"] is True
            payload = m.call_args.kwargs["json"]
            assert payload == {"status": 2}

    @pytest.mark.asyncio
    async def test_publish_article_missing_id(self, tool):
        result = await tool.fn(action="publish_article")
        assert "article_id required" in result["error"]

    @pytest.mark.asyncio
    async def test_unknown_action(self, tool):
        result = await tool.fn(action="xyz")
        assert "Unknown action" in result["error"]


# ═══════════════════════════════════════════════════════════════════════════
# 14. tools/projects.py — archive, restore, members, associations, tasks
# ═══════════════════════════════════════════════════════════════════════════
class TestProjectsFull:
    """Test project actions: archive, restore, members, associations, tasks."""

    @pytest.fixture
    def tools(self):
        from freshservice_mcp.tools.projects import register_project_tools
        mcp = FastMCP("test")
        register_project_tools(mcp)
        return mcp._tool_manager._tools

    MOD = "freshservice_mcp.tools.projects"

    # ── manage_project ──
    @pytest.mark.asyncio
    async def test_create_success(self, tools):
        with patch(f"{self.MOD}.api_post", new_callable=AsyncMock) as m:
            m.return_value = _ok({"project": {"id": 1}}, 201)
            result = await tools["manage_project"].fn(
                action="create", name="Migration", project_type=1,
                description="DB migration", key="MIG",
                priority_id=2, manager_id=100
            )
            assert result["success"] is True
            payload = m.call_args.kwargs["json"]
            assert payload["name"] == "Migration"
            assert payload["project_type"] == 1
            assert payload["key"] == "MIG"

    @pytest.mark.asyncio
    async def test_create_missing_name(self, tools):
        result = await tools["manage_project"].fn(action="create", project_type=0)
        assert "name is required" in result["error"]

    @pytest.mark.asyncio
    async def test_create_missing_type(self, tools):
        result = await tools["manage_project"].fn(action="create", name="X")
        assert "project_type is required" in result["error"]

    @pytest.mark.asyncio
    async def test_update_no_fields(self, tools):
        result = await tools["manage_project"].fn(action="update", project_id=1)
        assert result == {"error": "No fields provided for update"}

    @pytest.mark.asyncio
    async def test_delete(self, tools):
        with patch(f"{self.MOD}.api_delete", new_callable=AsyncMock) as m:
            m.return_value = _no_content()
            result = await tools["manage_project"].fn(action="delete", project_id=1)
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_delete_missing_id(self, tools):
        result = await tools["manage_project"].fn(action="delete")
        assert "project_id required" in result["error"]

    @pytest.mark.asyncio
    async def test_archive(self, tools):
        with patch(f"{self.MOD}.api_post", new_callable=AsyncMock) as m:
            m.return_value = _ok({}, 200)
            result = await tools["manage_project"].fn(action="archive", project_id=1)
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_archive_missing_id(self, tools):
        result = await tools["manage_project"].fn(action="archive")
        assert "project_id required" in result["error"]

    @pytest.mark.asyncio
    async def test_restore(self, tools):
        with patch(f"{self.MOD}.api_post", new_callable=AsyncMock) as m:
            m.return_value = _ok({}, 200)
            result = await tools["manage_project"].fn(action="restore", project_id=1)
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_restore_missing_id(self, tools):
        result = await tools["manage_project"].fn(action="restore")
        assert "project_id required" in result["error"]

    @pytest.mark.asyncio
    async def test_get_fields(self, tools):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"project_fields": []})
            result = await tools["manage_project"].fn(action="get_fields")
            assert "project_fields" in result

    @pytest.mark.asyncio
    async def test_get_templates(self, tools):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"project_templates": []})
            result = await tools["manage_project"].fn(action="get_templates")
            assert "project_templates" in result

    @pytest.mark.asyncio
    async def test_add_members(self, tools):
        with patch(f"{self.MOD}.api_post", new_callable=AsyncMock) as m:
            m.return_value = _ok({"members": [{"id": 1}]}, 201)
            result = await tools["manage_project"].fn(
                action="add_members", project_id=1,
                members=[{"email": "user@test.com", "role": 1}]
            )
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_add_members_missing_id(self, tools):
        result = await tools["manage_project"].fn(action="add_members")
        assert "project_id required" in result["error"]

    @pytest.mark.asyncio
    async def test_add_members_missing_list(self, tools):
        result = await tools["manage_project"].fn(action="add_members", project_id=1)
        assert "members required" in result["error"]

    @pytest.mark.asyncio
    async def test_get_memberships(self, tools):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"memberships": []})
            result = await tools["manage_project"].fn(
                action="get_memberships", project_id=1
            )
            assert "memberships" in result

    @pytest.mark.asyncio
    async def test_get_memberships_missing_id(self, tools):
        result = await tools["manage_project"].fn(action="get_memberships")
        assert "project_id required" in result["error"]

    @pytest.mark.asyncio
    async def test_create_association(self, tools):
        with patch(f"{self.MOD}.api_post", new_callable=AsyncMock) as m:
            m.return_value = _ok({"ids": [10]}, 201)
            result = await tools["manage_project"].fn(
                action="create_association", project_id=1,
                module_name="tickets", ids=[10, 20]
            )
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_create_association_invalid_module(self, tools):
        result = await tools["manage_project"].fn(
            action="create_association", project_id=1,
            module_name="invalid", ids=[1]
        )
        assert "error" in result

    @pytest.mark.asyncio
    async def test_create_association_missing_ids(self, tools):
        result = await tools["manage_project"].fn(
            action="create_association", project_id=1,
            module_name="tickets"
        )
        assert "ids required" in result["error"]

    @pytest.mark.asyncio
    async def test_get_associations(self, tools):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"tickets": [{"id": 1}]})
            result = await tools["manage_project"].fn(
                action="get_associations", project_id=1,
                module_name="tickets"
            )
            assert "tickets" in result

    @pytest.mark.asyncio
    async def test_get_associations_invalid_module(self, tools):
        result = await tools["manage_project"].fn(
            action="get_associations", project_id=1,
            module_name="invalid"
        )
        assert "error" in result

    @pytest.mark.asyncio
    async def test_delete_association(self, tools):
        with patch(f"{self.MOD}.api_delete", new_callable=AsyncMock) as m:
            m.return_value = _no_content()
            result = await tools["manage_project"].fn(
                action="delete_association", project_id=1,
                module_name="tickets", association_id=10
            )
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_delete_association_missing_id(self, tools):
        result = await tools["manage_project"].fn(
            action="delete_association", project_id=1,
            module_name="tickets"
        )
        assert "association_id required" in result["error"]

    @pytest.mark.asyncio
    async def test_get_versions(self, tools):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"versions": []})
            result = await tools["manage_project"].fn(
                action="get_versions", project_id=1
            )
            assert "versions" in result

    @pytest.mark.asyncio
    async def test_get_sprints(self, tools):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"sprints": []})
            result = await tools["manage_project"].fn(
                action="get_sprints", project_id=1
            )
            assert "sprints" in result

    @pytest.mark.asyncio
    async def test_unknown_action(self, tools):
        result = await tools["manage_project"].fn(action="xyz")
        assert "Unknown action" in result["error"]

    # ── manage_project_task ──
    @pytest.mark.asyncio
    async def test_task_missing_project_id(self, tools):
        result = await tools["manage_project_task"].fn(action="list")
        assert "project_id is required" in result["error"]

    @pytest.mark.asyncio
    async def test_task_list(self, tools):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"tasks": []})
            result = await tools["manage_project_task"].fn(
                action="list", project_id=1
            )
            assert "tasks" in result

    @pytest.mark.asyncio
    async def test_task_filter(self, tools):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"tasks": []})
            result = await tools["manage_project_task"].fn(
                action="filter", project_id=1, query="priority_id:3"
            )
            assert "tasks" in result

    @pytest.mark.asyncio
    async def test_task_filter_missing_query(self, tools):
        result = await tools["manage_project_task"].fn(
            action="filter", project_id=1
        )
        assert "query required" in result["error"]

    @pytest.mark.asyncio
    async def test_task_get(self, tools):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"task": {"id": 5}})
            result = await tools["manage_project_task"].fn(
                action="get", project_id=1, task_id=5
            )
            assert "task" in result

    @pytest.mark.asyncio
    async def test_task_get_missing_id(self, tools):
        result = await tools["manage_project_task"].fn(
            action="get", project_id=1
        )
        assert "task_id required" in result["error"]

    @pytest.mark.asyncio
    async def test_task_create(self, tools):
        with patch(f"{self.MOD}.api_post", new_callable=AsyncMock) as m:
            m.return_value = _ok({"task": {"id": 1}}, 201)
            result = await tools["manage_project_task"].fn(
                action="create", project_id=1, title="Implement feature",
                type_id=2, priority_id=3, assignee_id=100,
                story_points=5, sprint_id=10
            )
            assert result["success"] is True
            payload = m.call_args.kwargs["json"]
            assert payload["title"] == "Implement feature"
            assert payload["type_id"] == 2
            assert payload["story_points"] == 5

    @pytest.mark.asyncio
    async def test_task_create_missing_title(self, tools):
        result = await tools["manage_project_task"].fn(
            action="create", project_id=1, type_id=1
        )
        assert "title is required" in result["error"]

    @pytest.mark.asyncio
    async def test_task_create_missing_type(self, tools):
        result = await tools["manage_project_task"].fn(
            action="create", project_id=1, title="X"
        )
        assert "type_id is required" in result["error"]

    @pytest.mark.asyncio
    async def test_task_update(self, tools):
        with patch(f"{self.MOD}.api_put", new_callable=AsyncMock) as m:
            m.return_value = _ok({"task": {"id": 1}})
            result = await tools["manage_project_task"].fn(
                action="update", project_id=1, task_id=1,
                title="Updated", status_id=3
            )
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_task_update_missing_task_id(self, tools):
        result = await tools["manage_project_task"].fn(
            action="update", project_id=1, title="X"
        )
        assert "task_id required" in result["error"]

    @pytest.mark.asyncio
    async def test_task_update_no_fields(self, tools):
        result = await tools["manage_project_task"].fn(
            action="update", project_id=1, task_id=1
        )
        assert result == {"error": "No fields provided for update"}

    @pytest.mark.asyncio
    async def test_task_delete(self, tools):
        with patch(f"{self.MOD}.api_delete", new_callable=AsyncMock) as m:
            m.return_value = _no_content()
            result = await tools["manage_project_task"].fn(
                action="delete", project_id=1, task_id=5
            )
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_task_delete_missing_id(self, tools):
        result = await tools["manage_project_task"].fn(
            action="delete", project_id=1
        )
        assert "task_id required" in result["error"]

    @pytest.mark.asyncio
    async def test_task_get_task_types(self, tools):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"task_types": []})
            result = await tools["manage_project_task"].fn(
                action="get_task_types", project_id=1
            )
            assert "task_types" in result

    @pytest.mark.asyncio
    async def test_task_get_task_type_fields(self, tools):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"fields": []})
            result = await tools["manage_project_task"].fn(
                action="get_task_type_fields", project_id=1, type_id=2
            )
            assert "fields" in result

    @pytest.mark.asyncio
    async def test_task_get_task_type_fields_missing_type(self, tools):
        result = await tools["manage_project_task"].fn(
            action="get_task_type_fields", project_id=1
        )
        assert "type_id required" in result["error"]

    @pytest.mark.asyncio
    async def test_task_get_statuses(self, tools):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"task_statuses": []})
            result = await tools["manage_project_task"].fn(
                action="get_task_statuses", project_id=1
            )
            assert "task_statuses" in result

    @pytest.mark.asyncio
    async def test_task_get_priorities(self, tools):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"task_priorities": []})
            result = await tools["manage_project_task"].fn(
                action="get_task_priorities", project_id=1
            )
            assert "task_priorities" in result

    @pytest.mark.asyncio
    async def test_task_create_note(self, tools):
        with patch(f"{self.MOD}.api_post", new_callable=AsyncMock) as m:
            m.return_value = _ok({"notes": [{"id": 1}]}, 201)
            result = await tools["manage_project_task"].fn(
                action="create_note", project_id=1, task_id=5,
                content="<p>Progress update</p>"
            )
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_task_create_note_missing_task_id(self, tools):
        result = await tools["manage_project_task"].fn(
            action="create_note", project_id=1, content="X"
        )
        assert "task_id required" in result["error"]

    @pytest.mark.asyncio
    async def test_task_create_note_missing_content(self, tools):
        result = await tools["manage_project_task"].fn(
            action="create_note", project_id=1, task_id=1
        )
        assert "content required" in result["error"]

    @pytest.mark.asyncio
    async def test_task_list_notes(self, tools):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"notes": []})
            result = await tools["manage_project_task"].fn(
                action="list_notes", project_id=1, task_id=1
            )
            assert "notes" in result

    @pytest.mark.asyncio
    async def test_task_list_notes_missing_id(self, tools):
        result = await tools["manage_project_task"].fn(
            action="list_notes", project_id=1
        )
        assert "task_id required" in result["error"]

    @pytest.mark.asyncio
    async def test_task_update_note(self, tools):
        with patch(f"{self.MOD}.api_put", new_callable=AsyncMock) as m:
            m.return_value = _ok({"note": {"id": 1}})
            result = await tools["manage_project_task"].fn(
                action="update_note", project_id=1, task_id=1,
                note_id=1, content="<p>Updated</p>"
            )
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_task_update_note_missing_ids(self, tools):
        result = await tools["manage_project_task"].fn(
            action="update_note", project_id=1, content="X"
        )
        assert "task_id and note_id" in result["error"]

    @pytest.mark.asyncio
    async def test_task_update_note_missing_content(self, tools):
        result = await tools["manage_project_task"].fn(
            action="update_note", project_id=1, task_id=1, note_id=1
        )
        assert "content required" in result["error"]

    @pytest.mark.asyncio
    async def test_task_delete_note(self, tools):
        with patch(f"{self.MOD}.api_delete", new_callable=AsyncMock) as m:
            m.return_value = _no_content()
            result = await tools["manage_project_task"].fn(
                action="delete_note", project_id=1, task_id=1, note_id=1
            )
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_task_delete_note_missing_ids(self, tools):
        result = await tools["manage_project_task"].fn(
            action="delete_note", project_id=1
        )
        assert "task_id and note_id" in result["error"]

    @pytest.mark.asyncio
    async def test_task_create_association(self, tools):
        with patch(f"{self.MOD}.api_post", new_callable=AsyncMock) as m:
            m.return_value = _ok({"ids": [1]}, 201)
            result = await tools["manage_project_task"].fn(
                action="create_association", project_id=1,
                task_id=5, module_name="tickets", ids=[10]
            )
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_task_create_association_missing_task_id(self, tools):
        result = await tools["manage_project_task"].fn(
            action="create_association", project_id=1,
            module_name="tickets", ids=[1]
        )
        assert "task_id required" in result["error"]

    @pytest.mark.asyncio
    async def test_task_create_association_invalid_module(self, tools):
        result = await tools["manage_project_task"].fn(
            action="create_association", project_id=1,
            task_id=1, module_name="invalid", ids=[1]
        )
        assert "error" in result

    @pytest.mark.asyncio
    async def test_task_create_association_missing_ids(self, tools):
        result = await tools["manage_project_task"].fn(
            action="create_association", project_id=1,
            task_id=1, module_name="tickets"
        )
        assert "ids required" in result["error"]

    @pytest.mark.asyncio
    async def test_task_get_associations(self, tools):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"tickets": []})
            result = await tools["manage_project_task"].fn(
                action="get_associations", project_id=1,
                task_id=1, module_name="tickets"
            )
            assert "tickets" in result

    @pytest.mark.asyncio
    async def test_task_get_associations_missing_task_id(self, tools):
        result = await tools["manage_project_task"].fn(
            action="get_associations", project_id=1,
            module_name="tickets"
        )
        assert "task_id required" in result["error"]

    @pytest.mark.asyncio
    async def test_task_delete_association(self, tools):
        with patch(f"{self.MOD}.api_delete", new_callable=AsyncMock) as m:
            m.return_value = _no_content()
            result = await tools["manage_project_task"].fn(
                action="delete_association", project_id=1,
                task_id=1, module_name="tickets", association_id=10
            )
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_task_delete_association_missing_task_id(self, tools):
        result = await tools["manage_project_task"].fn(
            action="delete_association", project_id=1,
            module_name="tickets", association_id=10
        )
        assert "task_id required" in result["error"]

    @pytest.mark.asyncio
    async def test_task_delete_association_missing_assoc_id(self, tools):
        result = await tools["manage_project_task"].fn(
            action="delete_association", project_id=1,
            task_id=1, module_name="tickets"
        )
        assert "association_id required" in result["error"]

    @pytest.mark.asyncio
    async def test_task_unknown_action(self, tools):
        result = await tools["manage_project_task"].fn(
            action="xyz", project_id=1
        )
        assert "Unknown action" in result["error"]


# ═══════════════════════════════════════════════════════════════════════════
# 15. tools/tickets.py — create validation, filter with workspace_id
# ═══════════════════════════════════════════════════════════════════════════
class TestTicketsFull:
    """Test ticket create/update validation and filter workspace param."""

    @pytest.fixture
    def tool(self):
        from freshservice_mcp.tools.tickets import register_tickets_tools
        mcp = FastMCP("test")
        register_tickets_tools(mcp)
        return mcp._tool_manager._tools["manage_ticket"]

    MOD = "freshservice_mcp.tools.tickets"

    @pytest.mark.asyncio
    async def test_create_missing_email_and_requester(self, tool):
        result = await tool.fn(
            action="create", subject="Test", description="Desc"
        )
        assert "email or requester_id" in result["error"]

    @pytest.mark.asyncio
    async def test_create_invalid_enum(self, tool):
        result = await tool.fn(
            action="create", subject="Test", description="Desc",
            email="test@test.com", priority="not_a_number"
        )
        assert "Invalid value" in result["error"]

    @pytest.mark.asyncio
    async def test_create_with_custom_fields(self, tool):
        with patch(f"{self.MOD}.api_post", new_callable=AsyncMock) as m:
            m.return_value = _ok({"ticket": {"id": 1}}, 201)
            result = await tool.fn(
                action="create", subject="New ticket",
                description="Description here",
                email="user@test.com", priority=3,
                custom_fields={"cf_environment": "production"}
            )
            assert result["success"] is True
            payload = m.call_args.kwargs["json"]
            assert payload["custom_fields"] == {"cf_environment": "production"}
            assert payload["priority"] == 3

    @pytest.mark.asyncio
    async def test_filter_with_workspace_id(self, tool):
        """workspace_id is appended to filter URL."""
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"tickets": []})
            result = await tool.fn(
                action="filter", query="status:2", workspace_id=5
            )
            # Verify workspace_id in URL
            call_url = m.call_args.args[0]
            assert "workspace_id=5" in call_url

    @pytest.mark.asyncio
    async def test_filter_missing_query(self, tool):
        result = await tool.fn(action="filter")
        assert "query is required" in result["error"]

    @pytest.mark.asyncio
    async def test_update_no_fields(self, tool):
        result = await tool.fn(action="update", ticket_id=1)
        assert result == {"error": "No fields provided for update"}

    @pytest.mark.asyncio
    async def test_update_with_priority_and_status(self, tool):
        with patch(f"{self.MOD}.api_put", new_callable=AsyncMock) as m:
            m.return_value = _ok({"ticket": {"id": 1}})
            result = await tool.fn(
                action="update", ticket_id=1, priority=4, status=3
            )
            assert result["success"] is True
            payload = m.call_args.kwargs["json"]
            assert payload["priority"] == 4
            assert payload["status"] == 3

    @pytest.mark.asyncio
    async def test_delete_unexpected_status(self, tool):
        with patch(f"{self.MOD}.api_delete", new_callable=AsyncMock) as m:
            r = MagicMock()
            r.status_code = 409
            m.return_value = r
            result = await tool.fn(action="delete", ticket_id=1)
            assert "Unexpected status" in result["error"]

    @pytest.mark.asyncio
    async def test_get_fields(self, tool):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.return_value = _ok({"ticket_form_fields": []})
            result = await tool.fn(action="get_fields")
            assert "ticket_form_fields" in result
            m.assert_called_once_with("ticket_form_fields")


# ═══════════════════════════════════════════════════════════════════════════
# 16. tools/assets.py — relationship, component, filter/search errors
# ═══════════════════════════════════════════════════════════════════════════
class TestAssetsFull:
    """Test asset create with all fields, component/relationship sub-tools."""

    @pytest.fixture
    def tools(self):
        from freshservice_mcp.tools.assets import register_assets_tools
        mcp = FastMCP("test")
        register_assets_tools(mcp)
        return mcp._tool_manager._tools

    MOD = "freshservice_mcp.tools.assets"

    @pytest.mark.asyncio
    async def test_create_with_all_fields(self, tools):
        """Verify all optional fields are sent in asset create."""
        with patch(f"{self.MOD}.api_post", new_callable=AsyncMock) as m:
            m.return_value = _ok({"asset": {"id": 1}}, 201)
            result = await tools["manage_asset"].fn(
                action="create", name="Server-01",
                asset_type_id=3, description="Prod server",
                asset_tag="SRV-001", impact="high",
                agent_id=100, department_id=10,
                location_id=5, group_id=7
            )
            assert result.get("success") is True or "asset" in result
            payload = m.call_args.kwargs["json"]
            assert payload["name"] == "Server-01"
            assert payload["asset_type_id"] == 3
            assert payload["asset_tag"] == "SRV-001"

    @pytest.mark.asyncio
    async def test_search_missing_query(self, tools):
        result = await tools["manage_asset"].fn(action="search")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_filter_missing_query(self, tools):
        result = await tools["manage_asset"].fn(action="filter")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_get_types_api_error(self, tools):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.side_effect = Exception("Timeout")
            result = await tools["manage_asset"].fn(action="get_types")
            assert "error" in result

    @pytest.mark.asyncio
    async def test_list_api_error(self, tools):
        with patch(f"{self.MOD}.api_get", new_callable=AsyncMock) as m:
            m.side_effect = Exception("Network")
            result = await tools["manage_asset"].fn(action="list")
            assert "error" in result

    @pytest.mark.asyncio
    async def test_update_api_error(self, tools):
        with patch(f"{self.MOD}.api_put", new_callable=AsyncMock) as m:
            m.side_effect = Exception("Server error")
            result = await tools["manage_asset"].fn(
                action="update", display_id=1, name="X"
            )
            assert "error" in result

    @pytest.mark.asyncio
    async def test_delete_api_error(self, tools):
        with patch(f"{self.MOD}.api_delete", new_callable=AsyncMock) as m:
            m.side_effect = Exception("Server error")
            result = await tools["manage_asset"].fn(action="delete", display_id=1)
            assert "error" in result
