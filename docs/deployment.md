# Deployment

## Running Locally

### stdio (default)

For local development with Claude Desktop or VS Code Copilot:

```bash
FRESHSERVICE_APIKEY=<key> FRESHSERVICE_DOMAIN=<domain> freshservice-mcp
```

Or with Python directly:

```bash
FRESHSERVICE_APIKEY=<key> FRESHSERVICE_DOMAIN=<domain> python3 -m freshservice_mcp.server
```

### SSE / HTTP

For running as an HTTP server (behind a gateway or standalone):

```bash
FRESHSERVICE_DOMAIN=<domain> MCP_TRANSPORT=sse python3 -m freshservice_mcp.server
```

## Client Configuration

### Claude Desktop

Add to your `claude_desktop_config.json`:

```json
"mcpServers": {
  "freshservice-mcp": {
    "command": "uvx",
    "args": ["freshservice-mcp"],
    "env": {
      "FRESHSERVICE_APIKEY": "<YOUR_API_KEY>",
      "FRESHSERVICE_DOMAIN": "yourcompany.freshservice.com"
    }
  }
}
```

### VS Code (Copilot)

Add to `.vscode/mcp.json` in your workspace:

```json
{
  "servers": {
    "freshservice": {
      "type": "stdio",
      "command": "python3",
      "args": ["-m", "freshservice_mcp.server"],
      "env": {
        "PYTHONPATH": "/path/to/freshservice_mcp/src",
        "FRESHSERVICE_APIKEY": "<YOUR_API_KEY>",
        "FRESHSERVICE_DOMAIN": "yourcompany.freshservice.com"
      }
    }
  }
}
```

**WSL users** — use `wsl` as the command:

```json
{
  "servers": {
    "freshservice": {
      "type": "stdio",
      "command": "wsl",
      "args": [
        "-e", "env",
        "FRESHSERVICE_APIKEY=<YOUR_API_KEY>",
        "FRESHSERVICE_DOMAIN=yourcompany.freshservice.com",
        "PYTHONPATH=/path/to/freshservice_mcp/src",
        "python3", "-m", "freshservice_mcp.server"
      ]
    }
  }
}
```

### Smithery

```bash
npx -y @smithery/cli install @effytech/freshservice_mcp --client claude
```

## Docker

The server is published as a container image on GitHub Container Registry.

```bash
docker run -p 8000:8000 \
  -e FRESHSERVICE_DOMAIN=yourcompany.freshservice.com \
  -e MCP_TRANSPORT=sse \
  -e MCP_PORT=8000 \
  ghcr.io/forterro/freshservice_mcp:0.2.0
```

In gateway mode (OAuth2), no `FRESHSERVICE_APIKEY` is needed — the gateway forwards per-user tokens.

## Helm Chart

A Helm chart is published to `oci://ghcr.io/forterro/charts/freshservice-mcp`.

### Quick Install (gateway mode — OAuth2)

No API key needed — the gateway handles authentication:

```bash
helm install freshservice-mcp oci://ghcr.io/forterro/charts/freshservice-mcp \
  --version 0.2.0 \
  --set config.FRESHSERVICE_DOMAIN=yourcompany.freshservice.com
```

### Install with API Key (standalone)

```bash
helm install freshservice-mcp oci://ghcr.io/forterro/charts/freshservice-mcp \
  --version 0.2.0 \
  --set config.FRESHSERVICE_DOMAIN=yourcompany.freshservice.com \
  --set secret.FRESHSERVICE_APIKEY=your-api-key
```

### Install with Existing Secret

```bash
helm install freshservice-mcp oci://ghcr.io/forterro/charts/freshservice-mcp \
  --version 0.2.0 \
  --set config.FRESHSERVICE_DOMAIN=yourcompany.freshservice.com \
  --set existingSecret=my-freshservice-secret
```

### Values Reference

