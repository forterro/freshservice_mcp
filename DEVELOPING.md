# Developing

Local development guide for the Freshservice MCP Server.

## Prerequisites

- Python 3.13+ (3.10 minimum)
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- Docker (optional — for building images)

## Quick Start

### 1. Install Dependencies

```bash
uv sync --extra redis --extra observability
```

Or with pip:

```bash
pip install -e ".[redis,observability]"
```

### 2. Configure Environment

Create a `.env` file (or export variables):

```bash
# Required
FRESHSERVICE_DOMAIN=helpdesk-forterro.freshservice.com
FRESHSERVICE_APIKEY=your-api-key

# Optional — Redis cache
REDIS_URL=redis://localhost:6379/0

# Optional — tracing
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
OTEL_SERVICE_NAME=freshservice-mcp
```

### 3. Run the Server

**stdio** (local dev with Claude Desktop / VS Code):

```bash
freshservice-mcp
```

**SSE** (HTTP server — legacy):

```bash
freshservice-mcp --transport sse --port 8000
```

**streamable-http** (HTTP server — stateless, HA-ready):

```bash
freshservice-mcp --transport streamable-http --port 8000
```

Environment variable alternatives:

```bash
MCP_TRANSPORT=streamable-http MCP_PORT=8000 freshservice-mcp
```

### 4. Verify

```bash
# Health check
curl http://localhost:8000/healthz

# Metrics (Prometheus)
curl http://localhost:8000/metrics

# MCP endpoint (streamable-http)
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}'
```

## Scope Selection

Load only specific tool scopes to reduce startup time and attack surface:

```bash
# CLI
freshservice-mcp --scope tickets changes

# Environment variable
FRESHSERVICE_SCOPES=tickets,changes freshservice-mcp
```

Available scopes: `tickets`, `changes`, `assets`, `agents`, `requesters`,
`solutions`, `products`, `problems`, `releases`, `departments`, `projects`,
`status_page`, `misc`.

## Running Tests

```bash
PYTHONPATH=src python -m pytest tests/ -v
```

## Docker

### Build

```bash
docker build -t freshservice-mcp:dev .
```

### Run

```bash
docker run -p 8000:8000 \
  -e FRESHSERVICE_DOMAIN=helpdesk-forterro.freshservice.com \
  -e FRESHSERVICE_APIKEY=your-key \
  freshservice-mcp:dev
```

## Helm Chart

The chart lives in `chart/`. To test locally:

```bash
helm template test chart/ \
  --set config.FRESHSERVICE_DOMAIN=helpdesk-forterro.freshservice.com \
  --set secret.FRESHSERVICE_APIKEY=test
```

## Transport Comparison

| Transport | Endpoint | State | HA Scaling | Use Case |
| --- | --- | --- | --- | --- |
| `stdio` | stdin/stdout | N/A | N/A | Local dev, Claude Desktop |
| `sse` | `GET /sse`, `POST /messages/` | Server-side sessions | Requires sticky sessions | Legacy HTTP |
| `streamable-http` | `POST /mcp` | **Stateless** | Free scaling, no affinity | Production (recommended) |

## Project Structure

```text
src/freshservice_mcp/
├── server.py          # Entry point, FastMCP, transport setup
├── config.py          # Constants, enums (TicketStatus, ChangePriority…)
├── auth.py            # ForwardedAuthMiddleware (OAuth2/Basic extraction)
├── http_client.py     # Freshservice API client with per-user auth
├── cache.py           # Tiered cache (Redis + in-memory fallback)
├── discovery.py       # Dynamic form field discovery
├── telemetry.py       # Prometheus metrics + OpenTelemetry tracing
└── tools/
    ├── __init__.py    # SCOPE_REGISTRY mapping
    ├── tickets.py     # manage_ticket, manage_ticket_conversation, …
    ├── changes.py     # manage_change, manage_change_note, …
    ├── assets.py      # manage_asset, manage_asset_relationship, …
    ├── agents.py      # get_me, manage_agent, manage_agent_group
    ├── requesters.py  # manage_requester, manage_requester_group
    ├── problems.py    # manage_problem, manage_problem_note, …
    ├── releases.py    # manage_release, manage_release_note, …
    ├── solutions.py   # manage_solution_category, manage_solution_article
    ├── products.py    # manage_product
    ├── departments.py # manage_department, manage_location
    ├── projects.py    # manage_project, manage_project_task, …
    ├── status_page.py # manage_status_page, manage_maintenance_window
    └── misc.py        # manage_business_hours, manage_sla_policy

chart/                 # Helm chart (published to ghcr.io/forterro/charts)
tests/                 # pytest test suite
docs/                  # Extended documentation
grafana/               # Dashboard JSON sources
```
