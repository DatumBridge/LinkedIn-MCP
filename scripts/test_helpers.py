#!/usr/bin/env python3
"""Unit tests for LinkedIn MCP helpers (no live LinkedIn API / no FastMCP required)."""

import base64
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.core.exceptions import (
    LinkedInError,
    LinkedInValidationError,
    normalize_linkedin_error,
)
from app.services import linkedin_service as ls
from app.services.linkedin_service import (
    LinkedInService,
    build_ugc_text_body,
    encode_urn,
    load_credentials_dict,
    normalize_visibility,
    person_urn_from_id,
    validate_article_url,
    validate_person_urn,
    validate_post_urn,
    validate_upload_url,
)


class TestExceptions(unittest.TestCase):
    def test_normalize_401(self):
        err = normalize_linkedin_error(Exception("HTTP 401"), status_code=401)
        self.assertEqual(err.error_code, "AUTH_ERROR")
        self.assertTrue(err.retryable)

    def test_normalize_403(self):
        err = normalize_linkedin_error(Exception("HTTP 403"), status_code=403)
        self.assertEqual(err.error_code, "PERMISSION_DENIED")

    def test_normalize_404(self):
        err = normalize_linkedin_error(Exception("HTTP 404"), status_code=404)
        self.assertEqual(err.error_code, "NOT_FOUND")

    def test_normalize_429(self):
        err = normalize_linkedin_error(Exception("HTTP 429"), status_code=429)
        self.assertEqual(err.error_code, "RATE_LIMIT")
        self.assertTrue(err.retryable)


class TestCredentials(unittest.TestCase):
    def test_missing_credentials(self):
        with self.assertRaises(LinkedInError) as ctx:
            load_credentials_dict()
        self.assertEqual(ctx.exception.error_code, "CREDENTIALS_REQUIRED")

    def test_invalid_json(self):
        with self.assertRaises(LinkedInError) as ctx:
            load_credentials_dict(credentials_json="{not-json")
        self.assertEqual(ctx.exception.error_code, "INVALID_CREDENTIALS")

    def test_oauth_json(self):
        payload = {
            "type": "oauth",
            "access_token": "AQV.example",
            "refresh_token": "AQW.example",
            "client_id": "client.example",
            "scopes": ["openid", "profile", "email", "w_member_social"],
        }
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump(payload, f)
            path = f.name
        os.environ["LINKEDIN_CREDENTIALS_DIR"] = str(Path(path).parent)
        self.addCleanup(lambda: os.environ.pop("LINKEDIN_CREDENTIALS_DIR", None))
        creds = load_credentials_dict(credentials_path=Path(path).name)
        self.assertEqual(creds["access_token"], payload["access_token"])

    def test_path_jail_rejects_escape(self):
        os.environ["LINKEDIN_CREDENTIALS_DIR"] = tempfile.mkdtemp()
        self.addCleanup(lambda: os.environ.pop("LINKEDIN_CREDENTIALS_DIR", None))
        with self.assertRaises(LinkedInError) as ctx:
            load_credentials_dict(credentials_path="/etc/passwd")
        self.assertEqual(ctx.exception.error_code, "INVALID_CREDENTIALS")

    def test_token_alias(self):
        creds = load_credentials_dict(
            credentials_json=json.dumps({"token": "AQV.alias", "type": "oauth"})
        )
        self.assertEqual(creds["token"], "AQV.alias")


class TestHelpers(unittest.TestCase):
    def test_person_urn(self):
        self.assertEqual(person_urn_from_id("abc"), "urn:li:person:abc")
        self.assertEqual(
            person_urn_from_id("urn:li:person:abc"),
            "urn:li:person:abc",
        )

    def test_person_urn_rejects_org(self):
        with self.assertRaises(LinkedInValidationError):
            person_urn_from_id("urn:li:organization:1")
        with self.assertRaises(LinkedInValidationError):
            validate_person_urn("urn:li:organization:1")

    def test_post_urn(self):
        self.assertEqual(validate_post_urn("urn:li:share:1"), "urn:li:share:1")
        with self.assertRaises(LinkedInValidationError):
            validate_post_urn("urn:li:activity:1")

    def test_visibility(self):
        self.assertEqual(normalize_visibility("public"), "PUBLIC")
        self.assertEqual(normalize_visibility(None), "CONNECTIONS")
        self.assertEqual(normalize_visibility(""), "CONNECTIONS")
        with self.assertRaises(LinkedInValidationError):
            normalize_visibility("PRIVATE")

    def test_encode_urn(self):
        encoded = encode_urn("urn:li:ugcPost:123")
        self.assertIn("%3A", encoded)

    def test_article_https_only(self):
        self.assertTrue(validate_article_url("https://example.com/a").startswith("https"))
        with self.assertRaises(LinkedInValidationError):
            validate_article_url("http://example.com/a")

    def test_upload_host_allowlist(self):
        validate_upload_url("https://www.linkedin.com/upload")
        validate_upload_url("https://media.licdn.com/dms/upload")
        with self.assertRaises(LinkedInValidationError):
            validate_upload_url("https://evil.example/steal")

    def test_build_ugc_text_body(self):
        body = build_ugc_text_body(
            "urn:li:person:abc",
            "hello",
            visibility="PUBLIC",
        )
        self.assertEqual(body["author"], "urn:li:person:abc")


