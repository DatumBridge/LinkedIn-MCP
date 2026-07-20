"""
LinkedIn API wrapper layer.

All LinkedIn HTTP logic lives here. Credentials are passed as input
(credentials_path or credentials_json) — not from environment defaults.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import quote, urlparse

import requests

from app.core.exceptions import (
    LinkedInError,
    LinkedInValidationError,
    normalize_linkedin_error,
)

DEFAULT_SCOPES = ("openid", "profile", "email", "w_member_social")
ALLOWED_SCOPES = frozenset(DEFAULT_SCOPES)
TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
API_BASE = "https://api.linkedin.com/v2"
USERINFO_URL = f"{API_BASE}/userinfo"
UGC_POSTS_URL = f"{API_BASE}/ugcPosts"
ASSETS_URL = f"{API_BASE}/assets"
DEFAULT_MAX_IMAGE_BYTES = 8 * 1024 * 1024  # 8 MiB
DEFAULT_MAX_TEXT_CHARS = 3000
DEFAULT_TIMEOUT_SEC = 30
ALLOWED_IMAGE_MEDIA_TYPES = frozenset(
    {"image/jpeg", "image/png", "image/gif", "image/webp"}
)
UPLOAD_HOST_SUFFIXES = (".linkedin.com", ".licdn.com")

# Simple per-process create throttle (keyed by token fingerprint).
_create_events: Dict[str, list] = {}


def _max_image_bytes() -> int:
    raw = os.environ.get("LINKEDIN_MAX_IMAGE_BYTES", "").strip()
    if not raw:
        return DEFAULT_MAX_IMAGE_BYTES
    try:
        return max(1, int(raw))
    except ValueError:
        return DEFAULT_MAX_IMAGE_BYTES


def _max_text_chars() -> int:
    raw = os.environ.get("LINKEDIN_MAX_TEXT_CHARS", "").strip()
    if not raw:
        return DEFAULT_MAX_TEXT_CHARS
    try:
        return max(1, int(raw))
    except ValueError:
        return DEFAULT_MAX_TEXT_CHARS


def _request_timeout() -> int:
    raw = os.environ.get("LINKEDIN_HTTP_TIMEOUT_SEC", "").strip()
    if not raw:
        return DEFAULT_TIMEOUT_SEC
    try:
        return max(1, int(raw))
    except ValueError:
        return DEFAULT_TIMEOUT_SEC


def _create_rate_limit() -> int:
    """Max creates per window (default 10). Set 0 to disable."""
    raw = os.environ.get("LINKEDIN_CREATE_RATE_LIMIT", "10").strip()
    try:
        return max(0, int(raw))
    except ValueError:
        return 10


def _create_rate_window_sec() -> int:
    raw = os.environ.get("LINKEDIN_CREATE_RATE_WINDOW_SEC", "3600").strip()
    try:
        return max(60, int(raw))
    except ValueError:
        return 3600


def _credentials_dir() -> Path:
    raw = os.environ.get("LINKEDIN_CREDENTIALS_DIR", "").strip()
    if raw:
        return Path(raw).resolve()
    return Path(__file__).resolve().parent.parent.parent


def _is_oauth_creds(creds_dict: dict) -> bool:
    has_access = bool(creds_dict.get("access_token") or creds_dict.get("token"))
    has_refresh = bool(creds_dict.get("refresh_token"))
    return creds_dict.get("type") == "oauth" or has_access or has_refresh


def _resolve_credentials_path(credentials_path: str) -> Path:
    """Resolve credentials_path inside LINKEDIN_CREDENTIALS_DIR (path jail)."""
    base = _credentials_dir()
    candidate = Path(credentials_path)
    if not candidate.is_absolute():
        candidate = (base / candidate).resolve()
    else:
        candidate = candidate.resolve()
    try:
        candidate.relative_to(base)
    except ValueError as e:
        raise LinkedInError(
            "credentials_path must be under LINKEDIN_CREDENTIALS_DIR",
            error_code="INVALID_CREDENTIALS",
            retryable=False,
            original_error=e,
        ) from e
    return candidate


def load_credentials_dict(
    credentials_path: Optional[str] = None,
    credentials_json: Optional[str] = None,
) -> dict:
    """Load and validate OAuth credential dict from path or JSON string."""
    creds_dict = None
    try:
        if credentials_json:
            creds_dict = json.loads(credentials_json)
        elif credentials_path:
            path = _resolve_credentials_path(credentials_path)
            if not path.exists():
                raise LinkedInError(
                    f"Credentials file not found: {credentials_path}",
                    error_code="CREDENTIALS_REQUIRED",
                    retryable=False,
                )
            with open(path) as f:
                creds_dict = json.load(f)
    except LinkedInError:
        raise
    except json.JSONDecodeError as e:
        raise LinkedInError(
            "Invalid credentials JSON",
            error_code="INVALID_CREDENTIALS",
            retryable=False,
            original_error=e,
        ) from e
    except OSError as e:
        raise LinkedInError(
            "Unable to read credentials file",
            error_code="INVALID_CREDENTIALS",
            retryable=False,
            original_error=e,
        ) from e

    if not creds_dict or not isinstance(creds_dict, dict):
        raise LinkedInError(
            "Credentials required: provide credentials_path or credentials_json (OAuth token)",
            error_code="CREDENTIALS_REQUIRED",
            retryable=False,
        )

    if not _is_oauth_creds(creds_dict):
        raise LinkedInError(
            "OAuth credentials required. Use Connect with LinkedIn in the test UI "
            "or run scripts/oauth_connect.py to get a token.",
            error_code="INVALID_CREDENTIALS",
            retryable=False,
        )

    access = creds_dict.get("access_token") or creds_dict.get("token")
    refresh = creds_dict.get("refresh_token")
    if not access and not refresh:
        raise LinkedInError(
            "OAuth credentials must include access_token (or token), or refresh_token",
            error_code="INVALID_CREDENTIALS",
            retryable=False,
        )

    return creds_dict


def person_urn_from_id(person_id: str) -> str:
    pid = (person_id or "").strip()
    if not pid:
        raise LinkedInValidationError("person_id is required")
    if pid.startswith("urn:li:person:"):
        return pid
    if pid.startswith("urn:li:"):
        raise LinkedInValidationError(
            "person_id must be a person id or urn:li:person:..."
        )
    return f"urn:li:person:{pid}"


def validate_person_urn(author_urn: str) -> str:
    urn = (author_urn or "").strip()
    if not urn.startswith("urn:li:person:") or urn == "urn:li:person:":
        raise LinkedInValidationError(
            "author_urn must be urn:li:person:<id>"
        )
    return urn


def validate_post_urn(post_urn: str) -> str:
    urn = (post_urn or "").strip()
    if not urn:
        raise LinkedInValidationError("post_urn is required")
    if not (
        urn.startswith("urn:li:ugcPost:")
        or urn.startswith("urn:li:share:")
    ):
        raise LinkedInValidationError(
            "post_urn must be urn:li:ugcPost:... or urn:li:share:..."
        )
    return urn


def encode_urn(urn: str) -> str:
    """URL-encode a LinkedIn URN for path segments."""
    return quote(urn, safe="")


def normalize_visibility(visibility: Optional[str]) -> str:
    raw = "" if visibility is None else str(visibility).strip()
    if not raw:
        return "CONNECTIONS"
    value = raw.upper()
    if value not in ("PUBLIC", "CONNECTIONS"):
        raise LinkedInValidationError(
            "visibility must be PUBLIC or CONNECTIONS"
        )
    return value


def validate_article_url(article_url: str) -> str:
    url = (article_url or "").strip()
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise LinkedInValidationError("article_url must be an https:// URL")
    return url


def validate_upload_url(upload_url: str) -> str:
    parsed = urlparse((upload_url or "").strip())
    if parsed.scheme != "https" or not parsed.hostname:
        raise LinkedInValidationError("uploadUrl must be https with a host")
    host = parsed.hostname.lower()
    if not any(host == s[1:] or host.endswith(s) for s in UPLOAD_HOST_SUFFIXES):
        # also allow exact linkedin.com / licdn.com
        if host not in ("linkedin.com", "licdn.com"):
            raise LinkedInValidationError(
                "uploadUrl host is not an allowed LinkedIn media host"
            )
    return upload_url


def validate_oauth_scopes(scopes: Optional[list]) -> list:
    if not scopes:
        return list(DEFAULT_SCOPES)
    normalized = [str(s).strip() for s in scopes if str(s).strip()]
    unknown = [s for s in normalized if s not in ALLOWED_SCOPES]
    if unknown:
        raise LinkedInValidationError(
            f"Unsupported OAuth scopes for v1: {', '.join(unknown)}. "
            f"Allowed: {' '.join(DEFAULT_SCOPES)}"
        )
    return normalized


def _parse_expires_at(value: Any) -> Optional[float]:
    """Return unix seconds expiry, or None if absent. Fail closed on garbage."""
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        exp = float(value)
        return exp / 1000.0 if exp >= 1e12 else exp
    text = str(value).strip()
    try:
        exp = float(text)
        return exp / 1000.0 if exp >= 1e12 else exp
    except ValueError:
        pass
    # ISO-8601 basic support
    try:
        from datetime import datetime

        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        return datetime.fromisoformat(text).timestamp()
    except Exception as e:
        raise LinkedInError(
            "expires_at/expiry is not a parseable timestamp",
            error_code="INVALID_CREDENTIALS",
            retryable=False,
            original_error=e,
        ) from e


class LinkedInService:
    """Thin LinkedIn REST client for member profile + Share on LinkedIn."""

    def __init__(
        self,
        credentials_path: Optional[str] = None,
        credentials_json: Optional[str] = None,
    ):
        self._creds = load_credentials_dict(credentials_path, credentials_json)
        self._access_token = self._ensure_access_token()
        self._token_fp = hashlib.sha256(self._access_token.encode("utf-8")).hexdigest()[
            :16
        ]

    def _client_id_secret(self) -> tuple[str, str]:
        client_id = (
            self._creds.get("client_id")
            or os.environ.get("LINKEDIN_CLIENT_ID", "")
        ).strip()
        client_secret = (
            self._creds.get("client_secret")
            or os.environ.get("LINKEDIN_CLIENT_SECRET", "")
        ).strip()
        return client_id, client_secret

    def _ensure_access_token(self) -> str:
        token = self._creds.get("access_token") or self._creds.get("token")
        expires_at = _parse_expires_at(
            self._creds.get("expires_at") or self._creds.get("expiry")
        )
        needs_refresh = False
        if not token:
            needs_refresh = True
        elif expires_at is not None:
            needs_refresh = time.time() >= (expires_at - 60)

        if needs_refresh:
            token = self._refresh_access_token()
        if not token:
            raise LinkedInError(
                "No usable access token",
                error_code="AUTH_ERROR",
                retryable=True,
            )
        return token

    def _refresh_access_token(self) -> str:
        refresh = self._creds.get("refresh_token")
        client_id, client_secret = self._client_id_secret()
        if not (refresh and client_id and client_secret):
            raise LinkedInError(
                "Access token expired and refresh_token/client credentials missing",
                error_code="AUTH_ERROR",
                retryable=True,
            )
        try:
            resp = requests.post(
                TOKEN_URL,
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": refresh,
                    "client_id": client_id,
                    "client_secret": client_secret,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=_request_timeout(),
            )
            if resp.status_code >= 400:
                raise LinkedInError(
                    "Token refresh failed",
                    error_code="AUTH_ERROR",
                    retryable=True,
                    original_error=f"HTTP {resp.status_code}",
                )
            data = resp.json()
        except LinkedInError:
            raise
        except Exception as e:
            raise normalize_linkedin_error(e) from e

        access = data.get("access_token")
        if not access:
            raise LinkedInError(
                "Token refresh returned no access_token",
                error_code="AUTH_ERROR",
                retryable=True,
            )
        self._creds["access_token"] = access
        self._creds["token"] = access
        if data.get("refresh_token"):
            self._creds["refresh_token"] = data["refresh_token"]
        expires_in = data.get("expires_in")
        if expires_in:
            self._creds["expires_at"] = int(time.time()) + int(expires_in)
        return access

    def _headers(self, extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "X-Restli-Protocol-Version": "2.0.0",
            "Content-Type": "application/json",
        }
        version = os.environ.get("LINKEDIN_API_VERSION", "").strip()
        if version:
            headers["LinkedIn-Version"] = version
        if extra:
            headers.update(extra)
        return headers

    def _request(
        self,
        method: str,
        url: str,
        *,
        json_body: Optional[dict] = None,
        data: Any = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Any:
        try:
            resp = requests.request(
                method,
                url,
                headers=self._headers(headers),
                json=json_body,
                data=data,
                timeout=_request_timeout(),
            )
        except Exception as e:
            raise normalize_linkedin_error(e) from e

        if resp.status_code >= 400:
            raise normalize_linkedin_error(
                Exception(f"HTTP {resp.status_code}"),
                status_code=resp.status_code,
            )

        restli_id = (
            resp.headers.get("x-restli-id")
            or resp.headers.get("X-RestLi-Id")
            or resp.headers.get("x-linkedin-id")
        )

        if resp.status_code == 204 or not resp.content:
            return {"id": restli_id} if restli_id else {}

        content_type = (resp.headers.get("Content-Type") or "").lower()
        payload: Any
        if "application/json" in content_type:
            payload = resp.json()
        else:
            text = resp.text.strip()
            if text.startswith("{"):
                payload = resp.json()
            elif text:
                payload = {"id": text}
            else:
                payload = {}

        if isinstance(payload, dict) and restli_id and not payload.get("id"):
            payload["id"] = restli_id
        return payload

    def _throttle_create(self) -> None:
        limit = _create_rate_limit()
        if limit <= 0:
            return
        window = _create_rate_window_sec()
        now = time.time()
        events = _create_events.setdefault(self._token_fp, [])
        events[:] = [t for t in events if now - t < window]
        if len(events) >= limit:
            raise LinkedInError(
                f"Local create rate limit exceeded ({limit}/{window}s). "
                "Set LINKEDIN_CREATE_RATE_LIMIT=0 to disable (not recommended).",
                error_code="RATE_LIMIT",
                retryable=True,
            )
        events.append(now)

    def _resolve_author(self, author_urn: Optional[str]) -> str:
        me = self.get_me()
        me_urn = me.get("person_urn")
        if not me_urn:
            raise LinkedInValidationError("Unable to resolve author person URN")
        if author_urn:
            requested = validate_person_urn(author_urn)
            if requested != me_urn:
                raise LinkedInValidationError(
                    "author_urn must match the authenticated member from get_me"
                )
            return requested
        return me_urn

    def get_me(self) -> Dict[str, Any]:
        """Return OpenID userinfo for the authenticated member."""
        data = self._request("GET", USERINFO_URL)
        sub = data.get("sub") or data.get("id")
        person_urn = person_urn_from_id(str(sub)) if sub else None
        return {
            "sub": sub,
            "person_urn": person_urn,
            "name": data.get("name"),
            "given_name": data.get("given_name"),
            "family_name": data.get("family_name"),
            "email": data.get("email"),
            "email_verified": data.get("email_verified"),
            "picture": data.get("picture"),
            "locale": data.get("locale"),
            "content_trust": "untrusted",
        }

    def create_text_post(
        self,
        text: str,
        *,
        visibility: str = "CONNECTIONS",
        article_url: Optional[str] = None,
        article_title: Optional[str] = None,
        article_description: Optional[str] = None,
        author_urn: Optional[str] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Create a member feed share (text or article URL)."""
        commentary = (text or "").strip()
        if not commentary and not article_url:
            raise LinkedInValidationError("text or article_url is required")
        if len(commentary) > _max_text_chars():
            raise LinkedInValidationError(
                f"text exceeds LINKEDIN_MAX_TEXT_CHARS ({_max_text_chars()})"
            )

        vis = normalize_visibility(visibility)
        resolved_author = self._resolve_author(author_urn)

        share_content: Dict[str, Any] = {
            "shareCommentary": {"text": commentary},
            "shareMediaCategory": "NONE",
        }
        if article_url:
            media_item: Dict[str, Any] = {
                "status": "READY",
                "originalUrl": validate_article_url(article_url),
            }
            if article_title:
                media_item["title"] = {"text": article_title.strip()}
            if article_description:
                media_item["description"] = {"text": article_description.strip()}
            share_content["shareMediaCategory"] = "ARTICLE"
            share_content["media"] = [media_item]

        body = {
            "author": resolved_author,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": share_content,
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": vis,
            },
        }
        if dry_run:
            return {
                "dry_run": True,
                "request_body": body,
                "author_urn": resolved_author,
                "visibility": vis,
            }

        self._throttle_create()
        result = self._request("POST", UGC_POSTS_URL, json_body=body)
        post_urn = result.get("id")
        if not post_urn:
            raise LinkedInError(
                "LinkedIn create succeeded but returned no post id",
                error_code="PROVIDER_ERROR",
                retryable=True,
                original_error=result,
            )
        return {
            "post_id": post_urn,
            "post_urn": post_urn,
            "author_urn": resolved_author,
            "visibility": vis,
        }

    def get_post(self, post_urn: str) -> Dict[str, Any]:
        urn = validate_post_urn(post_urn)
        url = f"{UGC_POSTS_URL}/{encode_urn(urn)}"
        post = self._request("GET", url)
        if isinstance(post, dict):
            post = {**post, "content_trust": "untrusted"}
        return post

    def delete_post(self, post_urn: str) -> None:
        urn = validate_post_urn(post_urn)
        url = f"{UGC_POSTS_URL}/{encode_urn(urn)}"
        self._request("DELETE", url)

    def create_image_post(
        self,
        text: str,
        *,
        image_base64: str,
        image_media_type: str = "image/jpeg",
        visibility: str = "CONNECTIONS",
        author_urn: Optional[str] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Register upload, push image bytes, then create an IMAGE share."""
        commentary = (text or "").strip()
        if len(commentary) > _max_text_chars():
            raise LinkedInValidationError(
                f"text exceeds LINKEDIN_MAX_TEXT_CHARS ({_max_text_chars()})"
            )
        if not image_base64 or not str(image_base64).strip():
            raise LinkedInValidationError("image_base64 is required")

        media_type = (image_media_type or "image/jpeg").strip().lower()
        if media_type not in ALLOWED_IMAGE_MEDIA_TYPES:
            raise LinkedInValidationError(
                "image_media_type must be one of: "
                + ", ".join(sorted(ALLOWED_IMAGE_MEDIA_TYPES))
            )

        try:
            raw = base64.b64decode(image_base64, validate=False)
        except Exception as e:
            raise LinkedInValidationError(
                "image_base64 is not valid base64",
                original_error=e,
            ) from e

        if len(raw) == 0:
            raise LinkedInValidationError("image_base64 decoded to empty bytes")

        max_bytes = _max_image_bytes()
        if len(raw) > max_bytes:
            raise LinkedInValidationError(
                f"image exceeds LINKEDIN_MAX_IMAGE_BYTES ({max_bytes})"
            )

        vis = normalize_visibility(visibility)
        resolved_author = self._resolve_author(author_urn)

        if dry_run:
            return {
                "dry_run": True,
                "author_urn": resolved_author,
                "visibility": vis,
                "image_bytes": len(raw),
                "image_media_type": media_type,
            }

        self._throttle_create()
        register_body = {
            "registerUploadRequest": {
                "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
                "owner": resolved_author,
                "serviceRelationships": [
                    {
                        "relationshipType": "OWNER",
                        "identifier": "urn:li:userGeneratedContent",
                    }
                ],
            }
        }
        register = self._request(
            "POST",
            f"{ASSETS_URL}?action=registerUpload",
            json_body=register_body,
        )
        value = register.get("value") or {}
        upload_mech = (
            (value.get("uploadMechanism") or {})
            .get("com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest")
            or {}
        )
        upload_url = upload_mech.get("uploadUrl")
        asset = value.get("asset")
        if not upload_url or not asset:
            raise LinkedInError(
                "Image upload registration did not return uploadUrl/asset",
                error_code="PROVIDER_ERROR",
                retryable=True,
            )

        safe_upload_url = validate_upload_url(upload_url)
        try:
            upload_resp = requests.put(
                safe_upload_url,
                data=raw,
                headers={
                    "Authorization": f"Bearer {self._access_token}",
                    "Content-Type": media_type,
                },
                timeout=_request_timeout(),
                allow_redirects=False,
            )
        except Exception as e:
            raise normalize_linkedin_error(e) from e
        if upload_resp.status_code < 200 or upload_resp.status_code >= 300:
            raise normalize_linkedin_error(
                Exception(f"HTTP {upload_resp.status_code}"),
                status_code=upload_resp.status_code,
            )

        body = {
            "author": resolved_author,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": commentary},
                    "shareMediaCategory": "IMAGE",
                    "media": [
                        {
                            "status": "READY",
                            "media": asset,
                            "title": {"text": "Image"},
                        }
                    ],
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": vis,
            },
        }
        result = self._request("POST", UGC_POSTS_URL, json_body=body)
        post_urn = result.get("id")
        if not post_urn:
            raise LinkedInError(
                "LinkedIn create succeeded but returned no post id",
                error_code="PROVIDER_ERROR",
                retryable=True,
            )
        return {
            "post_id": post_urn,
            "post_urn": post_urn,
            "author_urn": resolved_author,
            "visibility": vis,
            "asset_urn": asset,
        }


def build_ugc_text_body(
    author_urn: str,
    text: str,
    visibility: str = "CONNECTIONS",
    article_url: Optional[str] = None,
) -> dict:
    """Pure helper for unit tests — shapes a ugcPosts create body."""
    vis = normalize_visibility(visibility)
    author = validate_person_urn(author_urn)
    share_content: Dict[str, Any] = {
        "shareCommentary": {"text": text},
        "shareMediaCategory": "NONE",
    }
    if article_url:
        share_content["shareMediaCategory"] = "ARTICLE"
        share_content["media"] = [
            {"status": "READY", "originalUrl": validate_article_url(article_url)},
        ]
    return {
        "author": author,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": share_content,
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": vis,
        },
    }
