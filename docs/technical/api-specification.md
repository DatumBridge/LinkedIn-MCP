# API Specification — LinkedIn MCP

## HTTP endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Liveness `{status, service}` |
| POST | `/mcp/` | Streamable HTTP MCP |
| GET | `/test` | Local test UI (gated) |
| GET | `/oauth/start` | Begin OAuth (gated) |
| GET | `/oauth/callback` | OAuth redirect (gated) |
| GET | `/oauth/token` | One-shot redeem (gated) |
| GET | `/oauth/info` | Redirect URI + scopes (gated) |

## MCP tools

### `get_me`

**Input:** `credentials_path?`, `credentials_json?`  
**Output:** `{success, profile?, error?}`

### `create_post`

**Input:** `text`, `visibility?` (default `CONNECTIONS`), `article_url?`, `article_title?`, `article_description?`, `author_urn?`, `confirm` (required true to publish), `dry_run?`, credentials  
**Output:** `{success, post_id?, post_urn?, author_urn?, visibility?, message?, dry_run?, request_body?, error?}`

### `create_image_post`

**Input:** `text`, `image_base64`, `image_media_type?`, `visibility?` (default `CONNECTIONS`), `author_urn?`, `confirm`, `dry_run?`, credentials  
**Output:** same shape as `create_post`

### `get_post`

**Input:** `post_urn`, credentials  
**Output:** `{success, post?, error?}` — `post.content_trust` is `untrusted`

### `delete_post`

**Input:** `post_urn`, `confirm` (required true), credentials  
**Output:** `{success, post_urn?, message?, error?}`

## Error body

```json
{
  "error_code": "CREDENTIALS_REQUIRED",
  "error_message": "...",
  "retryable": false,
  "original_provider_error": null
}
```

Common codes: `CREDENTIALS_REQUIRED`, `INVALID_CREDENTIALS`, `AUTH_ERROR`, `PERMISSION_DENIED`, `NOT_FOUND`, `RATE_LIMIT`, `VALIDATION_ERROR`, `PROVIDER_ERROR`.

## Authentication

OAuth 2.0 bearer token supplied per call. LinkedIn app products: Sign In (OIDC) + Share on LinkedIn.
