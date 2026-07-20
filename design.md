# Design: LinkedIn MCP Server

## Class

**Python FastMCP tool-server** (DatumBridge taxonomy). Not a transport/relay — do not copy `datumbridge-mcp-ws-hub` WebSocket, pairing, or correlation patterns.

## Purpose

Expose LinkedIn **member** profile and **Share on LinkedIn** operations as MCP tools for DatumBridge Studio / LangGraph workflows.

## Architecture

```text
Caller → Streamable HTTP /mcp → FastMCP tools → LinkedInService → LinkedIn REST (v2)
                 ↑
         OAuth credentials per call
```

## Key decisions

1. **Pass-through OAuth** — each tool call supplies `credentials_path` or `credentials_json`. No server-side encrypted token vault in v1.
2. **Consumer products only (v1)** — Sign In with LinkedIn (OIDC) + Share on LinkedIn. Default scopes: `openid profile email w_member_social` (allowlisted).
3. **Focused tools** — one capability per tool; no `linkedin_execute(action=…)` god-tool.
4. **Fail-fast** — missing credentials → `CREDENTIALS_REQUIRED`, not empty success lists.
5. **Data ≠ decisions** — tools return LinkedIn data; workflows decide what to post/approve.
6. **Size + confirm gates** — image/text limits; create/delete require `confirm=true`; create tools support optional `dry_run`.
7. **Default visibility `CONNECTIONS`** — safer than `PUBLIC` unless callers opt in.
8. **OAuth UI deny-by-default** — `LINKEDIN_ENABLE_OAUTH_UI` defaults to `0` (entrypoint + Docker).
9. **Author binding** — posts must use the authenticated member person URN.
10. **Untrusted content** — profile/post fields labeled `content_trust=untrusted`.

## v1 tools

| Tool | Purpose |
|------|---------|
| `get_me` | OpenID userinfo → person URN / name / email |
| `create_post` | Text and optional article URL share (`POST /v2/ugcPosts`) |
| `create_image_post` | Register upload → binary → IMAGE share |
| `get_post` | Fetch UGC post by URN |
| `delete_post` | Delete UGC post by URN |

## Non-goals (v1)

- Organization / Company Page posting — use sibling **`linkedin-corp-mcp`** (`mcpServer=linkedin-corp`)
- Ads, Lead Gen, analytics
- Messaging / InMail
- Connections graph, People Search, scraping
- Comments / reactions (partner-gated surfaces)
- Video / carousel / poll / document posts
- WS hub / edge relay patterns
- Resources / prompts
- Shared Google/LinkedIn OAuth library package

## Platform contracts

- `GET /health`
- `POST /mcp/` Streamable HTTP (`initialize` → `Mcp-Session-Id` → `tools/list` | `tools/call`)
- Registry: `mcpServer=linkedin`

See ADRs under `docs/adr/`.
