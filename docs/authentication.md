# Authentication

The Freshservice MCP server supports two authentication modes, selected **automatically per-request**.

| Mode | When | How |
|------|------|-----|
| **OAuth2 per-user** | Running behind an MCP gateway (e.g. ContextForge) via SSE/HTTP | The gateway forwards the user's Bearer token in the `Authorization` header. The server extracts it via ASGI middleware and uses it for all Freshservice API calls. Each user authenticates with their own Freshservice identity. |
| **API key** | Local development via stdio, or standalone deployment | Uses `FRESHSERVICE_APIKEY` env var with Basic Auth. All requests share the same identity. |

**Detection logic**: if an incoming HTTP request carries `Authorization: Bearer <token>`, OAuth2 mode is used for that request. Otherwise, the server falls back to the API key.

## API Key Authentication

The simplest mode — suitable for local development and single-user deployments.

1. In Freshservice, go to **Profile Settings → API Settings**
2. Copy your API key
3. Set the env var: `FRESHSERVICE_APIKEY=your-api-key`

All API calls use Basic Auth with this key. The identity is always the key owner.

## OAuth2 Authentication (via MCP Gateway)

In this mode, an MCP gateway (such as [ContextForge](https://github.com/IBM/mcp-context-forge)) sits in front of the server and handles the full OAuth2 authorization code flow with Freshservice. The server itself needs **no OAuth2 credentials** — it simply receives and forwards the per-user Bearer tokens.

**Architecture:**

```
User → MCP Gateway (OAuth2 flow) → freshservice-mcp (Bearer token forwarding) → Freshservice API
```

**Benefits:**

- Each user authenticates with their own Freshservice identity
- No shared API key — audit trail per user
- Token lifecycle (refresh, revocation) handled by the gateway
- The server is stateless — no token storage

### Creating a Freshservice OAuth2 Application

Before configuring the gateway, you must register an OAuth2 application in Freshservice.

#### Step 1 — Register the Application

1. Log in to Freshservice as an administrator
2. Navigate to **Admin → Security → OAuth Applications** (or go to `https://yourcompany.freshservice.com/admin/oauth_applications`)
3. Click **New Application**
4. Fill in:
   - **Application Name**: a descriptive name (e.g. `MCP Gateway - ContextForge`)
   - **Description**: optional
   - **Redirect URI**: the OAuth2 callback URL of your MCP gateway (e.g. `https://contextforge.dev.c1p.frtapps.com/oauth/callback/freshservice`)
5. Click **Save**
6. Copy the **Client ID** and **Client Secret** — you will need them for the gateway configuration

#### Step 2 — Note the OAuth2 Endpoints

Freshservice OAuth2 endpoints follow this pattern:

| Endpoint | URL |
|----------|-----|
| Authorization | `https://yourcompany.freshservice.com/authorize` |
| Token | `https://yourcompany.freshservice.com/api/v2/oauth/token` |

> **Important**: The token endpoint uses `client_secret_basic` authentication method (credentials in the `Authorization` header, not in the POST body). Make sure your gateway is configured accordingly.

#### Step 3 — Configure the MCP Gateway

Configure your MCP gateway with the OAuth2 credentials. Example for ContextForge:

```yaml
# Gateway configuration for Freshservice OAuth2
oauth:
  authorization_url: https://yourcompany.freshservice.com/authorize
  token_url: https://yourcompany.freshservice.com/api/v2/oauth/token
  client_id: "<from step 1>"
  client_secret: "<from step 1>"
  token_endpoint_auth_method: client_secret_basic
  scopes: []  # Freshservice does not use granular OAuth scopes
```

#### Step 4 — Verify

Use the `get_me` tool to verify authentication is working:

```
Tool: get_me
→ Returns: { "agent": { "email": "you@company.com", ... }, "source": "oauth_jwt" }
```

If the source is `oauth_jwt`, per-user OAuth2 is active.

### OAuth2 JWT Token Structure

For reference, Freshservice OAuth2 tokens are JWTs with these claims:

| Claim | Description |
|-------|-------------|
| `sub` | Numeric user ID (not email) |
| `user` | **User's email address** (primary identifier) |
| `iss` | Issuer (Freshservice) |
| `aud` | Audience |
| `organisation_id` | Freshservice organization ID |
| `organisation_domain` | e.g. `yourcompany.freshservice.com` |
| `scope` | Array of granted scopes (e.g. `freshservice.*`) |
| `bundle_id` | Freshworks bundle ID |
| `app_id` | OAuth application ID |
| `ext_oauth` | External OAuth flag |

> The `get_me` tool extracts the email from claims in this priority order: `user` → `email` → `unique_name` → `preferred_username`.

## Future: Direct OAuth2 (without Gateway)

> **Status: Not yet implemented** — contributions welcome.

Currently, OAuth2 only works via token forwarding from a gateway. A future enhancement could add native OAuth2 support directly in the server (client credentials flow or authorization code flow with built-in token management). This would require:

- New env vars: `FRESHSERVICE_OAUTH_CLIENT_ID`, `FRESHSERVICE_OAUTH_CLIENT_SECRET`
- Token refresh logic in `http_client.py`
- Optional token storage (in-memory or persistent)

For now, if you need OAuth2 without a gateway, you can obtain tokens externally and inject them via the `Authorization: Bearer <token>` header on each request to the SSE/HTTP transport.
