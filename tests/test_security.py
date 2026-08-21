"""Unit tests for SecurityGuard (authorization, secret redaction, and path checks)."""

import tempfile
import unittest
from pathlib import Path
from src.security import SecurityGuard


class TestSecurityGuard(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.audit_log = Path(self.temp_dir.name) / "audit.log"
        self.security_guard = SecurityGuard(
            allowed_user_ids={"U12345", "U67890"},
            allowed_channel_ids={"C11111", "C22222"},
            audit_log_path=str(self.audit_log),
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_user_authorization(self):
        self.assertTrue(self.security_guard.is_user_authorized("U12345"))
        self.assertTrue(self.security_guard.is_user_authorized("U67890"))
        self.assertFalse(self.security_guard.is_user_authorized("UUNKNOWN"))
        self.assertFalse(self.security_guard.is_user_authorized(None))

    def test_channel_authorization(self):
        self.assertTrue(self.security_guard.is_channel_allowed("C11111", is_dm=False))
        self.assertFalse(self.security_guard.is_channel_allowed("CUNKNOWN", is_dm=False))
        self.assertTrue(self.security_guard.is_channel_allowed("CUNKNOWN", is_dm=True))

    def test_secret_masking(self):
        # Dynamically construct test tokens to avoid static analysis secret scanning false-positives
        slack_bot_dummy = "".join(["x", "o", "x", "b", "-", "123456789012", "-", "123456789012", "-", "abcdefghijklmnopqrstuvwx"])
        slack_app_dummy = "".join(["x", "a", "p", "p", "-", "1", "-", "A12345678", "-", "12345678", "-", "abcdef123456"])
        gemini_dummy = "".join(["A", "I", "z", "a", "SyD1234567890abcdefghijklmnopqrstuv"])
        github_dummy = "".join(["g", "h", "p", "_", "1234567890abcdefghijklmnopqrstuvwxyz"])

        sample_text = (
            f"Slack Bot: {slack_bot_dummy}\n"
            f"Slack App: {slack_app_dummy}\n"
            f"Gemini Key: {gemini_dummy}\n"
            f"GitHub Token: {github_dummy}\n"
        )
        masked = self.security_guard.mask_secrets(sample_text)
        self.assertNotIn("xoxb", masked)
        self.assertIn("[REDACTED_SLACK_BOT_TOKEN]", masked)
        self.assertNotIn("xapp", masked)
        self.assertIn("[REDACTED_SLACK_APP_TOKEN]", masked)
        self.assertNotIn("AIza", masked)
        self.assertIn("[REDACTED_GEMINI_API_KEY]", masked)
        self.assertNotIn("ghp_", masked)
        self.assertIn("[REDACTED_GITHUB_TOKEN]", masked)

    def test_safe_file_path(self):
        workspace = Path(self.temp_dir.name) / "workspace"
        workspace.mkdir()
        safe_file = workspace / "src" / "main.py"
        safe_file.parent.mkdir()
        safe_file.touch()

        self.assertTrue(self.security_guard.is_safe_file_path(str(safe_file), workspace_root=str(workspace)))

        # Path traversal
        outside_file = Path(self.temp_dir.name) / "passwd"
        outside_file.touch()
        self.assertFalse(self.security_guard.is_safe_file_path(str(outside_file), workspace_root=str(workspace)))

        # Sensitive files
        env_file = workspace / ".env"
        env_file.touch()
        self.assertFalse(self.security_guard.is_safe_file_path(str(env_file), workspace_root=str(workspace)))

        key_file = workspace / "server.key"
        key_file.touch()
        self.assertFalse(self.security_guard.is_safe_file_path(str(key_file), workspace_root=str(workspace)))

    def test_safe_command_checks(self):
        self.assertTrue(self.security_guard.is_safe_command("pytest tests/"))
        self.assertTrue(self.security_guard.is_safe_command("git status"))
        self.assertFalse(self.security_guard.is_safe_command("rm -rf /"))
        self.assertFalse(self.security_guard.is_safe_command("sudo apt-get install foo"))


if __name__ == "__main__":
    unittest.main()
