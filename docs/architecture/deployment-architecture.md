# Deployment Architecture — LinkedIn MCP

## Runtime

- Container: Python 3.11-slim, non-root `appuser`
- Process: `uvicorn app.mcp_server:http_app --host 0.0.0.0 --port 8000`
- Health: `GET /health`
- MCP: `POST /mcp/`

## Kubernetes

- Namespace: `mcp-tools` (platform default)
- Resources: `linkedin-mcp-main` Deployment + NodePort Service + ConfigMap + Secret
- In-cluster URL: `http://linkedin-mcp-main.mcp-tools.svc.cluster.local:8000`
- Deploy: `./k8s-deploy.sh` (see README)

## Environment

See [configuration](../technical/configuration.md). Production defaults:

- `LINKEDIN_ENABLE_OAUTH_UI=0`
- Secrets via K8s Secret / platform env, never baked into image

## Platform wiring

- Register as `mcpServer=linkedin` pointing at service `/mcp`
- Prefer Studio credential vault inject of `credentials_json` on `tools/call`
