<!-- markdownlint-disable MD024 -->
# Changelog

All notable changes to freshservice-mcp are documented in this file.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning follows git tags — the CI pipeline sets chart and image versions from tags.

## [0.5.3] - 2026-04-20

### Fixed

- **StreamableHTTP session manager initialization**: the `StreamableHTTPSessionManager` requires its `run()` async context manager to create a task group before handling requests. Added a Starlette lifespan hook that calls `session_manager.run()` at startup — fixes `RuntimeError: Task group is not initialized`

## [0.5.2] - 2026-04-20

### Fixed

- **Project task update endpoint**: use singular `/tasks/{id}` endpoint instead of plural `/tasks/` for PM task updates

## [0.5.1] - 2026-04-20

### Fixed

- **MCP SDK version**: bump `mcp[cli]` from `>=1.3.0` to `>=1.8.0` in pyproject.toml and regenerate uv.lock (1.6.0 → 1.27.0). The previous lockfile pinned a version that predates `FastMCP.streamable_http_app()`
- **Dockerfile default transport**: change from `sse` to `streamable-http`

## [0.5.0] - 2026-04-20

### Changed

- **BREAKING: Default transport switched from SSE to streamable-http**. Clients must support MCP streamable-http transport. SSE remains available via `MCP_TRANSPORT=sse` override
- **Stateless HTTP mode**: `FastMCP` is now created with `stateless_http=True` when using streamable-http transport — eliminates server-side session state, enabling horizontal scaling without sticky sessions

### Added

- **PodDisruptionBudget template** in Helm chart (`pdb.yaml`)
- **`podDisruptionBudget` config section** in chart values.yaml

## [0.4.6] - 2026-04-03

### Added

- **Basic Auth forwarding**: support `Authorization: Basic` headers forwarded from MCP gateway (ContextForge), enabling API key auth passthrough alongside OAuth2 Bearer tokens

## [0.4.5] - 2026-04-01

### Fixed

- **PM task update endpoint**: use plural `/tasks/` endpoint for project management task updates

## [0.4.4] - 2026-04-01

### Fixed

- **Dashboard spanNulls**: enable `spanNulls` on all timeseries panels to bridge gaps in sparse metrics

## [0.4.3] - 2026-03-31

### Added

- **Tracing panels in Grafana dashboard**: Tempo span metrics, service dependency map, request rate/error/duration panels from traces
- **Service dependency visualization**: automatic upstream/downstream service detection from span data

## [0.4.2] - 2026-03-31

### Added

- **Grafana dashboard ConfigMap**: auto-discovered by Grafana sidecar via `grafana_dashboard` label

## [0.4.1] - 2026-03-31

### Fixed

- **CI image tag**: auto-set `image.tag` in chart `values.yaml` during the build pipeline to match the git tag

## [0.4.0] - 2026-03-31

### Added

- **Prometheus metrics**: request counters, duration histograms, error rates — exposed on `/metrics`
- **OpenTelemetry tracing**: distributed traces with span-per-tool instrumentation, OTLP gRPC export
- **Grafana dashboard**: pre-built JSON dashboard with request rate, latency percentiles, error breakdown, and tool usage panels
- **ServiceMonitor template**: for Prometheus Operator / Alloy auto-discovery

## [0.3.1] - 2026-03-31

### Fixed

- **Redis password from external Secret**: support `externalRedis.passwordSecret` to inject Redis password from a Kubernetes Secret (used with KubeBlocks-managed Redis)

## [0.3.0] - 2026-03-31

### Added

- **Tiered Redis read cache**: two-tier caching strategy to reduce Freshservice API calls and avoid rate limits
  - **Reference tier** (agents, departments, groups): shared keys `fs:ref:{path}:{hash}`, TTL 12h
  - **Operational tier** (tickets, changes, assets): per-user keys `fs:op:{userId}:{path}:{hash}`, TTL 5min
- **Graceful fallback**: Redis errors fall back to in-memory TTL cache transparently
- **Helm values**: `externalRedis.enabled`, `externalRedis.url`, `externalRedis.existingSecret`, `cache.ttlReference`, `cache.ttlOperational`

## [0.2.0] - 2026-03-26

### Added

- **Per-user OAuth2 token forwarding**: ASGI middleware extracts `Authorization: Bearer` header and makes it available to HTTP client via `contextvars`. Enables per-user Freshservice API calls when running behind an MCP gateway (ContextForge)
- **`get_me` tool**: returns the authenticated user's identity by decoding the forwarded OAuth JWT
- **Docker image**: multi-stage build with `python:3.13-alpine`, non-root user, `uv` for reproducible installs
- **Helm chart**: Kubernetes deployment with `ConfigMap`, `Secret`, `Service`, health probes, `ServiceMonitor`
- **GitHub Actions CI**: build and publish Docker image + Helm chart (OCI) to `ghcr.io/forterro` on tag push

## [0.1.0] - 2026-02-16

### Added

- **Initial modular architecture**: 36 tools organized into 13 independently loadable scopes
- **Scopes**: tickets, changes, problems, releases, assets, agents, requesters, solutions, products, departments, projects, status\_page, misc
- **Dynamic form discovery**: `discover_form_fields` and `clear_field_cache` tools for runtime field introspection
- **Multiple transports**: stdio (local development), SSE (HTTP server)
- **Project Management**: NewGen API support for projects, tasks, and time entries
- **Status Page**: full CRUD for status pages, maintenance windows, and incidents with auto-association
- **Assets/CMDB**: asset management with relationship handling and auto-fill for primary\_id/primary\_type
