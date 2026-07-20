# Integrations — LinkedIn MCP

## LinkedIn REST

| Surface | Endpoint | Used by |
|---------|----------|---------|
| OIDC userinfo | `GET /v2/userinfo` | `get_me` |
| UGC Posts | `POST/GET/DELETE /v2/ugcPosts` | create/get/delete post |
| Assets | `POST /v2/assets?action=registerUpload` | `create_image_post` |
| OAuth token | `POST https://www.linkedin.com/oauth/v2/accessToken` | refresh + connect |

Headers:

- `Authorization: Bearer <token>`
- `X-Restli-Protocol-Version: 2.0.0`
- Optional `LinkedIn-Version` from `LINKEDIN_API_VERSION`

## DatumBridge

- Tool Registry: `mcpServer=linkedin`
- Studio / LangGraph call Streamable HTTP `/mcp`
- Sibling pattern: `gmail-mcp`, `google-drive-mcp`
