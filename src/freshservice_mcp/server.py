"""Freshservice MCP Server — slim entry-point.

All tools live in ``freshservice_mcp.tools.*`` sub-modules.
This file creates the FastMCP instance, loads the requested scopes,
and starts the server.

Usage:
    freshservice-mcp                          # loads all scopes (stdio)
    freshservice-mcp --scope tickets changes  # loads only tickets & changes
    freshservice-mcp --transport sse          # start as HTTP/SSE server
    FRESHSERVICE_SCOPES=tickets,changes freshservice-mcp  # env-var alternative
    MCP_TRANSPORT=sse MCP_PORT=8000 freshservice-mcp      # HTTP server via env

Auth modes:
    - stdio / local dev:  FRESHSERVICE_APIKEY (Basic Auth)
    - HTTP behind gateway: per-user Bearer token forwarded by ContextForge
      (auto-detected from Authorization header; falls back to API key)
"""

import argparse
import logging
import os
import sys

import anyio
from mcp.server.fastmcp import FastMCP

from .auth import ForwardedAuthMiddleware
from .discovery import register_discovery_tools
from .telemetry import init_telemetry, metrics_response, instrument_tool
from .tools import SCOPE_REGISTRY


# ── logging ────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


VALID_TRANSPORTS = ("stdio", "sse", "streamable-http")


# ── MCP instance ───────────────────────────────────────────────────────────
# Lazily created in main() so we can pass stateless_http=True when using
# streamable-http transport (enables true stateless HA with multiple replicas).
mcp: FastMCP | None = None


# ── scope resolution ──────────────────────────────────────────────────────
def _resolve_scopes(cli_scopes: list[str] | None) -> list[str]:
    """Return the list of scope names to load.

    Priority: CLI args > FRESHSERVICE_SCOPES env-var > all.
    """
    if cli_scopes:
        scopes = cli_scopes
    else:
        env = os.getenv("FRESHSERVICE_SCOPES", "").strip()
        scopes = [s.strip() for s in env.split(",") if s.strip()] if env else list(SCOPE_REGISTRY)

    invalid = [s for s in scopes if s not in SCOPE_REGISTRY]
    if invalid:
        log.error(
            "Unknown scope(s): %s — valid scopes: %s",
            ", ".join(invalid),
            ", ".join(SCOPE_REGISTRY),
        )
        sys.exit(1)
    return scopes


def _resolve_transport(cli_transport: str | None) -> str:
    """Return the transport to use.  CLI > MCP_TRANSPORT env > stdio."""
    transport = cli_transport or os.getenv("MCP_TRANSPORT", "stdio").strip()
    if transport not in VALID_TRANSPORTS:
        log.error("Invalid transport %r — valid: %s", transport, ", ".join(VALID_TRANSPORTS))
        sys.exit(1)
    return transport


