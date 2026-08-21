"""Unit tests for Settings validation and edge cases (Issue #9)."""

import unittest

try:
    from pydantic import ValidationError
    from src.config import Settings
    HAS_PYDANTIC = True
except ImportError:
    HAS_PYDANTIC = False


class TestSettingsValidation(unittest.TestCase):
    @unittest.skipUnless(HAS_PYDANTIC, "pydantic is required for config validation test")
    def test_valid_settings(self):
        settings = Settings(
            SLACK_BOT_TOKEN="xoxb-valid-bot-token",
            SLACK_APP_TOKEN="xapp-valid-app-token",
            ALLOWED_USER_IDS=" U123 , U456 , U789 ",
            ALLOWED_CHANNEL_IDS=" C111 , C222 ",
            SESSION_MODE="thread",
        )
        self.assertEqual(settings.SLACK_BOT_TOKEN, "xoxb-valid-bot-token")
        self.assertEqual(settings.allowed_user_ids, {"U123", "U456", "U789"})
        self.assertEqual(settings.allowed_channel_ids, {"C111", "C222"})
        self.assertEqual(settings.SESSION_MODE, "thread")

    @unittest.skipUnless(HAS_PYDANTIC, "pydantic is required for config validation test")
    def test_missing_required_tokens_raises_error(self):
        with self.assertRaises(ValidationError):
            Settings(
                SLACK_BOT_TOKEN=None,  # Missing required
                SLACK_APP_TOKEN=None,
            )

    @unittest.skipUnless(HAS_PYDANTIC, "pydantic is required for config validation test")
    def test_invalid_session_mode_raises_error(self):
        with self.assertRaises(ValidationError):
            Settings(
                SLACK_BOT_TOKEN="xoxb-test",
                SLACK_APP_TOKEN="xapp-test",
                SESSION_MODE="invalid_mode",  # Invalid literal
            )

    @unittest.skipUnless(HAS_PYDANTIC, "pydantic is required for config validation test")
    def test_empty_whitelists(self):
        settings = Settings(
            SLACK_BOT_TOKEN="xoxb-test",
            SLACK_APP_TOKEN="xapp-test",
            ALLOWED_USER_IDS="",
            ALLOWED_CHANNEL_IDS="",
        )
        self.assertEqual(settings.allowed_user_ids, set())
        self.assertEqual(settings.allowed_channel_ids, set())


if __name__ == "__main__":
    unittest.main()
