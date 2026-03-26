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
"""

import argparse
import logging
import os
import sys

from mcp.server.fastmcp import FastMCP

from .discovery import register_discovery_tools
from .tools import SCOPE_REGISTRY


# ── logging ────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


VALID_TRANSPORTS = ("stdio", "sse", "streamable-http")


# ── MCP instance ───────────────────────────────────────────────────────────
mcp = FastMCP("freshservice_mcp")


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

    # Always register discovery tools (2 lightweight tools)
    register_discovery_tools(mcp)
    log.info("Registered discovery tools (discover_form_fields, clear_field_cache)")

    # Register requested scopes
    for scope in scopes:
        SCOPE_REGISTRY[scope](mcp)
        log.info("Registered scope: %s", scope)

    total = len(mcp._tool_manager._tools) if hasattr(mcp, "_tool_manager") else "?"
    log.info("Freshservice MCP server starting — %s tools loaded (scopes: %s)", total, ", ".join(scopes))

    if transport == "stdio":
        mcp.run(transport="stdio")
    else:
        host = args.host or os.getenv("MCP_HOST", "0.0.0.0")
        port = args.port or int(os.getenv("MCP_PORT", "8000"))
        log.info("Listening on %s:%d (%s)", host, port, transport)
        mcp.run(transport=transport, host=host, port=port)


if __name__ == "__main__":
    main()
