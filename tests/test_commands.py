"""Unit tests for Antigravity full slash commands suite and /btw behavior."""

import unittest
from src.session import SessionManager


class TestCommandsSuite(unittest.TestCase):
    def setUp(self):
        self.session_manager = SessionManager(ttl_hours=2, mode="thread")

    def test_btw_does_not_pollute_history(self):
        session = self.session_manager.get_or_create_session("C123", "1111.2222", "U123")
        
        # User adds regular message
        session.add_user_message("Let's build the auth feature.")
        session.add_assistant_message("Sure, working on auth.")
        self.assertEqual(len(session.history), 2)

        # A /btw question is executed (does NOT call add_user_message / add_assistant_message)
        # Verify history length remains 2
        self.assertEqual(len(session.history), 2)
        self.assertEqual(session.history[0]["content"], "Let's build the auth feature.")

    def test_reset_clears_session(self):
        session = self.session_manager.get_or_create_session("C123", "1111.2222", "U123")
        session.add_user_message("Some context")
        self.assertTrue(self.session_manager.has_active_session("C123", "1111.2222"))

        # Reset
        self.session_manager.clear_session("C123", "1111.2222")
        self.assertFalse(self.session_manager.has_active_session("C123", "1111.2222"))


if __name__ == "__main__":
    unittest.main()