class TestCreateTextPost(unittest.TestCase):
    def setUp(self):
        ls._create_events.clear()

    def test_create_reads_restli_id_header(self):
        svc = LinkedInService(
            credentials_json=json.dumps({"type": "oauth", "access_token": "AQV.test"})
        )

        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_resp.content = b""
        mock_resp.headers = {"x-restli-id": "urn:li:share:99"}
        mock_resp.text = ""

        with patch.object(
            svc, "get_me", return_value={"person_urn": "urn:li:person:xyz"}
        ):
            with patch("app.services.linkedin_service.requests.request", return_value=mock_resp):
                result = svc.create_text_post("hello world", visibility="PUBLIC")
        self.assertEqual(result["post_urn"], "urn:li:share:99")

    def test_rejects_mismatched_author(self):
        svc = LinkedInService(
            credentials_json=json.dumps({"type": "oauth", "access_token": "AQV.test"})
        )
        with patch.object(
            svc, "get_me", return_value={"person_urn": "urn:li:person:xyz"}
        ):
            with self.assertRaises(LinkedInValidationError):
                svc.create_text_post(
                    "hi",
                    author_urn="urn:li:person:other",
                    dry_run=True,
                )

    def test_dry_run(self):
        svc = LinkedInService(
            credentials_json=json.dumps({"type": "oauth", "access_token": "AQV.test"})
        )
        with patch.object(
            svc, "get_me", return_value={"person_urn": "urn:li:person:xyz"}
        ):
            result = svc.create_text_post("hello", dry_run=True)
        self.assertTrue(result["dry_run"])
        self.assertIn("request_body", result)

    def test_rejects_oversize_text(self):
        os.environ["LINKEDIN_MAX_TEXT_CHARS"] = "5"
        self.addCleanup(lambda: os.environ.pop("LINKEDIN_MAX_TEXT_CHARS", None))
        svc = LinkedInService(
            credentials_json=json.dumps({"type": "oauth", "access_token": "AQV.test"})
        )
        with self.assertRaises(LinkedInValidationError):
            svc.create_text_post("too long for gate")

    def test_image_empty_rejected(self):
        svc = LinkedInService(
            credentials_json=json.dumps({"type": "oauth", "access_token": "AQV.test"})
        )
        with patch.object(
            svc, "get_me", return_value={"person_urn": "urn:li:person:xyz"}
        ):
            with self.assertRaises(LinkedInValidationError):
                svc.create_image_post("hi", image_base64="====")

    def test_image_size_gate(self):
        os.environ["LINKEDIN_MAX_IMAGE_BYTES"] = "10"
        self.addCleanup(lambda: os.environ.pop("LINKEDIN_MAX_IMAGE_BYTES", None))
        svc = LinkedInService(
            credentials_json=json.dumps({"type": "oauth", "access_token": "AQV.test"})
        )
        big = base64.b64encode(b"x" * 50).decode("ascii")
        with patch.object(
            svc, "get_me", return_value={"person_urn": "urn:li:person:xyz"}
        ):
            with self.assertRaises(LinkedInValidationError):
                svc.create_image_post("hi", image_base64=big)

    def test_invalid_expiry_fails_closed(self):
        with self.assertRaises(LinkedInError) as ctx:
            LinkedInService(
                credentials_json=json.dumps(
                    {
                        "type": "oauth",
                        "access_token": "AQV.test",
                        "expires_at": "not-a-date",
                    }
                )
            )
        self.assertEqual(ctx.exception.error_code, "INVALID_CREDENTIALS")


class TestCredsRequiredAtService(unittest.TestCase):
    def test_service_init_requires_creds(self):
        with self.assertRaises(LinkedInError) as ctx:
            LinkedInService()
        self.assertEqual(ctx.exception.error_code, "CREDENTIALS_REQUIRED")


if __name__ == "__main__":
    unittest.main()
