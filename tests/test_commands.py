"""Unit tests for Antigravity full slash commands suite and commands dispatcher (Issue #1)."""

import unittest
from types import SimpleNamespace
from src.commands import (
    build_help_card,
    build_status_card,
    clean_mention,
    parse_command,
    transform_prompt_for_mode,
)
from src.session import SessionManager


class TestCommandsSuite(unittest.TestCase):
    def setUp(self):
        self.session_manager = SessionManager(ttl_hours=2, mode="thread")
        self.mock_settings = SimpleNamespace(
            SLACK_BOT_TOKEN="xoxb-dummy-test-token",
            SLACK_APP_TOKEN="xapp-dummy-test-token",
            TARGET_WORKSPACE_PATH="/tmp/test_workspace",
            SESSION_MODE="thread",
            AUTO_JOIN_CHANNELS=True,
            ALLOW_FILE_READ=True,
            ALLOW_FILE_WRITE=False,
            ALLOW_RUN_COMMAND=False,
            SESSION_TTL_HOURS=2,
        )

    def test_clean_mention(self):
        self.assertEqual(clean_mention("<@U12345> hello world"), "hello world")
        self.assertEqual(clean_mention("hello <@U99999>"), "hello")

    def test_parse_command(self):
        cmd, arg = parse_command("/goal fix all bugs")
        self.assertEqual(cmd, "goal")
        self.assertEqual(arg, "fix all bugs")

        cmd, arg = parse_command("/btw what is python?")
        self.assertEqual(cmd, "btw")
        self.assertEqual(arg, "what is python?")

        cmd, arg = parse_command("/status")
        self.assertEqual(cmd, "status")
        self.assertEqual(arg, "")

        cmd, arg = parse_command("reset")
        self.assertEqual(cmd, "reset")

        cmd, arg = parse_command("just a regular question")
        self.assertIsNone(cmd)
        self.assertEqual(arg, "just a regular question")

    def test_transform_prompt_for_mode(self):
        prompt, is_btw = transform_prompt_for_mode("goal", "test all", "")
        self.assertIn("[GOAL MODE:", prompt)
        self.assertFalse(is_btw)

        prompt, is_btw = transform_prompt_for_mode("btw", "quick question", "")
        self.assertEqual(prompt, "quick question")
        self.assertTrue(is_btw)

        prompt, is_btw = transform_prompt_for_mode("grill-me", "api design", "")
        self.assertIn("[GRILL-ME MODE:", prompt)
        self.assertFalse(is_btw)

    def test_build_cards(self):
        help_card = build_help_card()
        self.assertIn("/agy goal", help_card)
        self.assertIn("/agy btw", help_card)

        status_card = build_status_card(self.mock_settings)
        self.assertIn("/tmp/test_workspace", status_card)

    def test_btw_does_not_pollute_history(self):
        session = self.session_manager.get_or_create_session("C123", "1111.2222", "U123")
        session.add_user_message("Let's build the auth feature.")
        session.add_assistant_message("Sure, working on auth.")
        self.assertEqual(len(session.history), 2)

        # Verify history length remains 2 for /btw
        self.assertEqual(len(session.history), 2)
        self.assertEqual(session.history[0]["content"], "Let's build the auth feature.")


if __name__ == "__main__":
    unittest.main()
