"""Freshservice MCP — Observability: Prometheus metrics + OpenTelemetry tracing.

Initialised once at server startup via ``init_telemetry()``.
All metrics are defined here and imported by the modules that need them.

Configuration (env vars):
  OTEL_EXPORTER_OTLP_ENDPOINT  — OTLP collector (e.g. http://alloy:4317).
                                  When unset, tracing is disabled.
  OTEL_SERVICE_NAME            — Service name for traces (default: freshservice-mcp).
  METRICS_ENABLED              — Set to "false" to disable /metrics (default: true).
"""

import logging
import os
import time
from contextlib import asynccontextmanager
from functools import wraps
from typing import Any, Callable, Optional

from prometheus_client import (
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prometheus metrics
# ---------------------------------------------------------------------------
REGISTRY = CollectorRegistry()

# -- Tool calls
TOOL_CALLS = Counter(
    "freshservice_mcp_tool_calls_total",
    "Total MCP tool invocations",
    ["tool", "status"],
    registry=REGISTRY,
)
TOOL_DURATION = Histogram(
    "freshservice_mcp_tool_duration_seconds",
    "Tool execution latency",
    ["tool"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30),
    registry=REGISTRY,
)

# -- Freshservice API calls
API_REQUESTS = Counter(
    "freshservice_mcp_api_requests_total",
    "HTTP requests to Freshservice API",
    ["method", "path_root", "status_code"],
    registry=REGISTRY,
)
API_DURATION = Histogram(
    "freshservice_mcp_api_duration_seconds",
    "Freshservice API request latency",
    ["method", "path_root"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
    registry=REGISTRY,
)

# -- Cache
CACHE_OPS = Counter(
    "freshservice_mcp_cache_operations_total",
    "Cache operations",
    ["operation", "tier"],
    registry=REGISTRY,
)
CACHE_ENTRIES = Gauge(
    "freshservice_mcp_cache_entries",
    "Current number of cache entries (in-memory only)",
    registry=REGISTRY,
)
REDIS_CONNECTED = Gauge(
    "freshservice_mcp_redis_connected",
    "Whether Redis is reachable (1=yes, 0=no)",
    registry=REGISTRY,
)

# -- Auth
AUTH_MODE = Counter(
    "freshservice_mcp_auth_mode_total",
    "Authentication mode used",
    ["mode"],
    registry=REGISTRY,
)

# -- Server info
INFO = Gauge(
    "freshservice_mcp_info",
    "Static build metadata",
    ["version", "transport"],
    registry=REGISTRY,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _path_root(path: str) -> str:
    """Collapse API paths to their root for cardinality control.

    ``tickets/42`` → ``tickets``, ``catalog/items/3`` → ``catalog``.
    """
    return path.strip("/").split("/")[0] if path else "unknown"


def metrics_response() -> bytes:
    """Render Prometheus exposition format."""
    return generate_latest(REGISTRY)


# ---------------------------------------------------------------------------
# OpenTelemetry tracing (optional)
# ---------------------------------------------------------------------------
_tracer = None  # set by init_telemetry()


def get_tracer():
    """Return the OTel tracer (or a no-op if tracing is disabled)."""
    return _tracer


@asynccontextmanager
async def trace_span(name: str, attributes: Optional[dict] = None):
    """Async context manager that creates a span if tracing is enabled."""
    if _tracer is None:
        yield None
        return
    with _tracer.start_as_current_span(name, attributes=attributes or {}) as span:
        yield span


# ---------------------------------------------------------------------------
# Tool instrumentation decorator
# ---------------------------------------------------------------------------
def instrument_tool(func: Callable) -> Callable:
    """Decorator that wraps an MCP tool handler with metrics + tracing."""
    tool_name = func.__name__

    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        start = time.monotonic()
        status = "ok"
        try:
            async with trace_span(f"tool.{tool_name}", {"tool.name": tool_name}) as span:
                result = await func(*args, **kwargs)
                if isinstance(result, dict) and result.get("error"):
                    status = "error"
                    if span:
                        span.set_attribute("error", True)
                        span.set_attribute("error.message", str(result["error"])[:200])
                return result
        except Exception:
            status = "error"
            raise
        finally:
            elapsed = time.monotonic() - start
            TOOL_CALLS.labels(tool=tool_name, status=status).inc()
            TOOL_DURATION.labels(tool=tool_name).observe(elapsed)

    return wrapper


# ---------------------------------------------------------------------------
# Initialisation (called once from server.py)
# ---------------------------------------------------------------------------
def init_telemetry(version: str = "unknown", transport: str = "unknown") -> None:  # pragma: no cover
    """Set up metrics + optional OTel tracing."""
    global _tracer

    INFO.labels(version=version, transport=transport).set(1)

    # -- OpenTelemetry (only if OTLP endpoint is configured)
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip()
    if not otlp_endpoint:
        log.info("Telemetry: tracing disabled (OTEL_EXPORTER_OTLP_ENDPOINT not set)")
        return

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource

        service_name = os.getenv("OTEL_SERVICE_NAME", "freshservice-mcp")
        resource = Resource.create({"service.name": service_name, "service.version": version})
        provider = TracerProvider(resource=resource)

        exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
        provider.add_span_processor(BatchSpanProcessor(exporter))

        trace.set_tracer_provider(provider)
        _tracer = trace.get_tracer("freshservice_mcp")

        # Auto-instrument httpx
        try:
            from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentation
            HTTPXClientInstrumentation().instrument()
        except ImportError:
            pass

        log.info("Telemetry: tracing enabled → %s (service=%s)", otlp_endpoint, service_name)

    except ImportError:
        log.info("Telemetry: opentelemetry packages not installed, tracing disabled")
    except Exception:
        log.exception("Telemetry: failed to initialise tracing")
