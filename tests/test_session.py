"""Unit tests for SessionManager (supporting thread-scoped and channel-scoped modes)."""

import unittest
from datetime import datetime, timedelta
from src.session import ConversationSession, SessionManager


class TestSessionManager(unittest.TestCase):
    def test_thread_mode(self):
        manager = SessionManager(ttl_hours=2, mode="thread")
        session1 = manager.get_or_create_session("C123", "1111.2222", "U123")
        session2 = manager.get_or_create_session("C123", "3333.4444", "U123")

        # Two different threads should have different sessions
        self.assertNotEqual(session1.session_key, session2.session_key)
        self.assertEqual(session1.session_key, "C123:1111.2222")
        self.assertEqual(session2.session_key, "C123:3333.4444")

    def test_channel_mode(self):
        manager = SessionManager(ttl_hours=2, mode="channel")
        session1 = manager.get_or_create_session("C123", "1111.2222", "U123")
        session2 = manager.get_or_create_session("C123", "3333.4444", "U123")

        # In channel mode, both share the same channel session
        self.assertEqual(session1.session_key, "C123")
        self.assertEqual(session2.session_key, "C123")
        self.assertEqual(session1, session2)

    def test_message_history(self):
        manager = SessionManager(ttl_hours=2, mode="thread")
        session = manager.get_or_create_session("C123", "1111.2222", "U123")
        session.add_user_message("Hello")
        session.add_assistant_message("Hi there!")

        self.assertEqual(len(session.history), 2)
        self.assertEqual(session.history[0], {"role": "user", "content": "Hello"})
        self.assertEqual(session.history[1], {"role": "assistant", "content": "Hi there!"})

    def test_clear_session(self):
        manager = SessionManager(ttl_hours=2, mode="thread")
        manager.get_or_create_session("C123", "1111.2222", "U123")
        self.assertTrue(manager.has_active_session("C123", "1111.2222"))

        cleared = manager.clear_session("C123", "1111.2222")
        self.assertTrue(cleared)
        self.assertFalse(manager.has_active_session("C123", "1111.2222"))

    def test_ttl_expiration(self):
        manager = SessionManager(ttl_hours=2, mode="thread")
        session = manager.get_or_create_session("C123", "1111.2222", "U123")
        # Artificially age the session past 2 hours
        session.last_active_at = datetime.utcnow() - timedelta(hours=3)

        self.assertIsNone(manager.get_session("C123", "1111.2222"))
        self.assertFalse(manager.has_active_session("C123", "1111.2222"))


if __name__ == "__main__":
    unittest.main()
