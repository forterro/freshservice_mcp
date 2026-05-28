"""Tests for freshservice_mcp.http_client module."""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
import httpx

from freshservice_mcp.http_client import (
    api_url,
    get_auth_headers,
    get_auth_headers_readonly,
    parse_link_header,
    handle_error,
    api_get,
    api_post,
    api_put,
    api_delete,
    cached_api_get,
)


class TestApiUrl:
    def test_simple_path(self):
        result = api_url("tickets/42")
        assert result == "https://test.freshservice.com/api/v2/tickets/42"

    def test_strips_leading_slash(self):
        result = api_url("/tickets/42")
        assert result == "https://test.freshservice.com/api/v2/tickets/42"

    def test_empty_path(self):
        result = api_url("")
        assert result == "https://test.freshservice.com/api/v2/"


class TestAuthHeaders:
    def test_get_auth_headers_has_content_type(self):
        headers = get_auth_headers()
        assert "Authorization" in headers
        assert headers["Content-Type"] == "application/json"

    def test_get_auth_headers_readonly_no_content_type(self):
        headers = get_auth_headers_readonly()
        assert "Authorization" in headers
        assert "Content-Type" not in headers

    def test_uses_basic_auth_by_default(self):
        headers = get_auth_headers()
        assert headers["Authorization"].startswith("Basic ")


class TestParseLinkHeader:
    def test_empty_header(self):
        result = parse_link_header("")
        assert result == {"next": None, "prev": None}

    def test_next_link(self):
        header = '<https://api.freshservice.com/v2/tickets?page=2>; rel="next"'
        result = parse_link_header(header)
        assert result["next"] == 2
        assert result["prev"] is None

    def test_both_links(self):
        header = (
            '<https://api.freshservice.com/v2/tickets?page=3>; rel="next", '
            '<https://api.freshservice.com/v2/tickets?page=1>; rel="prev"'
        )
        result = parse_link_header(header)
        assert result["next"] == 3
        assert result["prev"] == 1


class TestHandleError:
    def test_http_status_error(self):
        response = MagicMock()
        response.json.return_value = {"description": "Not found"}
        error = httpx.HTTPStatusError(
            "404 Not Found",
            request=httpx.Request("GET", "https://test.com"),
            response=response,
        )
        result = handle_error(error, "get ticket")
        assert result["success"] is False
        assert "Failed to get ticket" in result["error"]
        assert result["details"] == {"description": "Not found"}

    def test_http_status_error_non_json(self):
        response = MagicMock()
        response.json.side_effect = Exception("not json")
        response.text = "Server error"
        error = httpx.HTTPStatusError(
            "500",
            request=httpx.Request("GET", "https://test.com"),
            response=response,
        )
        result = handle_error(error, "create asset")
        assert result["success"] is False
        assert result["details"] == "Server error"

    def test_generic_exception(self):
        error = RuntimeError("connection timeout")
        result = handle_error(error, "list agents")
        assert result["success"] is False
        assert "Unexpected error" in result["error"]
        assert "connection timeout" in result["error"]


class TestApiGet:
    @pytest.mark.asyncio
    async def test_successful_get(self):
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200

        with patch("freshservice_mcp.http_client.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            result = await api_get("tickets/42")
            assert result.status_code == 200
            mock_instance.get.assert_called_once()


class TestApiPost:
    @pytest.mark.asyncio
    async def test_successful_post(self):
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 201

        with patch("freshservice_mcp.http_client.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            result = await api_post("tickets", json={"subject": "test"})
            assert result.status_code == 201


class TestApiPut:
    @pytest.mark.asyncio
    async def test_successful_put(self):
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200

        with patch("freshservice_mcp.http_client.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.put = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            result = await api_put("tickets/42", json={"status": 3})
            assert result.status_code == 200


class TestApiDelete:
    @pytest.mark.asyncio
    async def test_successful_delete(self):
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 204

        with patch("freshservice_mcp.http_client.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.delete = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            result = await api_delete("tickets/42")
            assert result.status_code == 204


class TestCachedApiGet:
    @pytest.mark.asyncio
    async def test_cache_miss_calls_api(self):
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.is_success = True
        mock_response.text = '{"tickets": []}'

        with patch("freshservice_mcp.http_client.cache_get", new_callable=AsyncMock) as mock_cache_get, \
             patch("freshservice_mcp.http_client.cache_set", new_callable=AsyncMock) as mock_cache_set, \
             patch("freshservice_mcp.http_client.api_get", new_callable=AsyncMock) as mock_api_get:
            mock_cache_get.return_value = None
            mock_api_get.return_value = mock_response

            result = await cached_api_get("tickets")
            assert result.status_code == 200
            mock_cache_set.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_hit_skips_api(self):
        with patch("freshservice_mcp.http_client.cache_get", new_callable=AsyncMock) as mock_cache_get, \
             patch("freshservice_mcp.http_client.api_get", new_callable=AsyncMock) as mock_api_get:
            mock_cache_get.return_value = '{"tickets": [{"id": 1}]}'

            result = await cached_api_get("tickets")
            assert result.status_code == 200
            mock_api_get.assert_not_called()
