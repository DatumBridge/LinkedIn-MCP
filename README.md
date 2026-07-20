# LinkedIn MCP Server

DatumBridge **tool-server** that exposes LinkedIn member profile and Share-on-LinkedIn capabilities over Streamable HTTP MCP. Sibling to `gmail-mcp` / `google-drive-mcp`.

**Class:** Python FastMCP tool-server (not a WS hub/relay). See [`docs/`](docs/README.md).

## Tools

| Area | Tools |
|------|--------|
| Profile | `get_me` |
| Posts | `create_post`, `create_image_post`, `get_post`, `delete_post` |

Every tool requires **`credentials_path`** or **`credentials_json`** (OAuth token from Connect with LinkedIn / `scripts/oauth_connect.py`).

Side-effect tools (`create_post`, `create_image_post`, `delete_post`) require **`confirm=true`**. Use **`dry_run=true`** on create tools to preview without publishing. Default visibility is **`CONNECTIONS`**.

**Production (DatumBridge Studio):** prefer the platform **credential vault** — connect LinkedIn under Studio integrations when available. The MCP registry injects `credentials_json` on execute; do not put tokens in workflow parameter mappings.

Registry id: **`mcpServer=linkedin`**.

**Company Page posting** is a separate server: [`../linkedin-corp-mcp/`](../linkedin-corp-mcp/) (`mcpServer=linkedin-corp`). Do not mix org scopes into this personal-account server.

## Setup

1. LinkedIn Developer Portal → create an app.
2. Add products: **Sign In with LinkedIn using OpenID Connect** and **Share on LinkedIn**.
3. Set `LINKEDIN_CLIENT_ID` / `LINKEDIN_CLIENT_SECRET` (or `credentials.json`).
4. Add redirect URI: `http://localhost:8000/oauth/callback` (or `OAUTH_REDIRECT_URI`).
5. Consent scopes use `openid profile email w_member_social`.

```bash
cp .env.example .env
python -m venv .venv && source .venv/bin/activate
pip install -r requirements_mcp.txt
chmod +x mcp_server_entrypoint.sh
./mcp_server_entrypoint.sh
# or: uvicorn app.mcp_server:http_app --host 0.0.0.0 --port 8000
```

- Health: `GET http://localhost:8000/health`
- MCP: `POST http://localhost:8000/mcp/`
- Test UI: `http://localhost:8000/test` (opt-in: `LINKEDIN_ENABLE_OAUTH_UI=1` + `OAUTH_REDIRECT_URI`)
- OAuth: `http://localhost:8000/oauth/start` (same opt-in)

Requires **Python 3.10+** for FastMCP (Docker image uses 3.11). Helper tests run without FastMCP:

```bash
python scripts/test_helpers.py -v
```

## Manual testing

Full guide: [`docs/operations/manual-testing.md`](docs/operations/manual-testing.md)

**Browser Test UI** (set `LINKEDIN_ENABLE_OAUTH_UI=1`):

1. Start server / deploy to k8s
2. Open `/test`
3. Connect with LinkedIn (or paste `token.json`)
4. Call `get_me` → then `create_post` with **dry_run** → then **confirm**

**CLI:**

```bash
python scripts/oauth_connect.py
./scripts/manual_mcp_call.sh get_me
./scripts/manual_mcp_call.sh create_post --dry-run
./scripts/manual_mcp_call.sh create_post --confirm --text "hello from linkedin-mcp"
```

## Docker

```bash
docker build -t linkedin-mcp .
docker run -p 8000:8000 \
  -e LINKEDIN_CLIENT_ID=... \
  -e LINKEDIN_CLIENT_SECRET=... \
  linkedin-mcp
```

## Kubernetes (`mcp-tools`)

Deploys as `linkedin-mcp-main` (same naming pattern as `gmail-mcp-main`):

```bash
cp .env.example .env   # set LINKEDIN_CLIENT_ID / LINKEDIN_CLIENT_SECRET
chmod +x k8s-deploy.sh
./k8s-deploy.sh                    # build local image + apply to mcp-tools
# ./k8s-deploy.sh --image-repo docker.io/datumbridge/tools-linkedin-mcp --image-tag main --push
```

- Service: `http://linkedin-mcp-main.mcp-tools.svc.cluster.local:8000`
- MCP: `http://linkedin-mcp-main.mcp-tools.svc.cluster.local:8000/mcp/`
- Undeploy: `./k8s-undeploy.sh` (add `--delete-secret` to remove OAuth secret)

## Architecture

```text
Studio / LangGraph → POST /mcp → mcp_server tools → LinkedInService → LinkedIn API v2
```

- Fail-fast on missing credentials (`CREDENTIALS_REQUIRED`)
- Domain errors return structured `{error_code, error_message, retryable, ...}`
- Tools return data only (no approve/refuse/policy decisions)
- Profile/post payloads are **untrusted** (`content_trust=untrusted`)
- Never log tokens or post bodies; `/oauth/token` never returns `client_secret`
- OAuth UI off by default; `credentials_path` jailed under `LINKEDIN_CREDENTIALS_DIR`

## Non-goals (v1)

Organization pages, ads, messaging, connections search, comments/reactions, and scraping are out of scope. See [design.md](design.md).

## Project structure

```text
linkedin-mcp/
├── app/mcp_server.py
├── app/oauth_routes.py
├── app/services/linkedin_service.py
├── app/core/exceptions.py
├── app/schemas/mcp_models.py
├── scripts/
├── static/test-ui.html
├── docs/
├── Dockerfile
└── requirements_mcp.txt
```
