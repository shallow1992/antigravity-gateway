"""Integration tests for Slack Bolt event handlers and slash commands (Issue #7)."""

import inspect
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

try:
    from src.bot import create_app
    HAS_SLACK_BOLT = True
except ImportError:
    HAS_SLACK_BOLT = False

from src.agent_runner import AgentRunner
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

    async def _invoke_matching_listener(self, app, keyword, **kwargs):
        """Helper to find and invoke the matching AsyncApp listener function."""
        listeners = getattr(app, "_async_listeners", getattr(app, "_listeners", []))
        for listener in listeners:
            matchers_str = str(getattr(listener, "matchers", []))
            if keyword in matchers_str or keyword in str(getattr(listener, "pattern", "")):
                func = getattr(listener, "ack_function", None)
                if not func and hasattr(listener, "lazy_functions") and listener.lazy_functions:
                    func = listener.lazy_functions[0]
                if not func and hasattr(listener, "handler"):
                    func = listener.handler
                if func:
                    sig = inspect.signature(func)
                    call_kwargs = {k: v for k, v in kwargs.items() if k in sig.parameters}
                    res = func(**call_kwargs)
                    if inspect.isawaitable(res):
                        await res
                    return True
        return False

    @unittest.skipUnless(HAS_SLACK_BOLT, "slack_bolt is required for app integration test")
    async def test_authorized_mention_flow(self):
        app = create_app(
            settings=self.settings,
            security_guard=self.security_guard,
            session_manager=self.session_manager,
            agent_runner=self.agent_runner,
        )
        mock_client = MockSlackClient()
        event = {
            "user": "U_AUTHORIZED",
            "channel": "C_AUTHORIZED",
            "text": "<@U_BOT> explain the codebase",
            "ts": "1111.2222",
        }

        invoked = await self._invoke_matching_listener(
            app=app,
            keyword="app_mention",
            event=event,
            client=mock_client,
            body={"event": event},
        )
        self.assertTrue(invoked)
        self.assertGreater(len(mock_client.posted_messages), 0)
        self.assertGreater(len(mock_client.updated_messages), 0)
        final_update = mock_client.updated_messages[-1]["text"]
        self.assertIn("Mock Antigravity 応答", final_update)

    @unittest.skipUnless(HAS_SLACK_BOLT, "slack_bolt is required for app integration test")
    async def test_unauthorized_user_blocked(self):
        app = create_app(
            settings=self.settings,
            security_guard=self.security_guard,
            session_manager=self.session_manager,
            agent_runner=self.agent_runner,
        )
        mock_client = MockSlackClient()
        event = {
            "user": "U_UNAUTHORIZED",
            "channel": "C_AUTHORIZED",
            "text": "<@U_BOT> secret request",
            "ts": "1111.3333",
        }

        invoked = await self._invoke_matching_listener(
            app=app,
            keyword="app_mention",
            event=event,
            client=mock_client,
            body={"event": event},
        )
        self.assertTrue(invoked)
        self.assertEqual(len(mock_client.updated_messages), 0)
        self.assertIn("実行権限がありません", mock_client.posted_messages[0]["text"])

    @unittest.skipUnless(HAS_SLACK_BOLT, "slack_bolt is required for app integration test")
    async def test_slash_command_status(self):
        app = create_app(
            settings=self.settings,
            security_guard=self.security_guard,
            session_manager=self.session_manager,
            agent_runner=self.agent_runner,
        )
        mock_client = MockSlackClient()
        command = {
            "user_id": "U_AUTHORIZED",
            "channel_id": "C_AUTHORIZED",
            "text": "status",
        }
        ack = AsyncMock()

        invoked = await self._invoke_matching_listener(
            app=app,
            keyword="/agy",
            ack=ack,
            command=command,
            client=mock_client,
            body=command,
        )
        self.assertTrue(invoked)
        ack.assert_awaited_once()
        self.assertEqual(len(mock_client.ephemeral_messages), 1)
        self.assertIn("Antigravity Gateway 稼働状況", mock_client.ephemeral_messages[0]["text"])


if __name__ == "__main__":
    unittest.main()
