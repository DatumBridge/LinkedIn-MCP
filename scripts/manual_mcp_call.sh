#!/usr/bin/env bash
# Manual MCP tool caller for LinkedIn MCP (Streamable HTTP).
#
# Usage:
#   ./scripts/manual_mcp_call.sh get_me
#   ./scripts/manual_mcp_call.sh create_post --dry-run
#   ./scripts/manual_mcp_call.sh create_post --confirm --text "hello"
#   ./scripts/manual_mcp_call.sh get_post --urn "urn:li:share:..."
#   ./scripts/manual_mcp_call.sh delete_post --confirm --urn "urn:li:share:..."
#   ./scripts/manual_mcp_call.sh tools_list
#
# Env:
#   BASE_URL=http://localhost:8000
#   TOKEN_FILE=./token.json

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BASE_URL="${BASE_URL:-http://localhost:8000}"
TOKEN_FILE="${TOKEN_FILE:-${ROOT_DIR}/token.json}"

TOOL="${1:-}"
shift || true

DRY_RUN=0
CONFIRM=0
TEXT="LinkedIn MCP manual test"
URN=""
VISIBILITY="CONNECTIONS"

usage() {
  cat <<'EOF'
Usage:
  ./scripts/manual_mcp_call.sh <tool> [options]

Tools: get_me | create_post | get_post | delete_post | tools_list

Options:
  --dry-run
  --confirm
  --text <text>
  --urn <post_urn>
  --visibility PUBLIC|CONNECTIONS
  --base-url <url>
  --token-file <path>
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY_RUN=1; shift ;;
    --confirm) CONFIRM=1; shift ;;
    --text) TEXT="${2:-}"; shift 2 ;;
    --urn) URN="${2:-}"; shift 2 ;;
    --visibility) VISIBILITY="${2:-}"; shift 2 ;;
    --base-url) BASE_URL="${2:-}"; shift 2 ;;
    --token-file) TOKEN_FILE="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1"; usage; exit 1 ;;
  esac
done

if [[ -z "${TOOL}" ]]; then
  usage
  exit 1
fi

python3 - "$BASE_URL" "$TOKEN_FILE" "$TOOL" "$DRY_RUN" "$CONFIRM" "$TEXT" "$URN" "$VISIBILITY" <<'PY'
import json
import sys
import urllib.error
import urllib.request

base, token_file, tool, dry, confirm, text, urn, visibility = sys.argv[1:9]


def post(body, session=None, notification=False):
    payload = {"jsonrpc": "2.0", "method": body["method"]}
    if not notification:
        payload["id"] = body.get("id", 1)
    if "params" in body:
        payload["params"] = body["params"]
    data = json.dumps(payload).encode()
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    if session:
        headers["Mcp-Session-Id"] = session
    req = urllib.request.Request(
        base.rstrip("/") + "/mcp/",
        data=data,
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        sid = resp.headers.get("Mcp-Session-Id") or resp.headers.get("mcp-session-id")
        raw = resp.read().decode()
        return sid, raw


def print_raw(raw: str) -> None:
    # Prefer pretty JSON if response is JSON or SSE data lines.
    if raw.lstrip().startswith("{"):
        try:
            print(json.dumps(json.loads(raw), indent=2))
            return
        except Exception:
            pass
    lines = [ln[5:].strip() for ln in raw.splitlines() if ln.startswith("data:")]
    if lines:
        objs = []
        for ln in lines:
            try:
                objs.append(json.loads(ln))
            except Exception:
                objs.append(ln)
        print(json.dumps(objs if len(objs) > 1 else objs[0], indent=2))
        return
    print(raw)


try:
    sid, _ = post(
        {
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "manual-cli", "version": "1.0"},
            },
        }
    )
    if not sid:
        raise SystemExit("No Mcp-Session-Id from initialize")
    post({"method": "notifications/initialized", "params": {}}, session=sid, notification=True)

    if tool == "tools_list":
        _, raw = post({"id": 2, "method": "tools/list", "params": {}}, session=sid)
        print_raw(raw)
        raise SystemExit(0)

    with open(token_file) as f:
        creds = json.load(f)

    args = {"credentials_json": json.dumps(creds)}
    if tool == "get_me":
        pass
    elif tool == "create_post":
        args.update(
            {
                "text": text,
                "visibility": visibility,
                "dry_run": dry == "1",
                "confirm": confirm == "1",
            }
        )
    elif tool == "get_post":
        if not urn:
            raise SystemExit("--urn required for get_post")
        args["post_urn"] = urn
    elif tool == "delete_post":
        if not urn:
            raise SystemExit("--urn required for delete_post")
        args["post_urn"] = urn
        args["confirm"] = confirm == "1"
    else:
        raise SystemExit(f"Unsupported tool: {tool}")

    _, raw = post(
        {"id": 2, "method": "tools/call", "params": {"name": tool, "arguments": args}},
        session=sid,
    )
    print_raw(raw)
except FileNotFoundError:
    raise SystemExit(f"Missing {token_file}. Run: python scripts/oauth_connect.py")
except urllib.error.HTTPError as e:
    body = e.read().decode(errors="replace")
    raise SystemExit(f"HTTP {e.code}: {body}")
PY
