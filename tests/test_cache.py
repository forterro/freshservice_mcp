"""Tests for freshservice_mcp.cache module."""
import time
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from freshservice_mcp.cache import (
    _cache_key,
    _is_reference_path,
    _ttl_for,
    _mem_get,
    _mem_set,
    cache_get,
    cache_set,
    cache_invalidate,
    _mem_cache,
    TTL_REFERENCE,
    TTL_OPERATIONAL,
)


class TestIsReferencePath:
    def test_agent_fields_is_reference(self):
        assert _is_reference_path("agent_fields") is True

    def test_ticket_form_fields_is_reference(self):
        assert _is_reference_path("ticket_form_fields") is True

    def test_departments_is_reference(self):
        assert _is_reference_path("departments") is True

    def test_tickets_is_not_reference(self):
        assert _is_reference_path("tickets/42") is False

    def test_changes_is_not_reference(self):
        assert _is_reference_path("changes") is False


class TestTtlFor:
    def test_reference_path_ttl(self):
        assert _ttl_for("agent_fields") == TTL_REFERENCE

    def test_operational_path_ttl(self):
        assert _ttl_for("tickets/42") == TTL_OPERATIONAL


class TestCacheKey:
    def test_reference_path_key(self):
        key = _cache_key("agent_fields")
        assert key.startswith("fs:ref:")
        assert "agent_fields" in key

    def test_operational_path_key(self):
        key = _cache_key("tickets/42")
        assert key.startswith("fs:op:")
        assert "tickets/42" in key

    def test_with_params(self):
        key1 = _cache_key("tickets", {"page": 1})
        key2 = _cache_key("tickets", {"page": 2})
        assert key1 != key2


class TestMemCache:
    def setup_method(self):
        _mem_cache.clear()

    def test_set_and_get(self):
        _mem_set("testkey", '{"data": true}', 3600)
        result = _mem_get("testkey")
        assert result == '{"data": true}'

    def test_get_missing_key(self):
        result = _mem_get("nonexistent")
        assert result is None

    def test_expired_entry(self):
        _mem_set("testkey", '{"data": true}', 1)
        # Manually expire by setting expires_at in the past
        _mem_cache["testkey"] = (time.time() - 10, '{"data": true}')
        result = _mem_get("testkey")
        assert result is None


class TestCacheGetSet:
    def setup_method(self):
        _mem_cache.clear()

    @pytest.mark.asyncio
    async def test_cache_roundtrip_mem(self):
        with patch("freshservice_mcp.cache.REDIS_URL", ""):
            await cache_set("tickets/1", '{"id": 1}')
            result = await cache_get("tickets/1")
            assert result == '{"id": 1}'

    @pytest.mark.asyncio
    async def test_cache_miss_mem(self):
        with patch("freshservice_mcp.cache.REDIS_URL", ""):
            result = await cache_get("nonexistent/path")
            assert result is None


class TestCacheInvalidate:
    def setup_method(self):
        _mem_cache.clear()

    @pytest.mark.asyncio
    async def test_invalidate_all_mem(self):
        with patch("freshservice_mcp.cache.REDIS_URL", ""):
            await cache_set("tickets/1", '{"id": 1}')
            await cache_set("tickets/2", '{"id": 2}')
            count = await cache_invalidate()
            assert count >= 2
            assert len(_mem_cache) == 0

    @pytest.mark.asyncio
    async def test_invalidate_specific_mem(self):
        with patch("freshservice_mcp.cache.REDIS_URL", ""):
            await cache_set("tickets/1", '{"id": 1}')
            await cache_set("tickets/2", '{"id": 2}')
            count = await cache_invalidate("tickets/1")
            assert count == 1
