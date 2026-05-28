"""Tests for freshservice_mcp.discovery module."""
import json
import time
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from pathlib import Path

from freshservice_mcp.discovery import (
    _read_cache,
    _write_cache,
    invalidate_cache,
    _fetch_fields,
    _fetch_asset_types,
    _FIELD_ENDPOINTS,
    _mem_cache,
)


class TestDiscoveryCache:
    def setup_method(self):
        _mem_cache.clear()

    def test_write_and_read_cache(self):
        _write_cache("test_key", {"fields": [1, 2, 3]})
        result = _read_cache("test_key")
        assert result == {"fields": [1, 2, 3]}

    def test_read_cache_miss(self):
        result = _read_cache("nonexistent")
        assert result is None

    def test_invalidate_specific(self):
        _write_cache("fields_ticket", {"fields": []})
        invalidate_cache("fields_ticket")
        assert _read_cache("fields_ticket") is None

    def test_invalidate_all(self):
        _write_cache("fields_ticket", {"fields": []})
        _write_cache("fields_change", {"fields": []})
        invalidate_cache()
        assert _read_cache("fields_ticket") is None
        assert _read_cache("fields_change") is None


class TestFieldEndpoints:
    def test_ticket_endpoint(self):
        assert _FIELD_ENDPOINTS["ticket"] == "ticket_form_fields"

    def test_change_endpoint(self):
        assert _FIELD_ENDPOINTS["change"] == "change_form_fields"

    def test_agent_endpoint(self):
        assert _FIELD_ENDPOINTS["agent"] == "agent_fields"

    def test_requester_endpoint(self):
        assert _FIELD_ENDPOINTS["requester"] == "requester_fields"


class TestFetchFields:
    @pytest.mark.asyncio
    async def test_unknown_entity_type(self):
        result = await _fetch_fields("unknown_type")
        assert "error" in result
        assert "Unknown entity type" in result["error"]

    @pytest.mark.asyncio
    async def test_cached_result(self):
        _mem_cache.clear()
        _write_cache("fields_ticket", {"fields": [{"name": "subject"}]})
        result = await _fetch_fields("ticket")
        assert result["source"] == "cache"
        assert result["fields"] == {"fields": [{"name": "subject"}]}

    @pytest.mark.asyncio
    async def test_api_call_on_miss(self):
        _mem_cache.clear()
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"ticket_fields": [{"name": "subject"}]}

        with patch("freshservice_mcp.discovery.api_get", new_callable=AsyncMock) as mock_get, \
             patch("freshservice_mcp.discovery._read_cache", return_value=None):
            mock_get.return_value = mock_resp
            result = await _fetch_fields("ticket")
            assert result["source"] == "api"
            mock_get.assert_called_once_with("ticket_form_fields")


class TestFetchAssetTypes:
    @pytest.mark.asyncio
    async def test_cached_result(self):
        _mem_cache.clear()
        _write_cache("asset_types", [{"id": 1, "name": "Laptop"}])
        result = await _fetch_asset_types()
        assert result["source"] == "cache"
        assert result["asset_types"] == [{"id": 1, "name": "Laptop"}]

    @pytest.mark.asyncio
    async def test_api_pagination(self):
        _mem_cache.clear()
        page1_resp = MagicMock()
        page1_resp.raise_for_status = MagicMock()
        page1_resp.json.return_value = {"asset_types": [{"id": 1}]}

        page2_resp = MagicMock()
        page2_resp.raise_for_status = MagicMock()
        page2_resp.json.return_value = {"asset_types": []}

        with patch("freshservice_mcp.discovery.api_get", new_callable=AsyncMock) as mock_get, \
             patch("freshservice_mcp.discovery._read_cache", return_value=None):
            mock_get.side_effect = [page1_resp, page2_resp]
            result = await _fetch_asset_types()
            assert result["source"] == "api"
            assert len(result["asset_types"]) == 1
