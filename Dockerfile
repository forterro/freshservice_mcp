# ---------------------------------------------------------------------------
# Freshservice MCP Server — Production Dockerfile
# Multi-stage build using uv for fast, reproducible installs.
# ---------------------------------------------------------------------------

# ── Stage 1: build ─────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Install dependencies first (layer cache)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Install the project itself
COPY src ./src
RUN uv sync --frozen --no-dev


# ── Stage 2: runtime ──────────────────────────────────────────────────────
FROM python:3.12-slim

WORKDIR /app

# Copy the virtual-env from builder
COPY --from=builder /app/.venv /app/.venv

# Ensure the venv is on PATH
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

# Default: SSE transport on port 8000 (override via MCP_TRANSPORT, MCP_PORT)
ENV MCP_TRANSPORT=sse \
    MCP_HOST=0.0.0.0 \
    MCP_PORT=8000

EXPOSE 8000

# Run as non-root
RUN useradd --create-home --shell /bin/bash mcp
USER mcp

ENTRYPOINT ["freshservice-mcp"]
