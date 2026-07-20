#!/bin/bash
# Entrypoint for running LinkedIn MCP Server in HTTP/SSE mode
# Usage: ./mcp_server_entrypoint.sh

cd "$(dirname "$0")"
export LINKEDIN_ENABLE_OAUTH_UI="${LINKEDIN_ENABLE_OAUTH_UI:-0}"
uvicorn app.mcp_server:http_app --host 0.0.0.0 --port 8000
