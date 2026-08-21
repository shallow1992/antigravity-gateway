"""Unit and integration tests for Web Dashboard and OAuth flow (Issue #12)."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

try:
    from aiohttp.test_utils import AioHTTPTestCase
    from src.web_server import (
        WebServerManager,
        get_auth_account_email,
        is_authenticated,
    )
    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False
    AioHTTPTestCase = unittest.TestCase


@unittest.skipUnless(HAS_AIOHTTP, "aiohttp is required for web dashboard test")
class TestWebServer(AioHTTPTestCase):
    async def get_application(self):
        self.server_manager = WebServerManager(
            host="127.0.0.1",
            port=8080,
            target_workspace="/tmp/test_workspace",
        )
        return self.server_manager.app

    def setUp(self):
        if not HAS_AIOHTTP:
            return
        super().setUp()
        self.test_dir = tempfile.TemporaryDirectory()
        self.mock_token_path = Path(self.test_dir.name) / "jetski-standalone-oauth-token"

    def tearDown(self):
        if not HAS_AIOHTTP:
            return
        super().tearDown()
        self.test_dir.cleanup()

    async def test_dashboard_unauthenticated(self):
        """Test dashboard renders unauthenticated state with login button."""
        with patch("src.web_server.get_token_storage_path", return_value=self.mock_token_path):
            resp = await self.client.get("/")
            self.assertEqual(resp.status, 200)
            text = await resp.text()
            self.assertIn("Antigravity Gateway 管理ダッシュボード", text)
            self.assertIn("未連携", text)
            self.assertIn("/auth/login", text)

    async def test_dashboard_authenticated(self):
        """Test dashboard renders connected status when token exists."""
        token_data = {
            "access_token": "valid_mock_access_token",
            "refresh_token": "valid_mock_refresh_token",
            "email": "developer@example.com",
        }
        self.mock_token_path.write_text(json.dumps(token_data), encoding="utf-8")

        with patch("src.web_server.get_token_storage_path", return_value=self.mock_token_path):
            self.assertTrue(is_authenticated())
            self.assertEqual(get_auth_account_email(), "developer@example.com")

            resp = await self.client.get("/")
            self.assertEqual(resp.status, 200)
            text = await resp.text()
            self.assertIn("Google Pro 連携中", text)
            self.assertIn("developer@example.com", text)
            self.assertIn("/auth/logout", text)

    async def test_auth_login_redirect(self):
        """Test /auth/login generates state and redirects to Google OAuth."""
        resp = await self.client.get("/auth/login", allow_redirects=False)
        self.assertEqual(resp.status, 302)
        location = resp.headers.get("Location", "")
        self.assertIn("accounts.google.com", location)
        self.assertIn("client_id=", location)
        self.assertIn("state=", location)
        self.assertEqual(len(self.server_manager._active_states), 1)

    async def test_auth_callback_invalid_state(self):
        """Test /auth/callback rejects invalid or expired state."""
        resp = await self.client.get("/auth/callback?code=mock_code&state=invalid_state", allow_redirects=False)
        self.assertEqual(resp.status, 302)
        location = resp.headers.get("Location", "")
        self.assertIn("alert=", location)

    async def test_auth_callback_success(self):
        """Test /auth/callback saves token with valid state."""
        state = "valid_test_state_12345"
        self.server_manager._active_states.add(state)

        with patch("src.web_server.get_token_storage_path", return_value=self.mock_token_path):
            resp = await self.client.get(f"/auth/callback?code=mock_auth_code&state={state}", allow_redirects=False)
            self.assertEqual(resp.status, 302)
            self.assertTrue(self.mock_token_path.exists())
            saved_data = json.loads(self.mock_token_path.read_text())
            self.assertIn("access_token", saved_data)

    async def test_auth_logout(self):
        """Test /auth/logout removes token file."""
        self.mock_token_path.write_text(json.dumps({"access_token": "token"}), encoding="utf-8")
        self.assertTrue(self.mock_token_path.exists())

        with patch("src.web_server.get_token_storage_path", return_value=self.mock_token_path):
            resp = await self.client.post("/auth/logout", allow_redirects=False)
            self.assertEqual(resp.status, 302)
            self.assertFalse(self.mock_token_path.exists())

    async def test_api_status_endpoint(self):
        """Test /api/status JSON endpoint."""
        with patch("src.web_server.get_token_storage_path", return_value=self.mock_token_path):
            resp = await self.client.get("/api/status")
            self.assertEqual(resp.status, 200)
            data = await resp.json()
            self.assertEqual(data["status"], "ok")
            self.assertEqual(data["workspace"], "/tmp/test_workspace")
            self.assertEqual(data["engine"], "agy_cli")


if __name__ == "__main__":
    unittest.main()
