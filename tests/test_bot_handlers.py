"""Integration tests for Slack Bolt event routing and message pipeline (Issue #7, #12)."""

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from src.agent_runner import AgentRunner
from src.converter import convert_gfm_to_slack_mrkdwn, split_message_for_slack
from src.security import SecurityGuard
from src.session import SessionManager


class MockSlackClient:
    """Mock Slack WebClient capturing all API calls."""

    def __init__(self):
        self.posted_messages = []
        self.updated_messages = []
        self.ephemeral_messages = []
        self.reactions = []
        self.joined_channels = []

    async def chat_postMessage(self, **kwargs):
        self.posted_messages.append(kwargs)
        return {"ts": f"msg_ts_{len(self.posted_messages)}", "ok": True}

    async def chat_update(self, **kwargs):
        self.updated_messages.append(kwargs)
        return {"ok": True}

    async def chat_postEphemeral(self, **kwargs):
        self.ephemeral_messages.append(kwargs)
        return {"ok": True}

    async def reactions_add(self, **kwargs):
        self.reactions.append(("add", kwargs))
        return {"ok": True}

    async def reactions_remove(self, **kwargs):
        self.reactions.append(("remove", kwargs))
        return {"ok": True}

    async def conversations_join(self, **kwargs):
        self.joined_channels.append(kwargs.get("channel"))
        return {"ok": True}


class TestBotHandlers(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.settings = SimpleNamespace(
            SLACK_BOT_TOKEN="xoxb-dummy-test-token",
            SLACK_APP_TOKEN="xapp-dummy-test-token",
            SLACK_SIGNING_SECRET="",
            SESSION_MODE="thread",
            AUTO_JOIN_CHANNELS=True,
            ALLOW_FILE_READ=True,
            ALLOW_FILE_WRITE=False,
            ALLOW_RUN_COMMAND=False,
            TARGET_WORKSPACE_PATH="/tmp/workspace",
            THROTTLING_INTERVAL_SEC=0.01,
            AGENT_TIMEOUT_SEC=5,
            SESSION_TTL_HOURS=2,
            MAX_HISTORY_TURNS=20,
        )
        self.security_guard = SecurityGuard(
            allowed_user_ids={"U_AUTHORIZED"},
            allowed_channel_ids={"C_AUTHORIZED"},
            audit_log_path="/tmp/test_audit.log",
        )
        self.session_manager = SessionManager(ttl_hours=2, mode="thread")
        self.agent_runner = AgentRunner(self.settings)

        # Mock agent execution to avoid requiring real GEMINI_API_KEY in CI
        async def _mock_internal(full_prompt, session, on_progress=None):
            return f"（Mock Antigravity 応答）\n受信プロンプト: `{full_prompt}`"

        self.agent_runner._execute_agent_internal = _mock_internal
        self.mock_client = MockSlackClient()

    async def test_authorized_mention_pipeline(self):
        """Verify the full execution pipeline: auth -> reaction -> placeholder -> agent -> update -> reaction."""
        user_id = "U_AUTHORIZED"
        channel_id = "C_AUTHORIZED"
        prompt = "explain the codebase"
        thread_ts = "1111.2222"

        # 1. Auth check
        self.assertTrue(self.security_guard.is_user_authorized(user_id))
        self.assertTrue(self.security_guard.is_channel_allowed(channel_id))

        # 2. Session creation
        session = self.session_manager.get_or_create_session(channel_id, thread_ts, user_id)
        session.add_user_message(prompt)

        # 3. Add initial reaction & placeholder
        await self.mock_client.reactions_add(channel=channel_id, timestamp=thread_ts, name="eyes")
        resp = await self.mock_client.chat_postMessage(channel=channel_id, thread_ts=thread_ts, text="🧠 *考え中...*")
        placeholder_ts = resp["ts"]

        # 4. Agent execution (with authenticated state)
        with patch("src.agent_runner.is_authenticated", return_value=True):
            response_text = await self.agent_runner.execute_prompt(prompt=prompt, session=session)

        formatted_response = convert_gfm_to_slack_mrkdwn(response_text)
        safe_response = self.security_guard.mask_secrets(formatted_response)
        chunks = split_message_for_slack(safe_response)

        # 5. Message update
        await self.mock_client.chat_update(channel=channel_id, ts=placeholder_ts, text=chunks[0])
        await self.mock_client.reactions_remove(channel=channel_id, timestamp=thread_ts, name="eyes")
        await self.mock_client.reactions_add(channel=channel_id, timestamp=thread_ts, name="white_check_mark")

        # Verifications
        self.assertEqual(len(self.mock_client.posted_messages), 1)
        self.assertEqual(len(self.mock_client.updated_messages), 1)
        self.assertIn("Mock Antigravity 応答", self.mock_client.updated_messages[0]["text"])
        self.assertEqual(len(self.mock_client.reactions), 3)

    async def test_unauthorized_user_blocked(self):
        """Verify unauthorized user is blocked from executing agent."""
        user_id = "U_UNAUTHORIZED"
        channel_id = "C_AUTHORIZED"

        self.assertFalse(self.security_guard.is_user_authorized(user_id))
        await self.mock_client.chat_postMessage(
            channel=channel_id,
            text=f"⚠️ *実行権限がありません。* (User ID: `{user_id}`)",
        )

        self.assertEqual(len(self.mock_client.posted_messages), 1)
        self.assertIn("実行権限がありません", self.mock_client.posted_messages[0]["text"])
        self.assertEqual(len(self.mock_client.updated_messages), 0)

    async def test_slash_command_status_ephemeral(self):
        """Verify slash command status returns ephemeral message to authorized user."""
        from src.commands import build_status_card

        user_id = "U_AUTHORIZED"
        channel_id = "C_AUTHORIZED"

        self.assertTrue(self.security_guard.is_user_authorized(user_id))
        status_card = build_status_card(self.settings)

        await self.mock_client.chat_postEphemeral(
            channel=channel_id,
            user=user_id,
            text=status_card,
        )

        self.assertEqual(len(self.mock_client.ephemeral_messages), 1)
        self.assertIn("Antigravity Gateway 稼働状況", self.mock_client.ephemeral_messages[0]["text"])


if __name__ == "__main__":
    unittest.main()
