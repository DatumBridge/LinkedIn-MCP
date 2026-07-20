# Workflows — LinkedIn MCP

## Connect (local)

1. Operator sets client id/secret and opens `/oauth/start` (or runs `scripts/oauth_connect.py`).
2. LinkedIn consent grants OIDC + `w_member_social`.
3. Token JSON is redeemed and used as `credentials_json` / `credentials_path`.

## Share text/article

1. Caller invokes `get_me` (optional).
2. Recommended: `create_post(..., dry_run=true)` to preview.
3. Human / workflow HITL approval.
4. `create_post(..., confirm=true)` with text and optional `https` `article_url`.
5. Tool returns `post_urn` on success.

## Share image

1. Caller base64-encodes image bytes.
2. Optional dry-run, then HITL.
3. `create_image_post(..., confirm=true)`.
4. Service registers upload, uploads binary, creates IMAGE ugcPost.

## Delete

1. HITL approval.
2. `delete_post(..., confirm=true)`.
3. Service issues `DELETE /v2/ugcPosts/{urn}`.
