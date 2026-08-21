"""Unit tests for Antigravity CLI (agy) AgentRunner (Issue #2, #8, #12)."""

import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from src.agent_runner import AgentRunner
from src.session import ConversationSession


class TestAgentRunner(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.settings = SimpleNamespace(
            AGENT_TIMEOUT_SEC=0.1,
            THROTTLING_INTERVAL_SEC=0.01,
            TARGET_WORKSPACE_PATH="/tmp/workspace",
            ALLOW_FILE_READ=True,
            ALLOW_FILE_WRITE=True,
            ALLOW_RUN_COMMAND=True,
        )
        self.runner = AgentRunner(self.settings)
        self.session = ConversationSession(
            session_key="test_channel:1234.5678",
            channel_id="test_channel",
            thread_ts="1234.5678",
            user_id="U12345",
        )

    def test_build_prompt_with_history(self):
        """Test prompt concatenation with history context."""
        self.session.add_user_message("前回の質問")
        self.session.add_assistant_message("前回の回答")

        full_prompt = self.runner._build_full_prompt("今回の指示", self.session)
        self.assertIn("【これまでの会話履歴】", full_prompt)
        self.assertIn("user: 前回の質問", full_prompt)
        self.assertIn("assistant: 前回の回答", full_prompt)
        self.assertIn("【現在のユーザー指示】\n今回の指示", full_prompt)

    async def test_unauthenticated_guidance_message(self):
        """Test runner returns web dashboard guidance when not authenticated."""
        with patch("src.agent_runner.is_authenticated", return_value=False):
            with patch.dict("os.environ", {}, clear=True):
                result = await self.runner.execute_prompt("test", self.session)
                self.assertIn("Google Pro アカウントの連携が必要です", result)
                self.assertIn("http://localhost:8080", result)

    async def test_execute_prompt_mock(self):
        """Test successful execution with progress streaming."""
        progress_updates = []

        async def _progress_cb(text):
            progress_updates.append(text)

        with patch("src.agent_runner.is_authenticated", return_value=True):
            result = await self.runner.execute_prompt(
                prompt="test prompt",
                session=self.session,
                on_progress=_progress_cb,
            )

        self.assertIn("Mock Antigravity 応答", result)

    async def test_timeout_enforcement(self):
        """Test that agent execution strictly terminates upon reaching AGENT_TIMEOUT_SEC."""
        async def _slow_agent(full_prompt, session, on_progress=None):
            await asyncio.sleep(0.5)
            return "Too late"

        self.runner._execute_agent_internal = _slow_agent

        with patch("src.agent_runner.is_authenticated", return_value=True):
            result = await self.runner.execute_prompt(
                prompt="hang prompt",
                session=self.session,
            )

        self.assertIn("タイムアウトエラー", result)
        self.assertIn("0.1秒", result)


if __name__ == "__main__":
    unittest.main()
