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

Before configuring the gateway, you must register OAuth2 credentials in the
**Freshworks Developer Portal** (not in the Freshservice admin panel).

#### Step 1 — Discover the OAuth2 Endpoints

Freshservice exposes a standard OAuth Authorization Server metadata endpoint.
Query it to get the correct URLs for your account:

```bash
curl -s https://YOUR-DOMAIN.freshservice.com/.well-known/oauth-authorization-server | python3 -m json.tool
```

This returns a JSON document like:

```json
{
  "issuer": "https://YOUR-ORG.myfreshworks.com",
  "authorization_endpoint": "https://YOUR-ORG.myfreshworks.com/org/oauth/v2/authorize",
  "token_endpoint": "https://YOUR-ORG.myfreshworks.com/org/oauth/v2/token",
  "registration_endpoint": "https://YOUR-ORG.myfreshworks.com/developer/oauth/product/.../register",
  "response_types_supported": ["code"],
  "grant_types_supported": ["authorization_code", "refresh_token"],
  "token_endpoint_auth_methods_supported": ["none", "client_secret_basic"],
  "code_challenge_methods_supported": ["plain", "S256"],
  "scopes_supported": [
    "freshservice.tickets.create",
    "freshservice.tickets.view",
    "freshservice.assets.view",
    "freshservice.assets.manage",
    "..."
  ]
}
```

> **Critical**: The endpoints are on the **Freshworks organization domain**
> (`YOUR-ORG.myfreshworks.com`), NOT on the Freshservice product domain
> (`YOUR-DOMAIN.freshservice.com`). The product domain only serves the
> `.well-known` metadata and the legacy `/api/v2/oauth/token` endpoint.

Key takeaways from the metadata:

| Field | Value |
|-------|-------|
| Authorization endpoint | `https://YOUR-ORG.myfreshworks.com/org/oauth/v2/authorize` |
| Token endpoint | `https://YOUR-ORG.myfreshworks.com/org/oauth/v2/token` |
| Auth method | `client_secret_basic` (credentials in Authorization header) |
| PKCE | Supported (`S256` and `plain`) |
| Scopes | Granular per-resource (see `scopes_supported`) |

#### Step 2 — Register OAuth2 Credentials

1. Go to the [Freshworks Developer Portal](https://developers.freshworks.com/login/)
2. Enter your **organization URL** (e.g. `YOUR-ORG.myfreshworks.com`) and click **Proceed**
3. Click the **Settings** icon (gear) in the top navigation bar
4. In the **OAuth Credentials** section, click **Create OAuth Credentials**
5. Fill in:
   - **Name**: a descriptive name (e.g. `ContextForge MCP Gateway`)
   - **Description**: brief description of the integration
   - **Redirect URL**: the OAuth2 callback URL of your MCP gateway
     (e.g. `https://your-contextforge.example.com/oauth/callback`)
   - **Add scopes**: select the Freshservice resources and permissions your
     integration needs (e.g. `freshservice.tickets.view`,
     `freshservice.assets.view`, etc.)
6. Click **Create Credentials**
7. Copy the **Client ID** (format: `fw_ext_...`) and **Client Secret**

> **Important — scope limitations:**
>
> The Freshworks Developer Portal has an **undocumented limit on the number
> of scopes** that can be associated with a single OAuth credential. If you
> select too many scopes, the portal silently fails with:
>
> > *"An error occurred when updating OAuth credential, please retry later"*
>
> This is a Freshworks platform bug, not a ContextForge issue. Workarounds:
>
> - **Add scopes incrementally** — save after adding a few at a time
> - **Prioritize essential scopes** — tickets, assets, changes, problems,
>   agents, solutions cover 90% of use cases
> - Some Freshservice API endpoints (releases, canned responses,
>   maintenance windows, workspaces, change approvals) may not have
>   corresponding OAuth scopes available at all and will return 403
>   regardless of configuration

> **Important — common mistakes to avoid:**
>
> - Do **NOT** create the app in the Freshservice admin panel
>   (`Admin → Security`) — that section does not have OAuth Applications.
> - Do **NOT** use the Freshworks Developer Portal "Apps" section
>   (Freshworks/Custom/External apps) — those are for marketplace apps built
>   with the FDK, not for external OAuth integrations.
> - The OAuth credentials are created under your **profile settings** in
>   the Developer Portal only.

#### Step 3 — Configure the MCP Gateway

Configure your MCP gateway with the OAuth2 credentials. The authorization and
token URLs come from the `.well-known` metadata discovered in Step 1.

Example for ContextForge:

```json
{
  "grant_type": "authorization_code",
  "authorization_url": "https://YOUR-ORG.myfreshworks.com/org/oauth/v2/authorize",
  "token_url": "https://YOUR-ORG.myfreshworks.com/org/oauth/v2/token",
  "redirect_uri": "https://your-contextforge.example.com/oauth/callback",
  "client_id": "fw_ext_...",
  "client_secret": "...",
  "token_endpoint_auth_method": "client_secret_basic",
  "scopes": [],
  "omit_resource": true
}
```

> **Gateway-specific flags:**
>
> - `omit_resource: true` — Freshworks does not support the RFC 8707
>   `resource` parameter. If your gateway sends it, Freshworks will reject
>   the request with `invalid_id`.
> - `token_endpoint_auth_method: client_secret_basic` — must match the
>   `token_endpoint_auth_methods_supported` from the metadata. Using
>   `client_secret_post` may crash the HTTP/2 stream on Freshworks.

#### Step 4 — Verify

Use the `get_me` tool to verify authentication is working:

```text
Tool: get_me
→ Returns: { "agent": { "email": "you@company.com", ... }, "source": "oauth_jwt" }
```

If the source is `oauth_jwt`, per-user OAuth2 is active.

### Troubleshooting OAuth2

| Symptom | Cause | Fix |
|---------|-------|-----|
| `invalid_client` / `client does not exist` | Wrong authorize/token URL | Use the URLs from `.well-known/oauth-authorization-server` — they are on `YOUR-ORG.myfreshworks.com/org/oauth/v2/...`, NOT `/oauth/authorize` |
| `invalid_id` / `invalid identifier value` | Gateway sends unsupported params (`resource`, `code_challenge` with wrong config) | Set `omit_resource: true`; verify PKCE is using S256 if enabled |
| HTTP/2 stream crash on token exchange | Using `client_secret_post` | Switch to `client_secret_basic` |
| 404 on `/authorize` or `/oauth/authorize` | Wrong URL path | The correct path is `/org/oauth/v2/authorize` |
| Freshworks login page shows "page not found" | Wrong authorize URL variant | Use exactly the URL from `.well-known` metadata |
| Token endpoint returns empty body | Wrong `Content-Type` | Token endpoint expects `application/json`, not `application/x-www-form-urlencoded` |
| 403 on some API endpoints (releases, canned responses, etc.) | OAuth scope not available or not selected | Some endpoints have no OAuth scope; add scopes incrementally to avoid the portal bug |
| "An error occurred when updating OAuth credential" in Developer Portal | Too many scopes selected at once | Add scopes in smaller batches and save between each batch |

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
