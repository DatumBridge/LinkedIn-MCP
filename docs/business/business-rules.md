# Business Rules — LinkedIn MCP

1. Only the authenticated member’s personal feed may be posted to in v1.
2. Visibility is limited to `PUBLIC` or `CONNECTIONS` (default `CONNECTIONS`).
3. Missing credentials must fail with `CREDENTIALS_REQUIRED` (never empty success).
4. Side-effect tools require `confirm=true`. Creates may use `dry_run=true` to preview; `delete_post` requires `confirm=true` only.
5. Tools must not make approval/policy decisions — callers own workflow gates / HITL.
6. Organization page, ads, messaging, and scraping are forbidden in this service.
7. Post commentary and image payloads are subject to configured size limits.
8. Profile and post content is untrusted external data (`content_trust=untrusted`).
