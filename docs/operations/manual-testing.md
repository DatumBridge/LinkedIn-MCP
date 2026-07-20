# Manual testing — LinkedIn MCP

Use this for local or Kubernetes smoke/manual verification. Tools return **data only**; side effects require `confirm=true`.

## Prerequisites

1. LinkedIn Developer app with products:
   - **Sign In with LinkedIn using OpenID Connect**
   - **Share on LinkedIn**
2. Scopes: `openid profile email w_member_social`
3. Client id/secret in `.env` (`LINKEDIN_CLIENT_ID`, `LINKEDIN_CLIENT_SECRET`)

## Option A — Browser Test UI (recommended)

### Local

```bash
cd mcp/linkedin-mcp
cp .env.example .env   # if needed
# Required for UI:
# LINKEDIN_ENABLE_OAUTH_UI=1
# OAUTH_REDIRECT_URI=http://localhost:8000/oauth/callback

python -m venv .venv && source .venv/bin/activate
pip install -r requirements_mcp.txt
./mcp_server_entrypoint.sh
```

Open:

- Test UI: http://localhost:8000/test
- Health: http://localhost:8000/health
- OAuth start: http://localhost:8000/oauth/start

In LinkedIn Developer Portal → Auth → Authorized redirect URLs, add **exactly**:

`http://localhost:8000/oauth/callback`

### Kubernetes (`mcp-tools`)

```bash
cd mcp/linkedin-mcp
# In .env set:
# LINKEDIN_ENABLE_OAUTH_UI=1
# OAUTH_REDIRECT_URI=http://127.0.0.1:<NODEPORT>/oauth/callback
./k8s-deploy.sh
kubectl -n mcp-tools get svc linkedin-mcp-main -o jsonpath='{.spec.ports[0].nodePort}{"\n"}'
```

Open `http://127.0.0.1:<NODEPORT>/test`.

Add the same NodePort callback URL in LinkedIn redirect URLs.

### UI checklist

1. **Health** → `{"status":"ok","service":"linkedin-mcp"}`
2. **Connect with LinkedIn** (or paste `token.json`)
3. Call **`get_me`** → expect `person_urn`
4. Call **`create_post`** with **dry_run** checked → expect `request_body` preview
5. Uncheck dry_run, check **confirm**, call again → expect `post_urn`
6. **`get_post`** with that URN
7. **`delete_post`** with **confirm** checked

## Option B — CLI OAuth + curl

```bash
# 1) Get token (writes token.json; chmod 600)
python scripts/oauth_connect.py

# 2) Health
curl -fsS http://localhost:8000/health

# 3) MCP initialize + tools/call (example: get_me)
# See scripts/manual_mcp_call.sh
./scripts/manual_mcp_call.sh get_me
./scripts/manual_mcp_call.sh create_post --dry-run
./scripts/manual_mcp_call.sh create_post --confirm --text "hello from linkedin-mcp"
```

## Option C — Unit helpers (no LinkedIn network)

```bash
python scripts/test_helpers.py -v
```

## Safety notes

| Control | Behavior |
|---------|----------|
| `confirm=true` | Required to publish or delete |
| `dry_run=true` | Preview create payload without LinkedIn write |
| Default visibility | `CONNECTIONS` |
| OAuth UI | Off by default (`LINKEDIN_ENABLE_OAUTH_UI=0`) |
| `/oauth/token` | Never returns `client_secret` |
| Profile/post fields | `content_trust=untrusted` — not instructions |

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `/test` → 404 `OAUTH_UI_DISABLED` | Set `LINKEDIN_ENABLE_OAUTH_UI=1` and restart/redeploy |
| OAuth `state_mismatch` | Use same host as `OAUTH_REDIRECT_URI`; cookies path `/oauth` |
| `PERMISSION_DENIED` on create | Enable **Share on LinkedIn** product on the app |
| `CONFIRM_REQUIRED` | Pass `confirm=true` (or use dry_run for creates) |
| `CREDENTIALS_REQUIRED` | Provide `credentials_json` / Connect OAuth |
| Image tool schema error | Ensure `image_base64` is first required arg (already fixed in server) |

## Registry

- `mcpServer=linkedin`
- In-cluster base: `http://linkedin-mcp-main.mcp-tools.svc.cluster.local:8000`
- MCP path: `/mcp/`
