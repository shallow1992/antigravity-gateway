"""Unit tests for AgentRunner (Issue #8 execution, history context, progress, and timeouts)."""

import asyncio
import unittest
from types import SimpleNamespace
from src.agent_runner import AgentRunner
from src.session import ConversationSession


class TestAgentRunner(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.mock_settings = SimpleNamespace(
            TARGET_WORKSPACE_PATH="/tmp/workspace",
            THROTTLING_INTERVAL_SEC=0.1,
            AGENT_TIMEOUT_SEC=5,
            ALLOW_FILE_READ=True,
            ALLOW_FILE_WRITE=False,
            ALLOW_RUN_COMMAND=False,
        )
        self.runner = AgentRunner(self.mock_settings)

    async def test_execute_prompt_mock(self):
        # Mock internal execution to avoid requiring real GEMINI_API_KEY in CI
        async def _mock_internal(full_prompt, session, on_progress=None):
            if on_progress:
                await on_progress("🧠 *思考中...*")
            return f"（Mock Antigravity 応答）\n受信プロンプト: `{full_prompt}`"

        self.runner._execute_agent_internal = _mock_internal

        session = ConversationSession(
            session_key="C123:1111",
            channel_id="C123",
            thread_ts="1111",
            user_id="U123",
        )
        progress_updates = []

        async def _progress_cb(text: str):
            progress_updates.append(text)

        result = await self.runner.execute_prompt(
            prompt="Hello agent",
            session=session,
            on_progress=_progress_cb,
        )

        self.assertIn("Hello agent", result)
        self.assertGreater(len(progress_updates), 0)

    def test_build_prompt_with_history(self):
        session = ConversationSession(
            session_key="C123:1111",
            channel_id="C123",
            thread_ts="1111",
            user_id="U123",
        )
        session.add_user_message("First question")
        session.add_assistant_message("First answer")

        full_prompt = self.runner._build_prompt_with_history("Second question", session)
        self.assertIn("[Previous Conversation Context]", full_prompt)
        self.assertIn("User: First question", full_prompt)
        self.assertIn("Assistant: First answer", full_prompt)
        self.assertIn("[Current User Prompt]\nSecond question", full_prompt)

    async def test_timeout_enforcement(self):
        timeout_settings = SimpleNamespace(
            TARGET_WORKSPACE_PATH="/tmp/workspace",
            THROTTLING_INTERVAL_SEC=0.1,
            AGENT_TIMEOUT_SEC=0.001,
            ALLOW_FILE_READ=True,
            ALLOW_FILE_WRITE=False,
            ALLOW_RUN_COMMAND=False,
        )
        runner_with_timeout = AgentRunner(timeout_settings)

        async def _slow_agent(*args, **kwargs):
            await asyncio.sleep(0.1)
            return "Done"

        runner_with_timeout._execute_agent_internal = _slow_agent

        session = ConversationSession(
            session_key="C123:1111",
            channel_id="C123",
            thread_ts="1111",
            user_id="U123",
        )

        result = await runner_with_timeout.execute_prompt("Slow task", session)
        self.assertIn("タイムアウトしました", result)


if __name__ == "__main__":
    unittest.main()