| Key | Default | Description |
|-----|---------|-------------|
| `replicaCount` | `1` | Number of pod replicas |
| `image.repository` | `ghcr.io/forterro/freshservice_mcp` | Container image repository |
| `image.tag` | `""` (appVersion) | Image tag override |
| `config.MCP_TRANSPORT` | `sse` | Transport: `sse` or `streamable-http` |
| `config.MCP_HOST` | `0.0.0.0` | Bind address |
| `config.MCP_PORT` | `8000` | Bind port |
| `config.FRESHSERVICE_DOMAIN` | `""` | **Required.** Your Freshservice domain |
| `config.FRESHSERVICE_SCOPES` | `""` (all) | Comma-separated scopes to load |
| `secret.FRESHSERVICE_APIKEY` | `""` | API key (standalone mode only) |
| `existingSecret` | `""` | Use an existing K8s Secret |
| `service.type` | `ClusterIP` | Service type |
| `service.port` | `8000` | Service port |
| `resources.requests.cpu` | `50m` | CPU request |
| `resources.requests.memory` | `128Mi` | Memory request |
| `resources.limits.cpu` | `500m` | CPU limit |
| `resources.limits.memory` | `256Mi` | Memory limit |
| `extraEnv` | `[]` | Extra env vars (`[{name, value}]`) |
| `extraEnvFrom` | `[]` | Extra envFrom (`[{secretRef: {name}}]`) |
| `probes.liveness.enabled` | `true` | Enable liveness probe on `/healthz` |
| `probes.readiness.enabled` | `true` | Enable readiness probe on `/healthz` |

## Configuration Options

### Scope Selection

By default all 13 scopes are loaded (34 scoped tools + 2 discovery = 36 tools). To load only specific scopes:

**Via environment variable:**

```bash
FRESHSERVICE_SCOPES=tickets,changes,status_page freshservice-mcp
```

**Via CLI argument:**

```bash
freshservice-mcp --scope tickets changes problems
```

This is useful when you have many MCP servers and need to stay under client tool limits (e.g. VS Code Copilot's 128-tool cap).

### Transport Selection

| Transport | Use case | Command |
|-----------|----------|---------|
| `stdio` (default) | Local dev with Claude Desktop / VS Code | `freshservice-mcp` |
| `sse` | HTTP server behind MCP gateway | `MCP_TRANSPORT=sse freshservice-mcp` |
| `streamable-http` | HTTP server with streamable responses | `MCP_TRANSPORT=streamable-http freshservice-mcp` |

HTTP transports also accept `MCP_HOST` (default `0.0.0.0`) and `MCP_PORT` (default `8000`).

### Health Check

HTTP transports expose a `GET /healthz` endpoint that returns `200 ok`. Use this for Kubernetes liveness/readiness probes.

## Testing

```bash
# stdio mode (API key)
FRESHSERVICE_APIKEY=<key> FRESHSERVICE_DOMAIN=<domain> python3 -m freshservice_mcp.server

# SSE mode (for gateway testing)
FRESHSERVICE_DOMAIN=<domain> MCP_TRANSPORT=sse python3 -m freshservice_mcp.server
```

Or with uvx:

```bash
uvx freshservice-mcp --env FRESHSERVICE_APIKEY=<key> --env FRESHSERVICE_DOMAIN=<domain>
```

## Troubleshooting

- Verify your Freshservice domain is correct (`yourcompany.freshservice.com`)
- **API key mode**: verify `FRESHSERVICE_APIKEY` is set and valid
- **OAuth2 mode**: verify the gateway is forwarding the `Authorization: Bearer <token>` header — see [Authentication](authentication.md)
- Ensure proper network connectivity to Freshservice servers
- Check API rate limits and quotas
- If tools appear "disabled" in VS Code Copilot, you may have exceeded the 128-tool limit across all MCP servers — use `FRESHSERVICE_SCOPES` to load fewer scopes
- Check server logs: the server logs which scopes and how many tools were loaded at startup
- Use `get_me` to verify authentication — it returns the current user's agent profile
