"""Tests for freshservice_mcp.telemetry module."""
import time
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from freshservice_mcp.telemetry import (
    _path_root,
    metrics_response,
    instrument_tool,
    trace_span,
    init_telemetry,
    TOOL_CALLS,
    TOOL_DURATION,
    API_REQUESTS,
    API_DURATION,
    REGISTRY,
    INFO,
)


class TestPathRoot:
    def test_simple_path(self):
        assert _path_root("tickets/42") == "tickets"

    def test_nested_path(self):
        assert _path_root("catalog/items/3") == "catalog"

    def test_empty_path(self):
        assert _path_root("") == "unknown"

    def test_leading_slash(self):
        assert _path_root("/tickets/42") == "tickets"

    def test_trailing_slash(self):
        assert _path_root("changes/") == "changes"

    def test_single_segment(self):
        assert _path_root("agents") == "agents"


class TestMetricsResponse:
    def test_returns_bytes(self):
        result = metrics_response()
        assert isinstance(result, bytes)

    def test_contains_metric_names(self):
        result = metrics_response().decode()
        assert "freshservice_mcp_tool_calls_total" in result


class TestInstrumentTool:
    @pytest.mark.asyncio
    async def test_successful_call(self):
        async def my_tool(x: int) -> dict:
            return {"result": x * 2}

        wrapped = instrument_tool(my_tool)
        result = await wrapped(5)
        assert result == {"result": 10}

    @pytest.mark.asyncio
    async def test_error_result(self):
        async def failing_tool() -> dict:
            return {"error": "something went wrong"}

        wrapped = instrument_tool(failing_tool)
        result = await wrapped()
        assert result == {"error": "something went wrong"}

    @pytest.mark.asyncio
    async def test_exception_propagated(self):
        async def exploding_tool():
            raise ValueError("boom")

        wrapped = instrument_tool(exploding_tool)
        with pytest.raises(ValueError, match="boom"):
            await wrapped()


class TestTraceSpan:
    @pytest.mark.asyncio
    async def test_no_tracer_yields_none(self):
        async with trace_span("test.span") as span:
            assert span is None


class TestInitTelemetry:
    def test_without_otlp_endpoint(self):
        with patch.dict("os.environ", {"OTEL_EXPORTER_OTLP_ENDPOINT": ""}):
            init_telemetry(version="1.0.0", transport="sse")
            # Should not crash
