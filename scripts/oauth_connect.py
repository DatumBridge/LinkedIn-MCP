#!/usr/bin/env python3
"""
OAuth 2.0 connection script for LinkedIn (Sign In + Share).

Usage:
    1. Create a LinkedIn app in Developer Portal
    2. Enable products: Sign In with LinkedIn (OpenID Connect) + Share on LinkedIn
    3. Set LINKEDIN_CLIENT_ID / LINKEDIN_CLIENT_SECRET (or credentials.json)
    4. python scripts/oauth_connect.py
    5. Use token.json as credentials_path for MCP tools

This script uses a local loopback redirect (default http://127.0.0.1:8765/callback).
Add that exact URL under Auth → Authorized redirect URLs.
"""

from __future__ import annotations

import json
import os
import sys
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:
    import requests
except ImportError:
    print("Error: pip install requests")
    sys.exit(1)

DEFAULT_SCOPES = ["openid", "profile", "email", "w_member_social"]
ALLOWED_SCOPES = frozenset(DEFAULT_SCOPES)
TOKEN_FILE = ROOT / "token.json"
CREDENTIALS_FILE = ROOT / "credentials.json"
AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
REDIRECT_HOST = "127.0.0.1"
REDIRECT_PORT = 8765
REDIRECT_URI = f"http://{REDIRECT_HOST}:{REDIRECT_PORT}/callback"

_auth_code: dict = {}


def _load_client() -> tuple[str, str]:
    client_id = os.environ.get("LINKEDIN_CLIENT_ID", "").strip()
    client_secret = os.environ.get("LINKEDIN_CLIENT_SECRET", "").strip()
    if CREDENTIALS_FILE.exists():
        with open(CREDENTIALS_FILE) as f:
            data = json.load(f)
        client = data.get("web") or data.get("installed") or data
        client_id = client_id or client.get("client_id", "")
        client_secret = client_secret or client.get("client_secret", "")
    return client_id, client_secret


def _scopes() -> list[str]:
    raw = os.environ.get("LINKEDIN_OAUTH_SCOPES", "").strip()
    if not raw:
        return list(DEFAULT_SCOPES)
    requested = [s for s in raw.replace(",", " ").split() if s]
    unknown = [s for s in requested if s not in ALLOWED_SCOPES]
    if unknown:
        print(
            f"Warning: ignoring unsupported scopes {unknown}; "
            f"using defaults {DEFAULT_SCOPES}"
        )
        return list(DEFAULT_SCOPES)
    return requested


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path != "/callback":
            self.send_response(404)
            self.end_headers()
            return
        qs = parse_qs(parsed.query)
        if qs.get("error"):
            _auth_code["error"] = qs["error"][0]
        else:
            _auth_code["code"] = (qs.get("code") or [None])[0]
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(
            b"<html><body><h3>LinkedIn OAuth complete.</h3>"
            b"<p>You can close this window.</p></body></html>"
        )

    def log_message(self, format, *args):  # noqa: A003
        return


def main() -> None:
    client_id, client_secret = _load_client()
    if not client_id or not client_secret:
        print("Error: set LINKEDIN_CLIENT_ID and LINKEDIN_CLIENT_SECRET")
        print(f"  or create {CREDENTIALS_FILE} with client_id/client_secret")
        sys.exit(1)

    scopes = _scopes()
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "scope": " ".join(scopes),
        "state": "linkedin-mcp-cli",
    }
    auth_url = f"{AUTH_URL}?{urlencode(params)}"
    print(f"Redirect URI (must match Developer Portal): {REDIRECT_URI}")
    print("Opening browser for LinkedIn sign-in...")
    webbrowser.open(auth_url)

    server = HTTPServer((REDIRECT_HOST, REDIRECT_PORT), _Handler)
    server.handle_request()

    if _auth_code.get("error"):
        print(f"OAuth error: {_auth_code['error']}")
        sys.exit(1)
    code = _auth_code.get("code")
    if not code:
        print("OAuth failed: no authorization code")
        sys.exit(1)

    resp = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "client_id": client_id,
            "client_secret": client_secret,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30,
    )
    if resp.status_code >= 400:
        print(f"Token exchange failed: HTTP {resp.status_code}")
        sys.exit(1)
    token_data = resp.json()
    expires_in = token_data.get("expires_in")
    # Do not persist client_secret — refresh uses LINKEDIN_CLIENT_SECRET from env.
    out = {
        "type": "oauth",
        "access_token": token_data.get("access_token"),
        "token": token_data.get("access_token"),
        "refresh_token": token_data.get("refresh_token"),
        "token_uri": TOKEN_URL,
        "client_id": client_id,
        "scopes": scopes,
        "expires_at": int(time.time()) + int(expires_in) if expires_in else None,
    }
    with open(TOKEN_FILE, "w") as f:
        json.dump(out, f, indent=2)
    try:
        os.chmod(TOKEN_FILE, 0o600)
    except OSError:
        pass
    print(f"\nSuccess! Token saved to {TOKEN_FILE}")
    print(f"  credentials_path: {TOKEN_FILE}")
    print("  Keep LINKEDIN_CLIENT_SECRET in env for token refresh.")


if __name__ == "__main__":
    main()
