# Configuration — LinkedIn MCP

| Variable | Required | Default | Notes |
|----------|----------|---------|-------|
| `PORT` | no | `8000` | Documented for ops; uvicorn flag also used |
| `LOG_LEVEL` | no | `INFO` | |
| `LINKEDIN_CLIENT_ID` | for OAuth UI/CLI | | |
| `LINKEDIN_CLIENT_SECRET` | for OAuth UI/CLI / refresh | | Prefer env for refresh; do not store in token JSON |
| `LINKEDIN_OAUTH_CREDENTIALS` | no | `./credentials.json` | Optional client file path |
| `OAUTH_REDIRECT_URI` | **yes when OAuth UI enabled** | | e.g. `http://localhost:8000/oauth/callback` |
| `LINKEDIN_OAUTH_SCOPES` | no | `openid profile email w_member_social` | Allowlisted; unknown scopes ignored / fail closed |
| `LINKEDIN_API_VERSION` | no | unset | Optional `LinkedIn-Version` header |
| `LINKEDIN_MAX_IMAGE_BYTES` | no | `8388608` | |
| `LINKEDIN_MAX_TEXT_CHARS` | no | `3000` | |
| `LINKEDIN_HTTP_TIMEOUT_SEC` | no | `30` | |
| `LINKEDIN_ENABLE_OAUTH_UI` | no | **`0`** | Opt-in only (`1` for local connect). Entrypoint + Docker also default `0`. |
| `LINKEDIN_CREDENTIALS_DIR` | no | project root | Path jail for `credentials_path` |
| `LINKEDIN_CREATE_RATE_LIMIT` | no | `10` | Max creates per window per token fingerprint; `0` disables |
| `LINKEDIN_CREATE_RATE_WINDOW_SEC` | no | `3600` | |
| `TOOL_REGISTRY_BASE_URL` | no | | Optional |
| `TOOL_REGISTRY_API_KEY` | no | | Optional |

Per-call tool inputs always require `credentials_path` or `credentials_json`.

Side-effect tools require `confirm=true`. `create_post` / `create_image_post` also accept `dry_run=true` to preview payloads without publishing (`delete_post` has no dry-run). Default MCP visibility is `CONNECTIONS`.
