# System Overview — LinkedIn MCP

## What changed

Greenfield LinkedIn tool-server under `mcp/linkedin-mcp`.

## Why

Agents and Studio workflows need first-class LinkedIn member interactions (profile + personal feed sharing) without scraping or Marketing Partner APIs.

## Components

| Component | Role |
|-----------|------|
| `app/mcp_server.py` | FastMCP tools + Starlette `/health` `/oauth/*` `/test` |
| `app/services/linkedin_service.py` | LinkedIn REST client (OIDC userinfo, ugcPosts, assets) |
| `app/oauth_routes.py` | Local-dev OAuth connect UI (opt-in) |
| LinkedIn API v2 | External provider |

## Controls

- Side effects require `confirm=true`; create tools support `dry_run` payload preview
- Default post visibility is `CONNECTIONS` (not `PUBLIC`)
- Profile/post fields labeled `content_trust=untrusted`
- Local create rate limit (`LINKEDIN_CREATE_RATE_LIMIT`)
- Person URN author binding; Consumer scopes only
- OAuth UI off by default (`LINKEDIN_ENABLE_OAUTH_UI=0`); credential path jail; upload host allowlist

## Dependencies

- FastMCP, uvicorn, requests, pydantic
- LinkedIn Developer app with Sign In (OIDC) + Share on LinkedIn

## Risks

- Share product / scope not enabled → `PERMISSION_DENIED`
- Member share rate limits (~150/day) → `RATE_LIMIT` (retryable)
- Access-token expiry; refresh only when refresh_token + client secret (env) present
- Agents must still apply HITL before confirm=true publishes
