# Changelog

## 2026-07-20

### Added

- Initial LinkedIn MCP tool-server (`mcpServer=linkedin`)
- Tools: `get_me`, `create_post`, `create_image_post`, `get_post`, `delete_post`
- Pass-through OAuth credentials, local OAuth UI/CLI, Docker image, docs tree
- Side-effect `confirm` (creates also support `dry_run`), person URN binding, upload host allowlist
- Default post visibility `CONNECTIONS`; credential path jail; OAuth UI default-off (`LINKEDIN_ENABLE_OAUTH_UI=0`); untrusted content labeling
- Kubernetes deploy to `mcp-tools` (`linkedin-mcp-main`, `./k8s-deploy.sh`)
- Manual Test UI (`/test`) with real MCP `tools/call`, plus `docs/operations/manual-testing.md` and `scripts/manual_mcp_call.sh`
