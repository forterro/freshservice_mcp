# Contributing

Guidelines for contributing to the Freshservice MCP Server.

## Language

- **Code, comments, commit messages, documentation, reviews**: English only.

## Development Workflow

### 1. Setup

See [DEVELOPING.md](DEVELOPING.md) for local environment setup, running
tests, and Docker usage.

### 2. Branch Strategy

All work happens on **topic branches** created from `main`:

```bash
git checkout main
git pull
git checkout -b feature/my-change
```

Branch naming:

- `feature/<description>` — New features
- `fix/<description>` — Bug fixes
- `refactor/<description>` — Code restructuring

### 3. Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```text
feat: add new tool for ticket categories
fix(changes): correct planning field serialization
feat(dashboard): add error rate panel
```

Scope is optional but encouraged when the change targets a specific module
(e.g., `tickets`, `changes`, `dashboard`, `ci`).

### 4. Tags and Releases

- **Tags are immutable** — never overwrite an existing tag.
- Tags follow semver: `v<major>.<minor>.<patch>` (e.g., `v0.5.3`).
- Pushing a `v*` tag triggers CI to build the Docker image and publish the
  Helm chart to `oci://ghcr.io/forterro/charts`.
- Update [CHANGELOG.md](CHANGELOG.md) before tagging a release.

### 5. Development Checklist

Before pushing, every change must satisfy:

- [ ] **Tests pass**: `PYTHONPATH=src python -m pytest tests/ -v`
- [ ] **No dead code**: remove unused imports and functions
- [ ] **CHANGELOG updated**: add an entry under `## [Unreleased]`
- [ ] **Documentation updated**: if behavior changed, update the relevant docs

### 6. Code Standards

#### Architecture

The codebase is organized by responsibility:

| Module | Responsibility |
| --- | --- |
| `server.py` | Entry point, FastMCP instance, transport setup |
| `config.py` | Configuration constants and enums |
| `auth.py` | ForwardedAuthMiddleware (OAuth2/Basic token extraction) |
| `http_client.py` | Freshservice API client with auth injection |
| `cache.py` | Tiered read cache (Redis + in-memory fallback) |
| `discovery.py` | Dynamic form field discovery with TTL cache |
| `telemetry.py` | Prometheus metrics + OpenTelemetry tracing setup |
| `tools/*.py` | Tool modules — one per Freshservice scope |

Rules:

- **No circular imports** — `config.py` and `telemetry.py` are leaf modules.
- **No dead code** — remove unused functions during review.
- **Factor shared logic** — if the same pattern appears twice, extract it.
- **External dependencies are mocked in tests**.

#### Tool Modules

Each scope module (e.g., `tools/tickets.py`) exposes a single
`register_<scope>_tools(mcp)` function that registers all tools for that
scope on the given `FastMCP` instance.

Tools follow a consistent pattern:

- Single `manage_*` tool per entity with an `action` parameter
  (`list`, `get`, `create`, `update`, `delete`)
- Sub-resources use separate tools (e.g., `manage_ticket_conversation`)
- All API calls go through `http_client.py` for auth injection