# ── main ───────────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Freshservice MCP Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"Available scopes: {', '.join(SCOPE_REGISTRY)}",
    )
    parser.add_argument(
        "--scope",
        nargs="*",
        metavar="SCOPE",
        help="Load only these tool scopes (default: all). "
        "Can also be set via FRESHSERVICE_SCOPES env-var (comma-separated).",
    )
    parser.add_argument(
        "--transport",
        choices=VALID_TRANSPORTS,
        default=None,
        help="MCP transport (default: stdio). "
        "Can also be set via MCP_TRANSPORT env-var.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Port for HTTP transports (default: 8000). "
        "Can also be set via MCP_PORT env-var.",
    )
    parser.add_argument(
        "--host",
        default=None,
        help="Host to bind for HTTP transports (default: 0.0.0.0). "
        "Can also be set via MCP_HOST env-var.",
    )

    args, _unknown = parser.parse_known_args()
    scopes = _resolve_scopes(args.scope)
    transport = _resolve_transport(args.transport)

    # Create MCP instance — enable stateless mode for streamable-http
    # so that no server-side session state is kept in memory.  This makes
    # horizontal scaling (multiple replicas) work without sticky sessions.
    global mcp

    # Build transport security settings: the MCP SDK (>=1.8) validates
    # Host and Origin headers to prevent DNS-rebinding attacks.  In K8s
    # behind a reverse proxy the Host is the external FQDN, so we must
    # allowlist it.  When MCP_ALLOWED_HOSTS is unset we disable the
    # protection entirely (safe when Traefik is the only entry-point).
    from mcp.server.fastmcp.server import TransportSecuritySettings

    allowed_hosts_env = os.getenv("MCP_ALLOWED_HOSTS", "").strip()
    if allowed_hosts_env:
        allowed_hosts = [h.strip() for h in allowed_hosts_env.split(",")]
        allowed_origins = [f"https://{h}" for h in allowed_hosts] + [f"http://{h}" for h in allowed_hosts]
        security = TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=allowed_hosts,
            allowed_origins=allowed_origins,
        )
    else:
        # Behind a reverse proxy — disable host validation
        security = TransportSecuritySettings(
            enable_dns_rebinding_protection=False,
        )

    mcp = FastMCP(
        "freshservice_mcp",
        stateless_http=(transport == "streamable-http"),
        transport_security=security,
    )

    # Always register discovery tools (2 lightweight tools)
    register_discovery_tools(mcp)
    log.info("Registered discovery tools (discover_form_fields, clear_field_cache)")

    # Register requested scopes
    for scope in scopes:
        SCOPE_REGISTRY[scope](mcp)
        log.info("Registered scope: %s", scope)

    # Wrap all registered tool handlers with observability instrumentation
    if hasattr(mcp, "_tool_manager"):
        for name, tool in mcp._tool_manager._tools.items():
            if hasattr(tool, "fn") and callable(tool.fn):
                tool.fn = instrument_tool(tool.fn)

    total = len(mcp._tool_manager._tools) if hasattr(mcp, "_tool_manager") else "?"
    log.info("Freshservice MCP server starting — %s tools loaded (scopes: %s)", total, ", ".join(scopes))

    # Initialise telemetry (metrics + optional OTel tracing)
    from importlib.metadata import version as pkg_version
    try:
        ver = pkg_version("freshservice-mcp")
    except Exception:
        ver = "dev"
    init_telemetry(version=ver, transport=transport)

    if transport == "stdio":
        mcp.run(transport="stdio")
    else:
        host = args.host or os.getenv("MCP_HOST", "0.0.0.0")
        port = args.port or int(os.getenv("MCP_PORT", "8000"))
        log.info("Listening on %s:%d (%s)", host, port, transport)

        # Build the Starlette app and wrap it with ForwardedAuthMiddleware
        # so that per-user Bearer tokens from the gateway are available
        # to http_client.py via contextvars.
        if transport == "sse":
            starlette_app = mcp.sse_app()
        else:
            starlette_app = mcp.streamable_http_app()

        # Add a lightweight health endpoint for K8s probes
        from starlette.responses import PlainTextResponse, Response
        from starlette.routing import Route

        async def healthz(request):
            return PlainTextResponse("ok")

        async def metrics(request):
            return Response(
                content=metrics_response(),
                media_type="text/plain; version=0.0.4; charset=utf-8",
            )

        from starlette.applications import Starlette
        from starlette.routing import Mount

        # For streamable-http, the session manager must be started via its
        # run() async context manager.  Wire it into Starlette's lifespan.
        import contextlib
        from collections.abc import AsyncIterator

        @contextlib.asynccontextmanager
        async def lifespan(app: Starlette) -> AsyncIterator[None]:
            if transport == "streamable-http" and mcp._session_manager is not None:
                async with mcp._session_manager.run():
                    yield
            else:
                yield

        health_app = Starlette(
            routes=[
                Route("/healthz", healthz),
                Route("/metrics", metrics),
                Mount("/", app=starlette_app),
            ],
            lifespan=lifespan,
        )

        health_app = ForwardedAuthMiddleware(health_app)

        mcp.settings.host = host
        mcp.settings.port = port

        import uvicorn
        config = uvicorn.Config(
            health_app,
            host=host,
            port=port,
            log_level=mcp.settings.log_level.lower(),
        )
        server = uvicorn.Server(config)
        anyio.run(server.serve)


if __name__ == "__main__":
    main()
