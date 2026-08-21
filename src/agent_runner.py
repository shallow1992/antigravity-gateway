"""Antigravity CLI (agy) Wrapper Engine with Real-Time Streaming and Timeout (Issue #2, #8, #12).

Wraps the local 'agy' CLI / Google Pro authentication seamlessly to execute agent tasks
without incurring API key billing or strict rate limits.
"""

import asyncio
import logging
import os
import shutil
import time
from typing import Callable, Optional

from src.session import ConversationSession
from src.web_server import is_authenticated

logger = logging.getLogger("gateway.agent")


class AgentRunner:
    """Wrapper engine executing Antigravity CLI (agy) or SDK using local Google Pro authentication."""

    def __init__(self, settings):
        self.settings = settings
        self.timeout_sec = getattr(settings, "AGENT_TIMEOUT_SEC", 300)
        self.throttling_interval = getattr(settings, "THROTTLING_INTERVAL_SEC", 0.8)
        self.workspace_path = getattr(settings, "TARGET_WORKSPACE_PATH", "/workspace")

    def _build_full_prompt(self, current_prompt: str, session: ConversationSession) -> str:
        """Combine current prompt with previous conversation context."""
        history = session.get_formatted_history()
        if not history:
            return current_prompt

        return (
            "【これまでの会話履歴】\n"
            f"{history}\n\n"
            "【現在のユーザー指示】\n"
            f"{current_prompt}"
        )

    async def execute_prompt(
        self,
        prompt: str,
        session: ConversationSession,
        on_progress: Optional[Callable[[str], asyncio.Future]] = None,
    ) -> str:
        """Execute prompt via Antigravity CLI (agy) or internal runner with timeout and streaming updates."""
        # 1. Check Google Pro authentication status
        if not is_authenticated() and not os.environ.get("GEMINI_API_KEY"):
            return (
                "⚠️ *Google Pro アカウントの連携が必要です。*\n\n"
                "ブラウザで管理ダッシュボードを開き、連携を完了してください：\n"
                "👉 `http://localhost:8080`\n\n"
                "_（「Google アカウントでログイン」を押すだけで 1 クリックで完了します）_"
            )

        full_prompt = self._build_full_prompt(prompt, session)

        try:
            # Enforce max execution timeout (Issue #2)
            result = await asyncio.wait_for(
                self._execute_cli_or_internal(full_prompt, session, on_progress),
                timeout=self.timeout_sec,
            )
            return result
        except asyncio.TimeoutError:
            error_msg = f"Agent execution timed out after {self.timeout_sec} seconds"
            logger.error(error_msg)
            return f"⏱️ *タイムアウトエラー*: 処理が制限時間（{self.timeout_sec}秒）を超過したため安全に中断しました。"
        except Exception as e:
            logger.error(f"Unexpected error during agent execution: {e}", exc_info=True)
            return f"❌ *エージェント実行エラー*: {e}"

    async def _execute_cli_or_internal(
        self,
        full_prompt: str,
        session: ConversationSession,
        on_progress: Optional[Callable[[str], asyncio.Future]] = None,
    ) -> str:
        """Execute via 'agy' CLI if installed, or fallback to internal SDK/mock."""
        agy_bin = shutil.which("agy") or shutil.which("antigravity")

        if agy_bin:
            return await self._execute_agy_subprocess(agy_bin, full_prompt, on_progress)
        else:
            return await self._execute_agent_internal(full_prompt, session, on_progress)

    async def _execute_agy_subprocess(
        self,
        agy_path: str,
        prompt: str,
        on_progress: Optional[Callable[[str], asyncio.Future]] = None,
    ) -> str:
        """Run agy CLI as an asynchronous subprocess and stream stdout."""
        logger.info(f"🚀 Launching Antigravity CLI: {agy_path} (workspace: {self.workspace_path})")

        cmd = [
            agy_path,
            "--prompt", prompt,
            "--workspace", self.workspace_path,
        ]

        # Prepare execution environment ensuring token directory is visible
        proc_env = os.environ.copy()
        proc_env["PYTHONUNBUFFERED"] = "1"

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=proc_env,
            cwd=self.workspace_path if os.path.exists(self.workspace_path) else None,
        )

        collected_output = []
        last_update_time = 0.0

        try:
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                decoded_line = line.decode("utf-8", errors="replace")
                collected_output.append(decoded_line)

                now = time.time()
                if on_progress and (now - last_update_time >= self.throttling_interval):
                    current_preview = "".join(collected_output[-15:])
                    try:
                        await on_progress(f"🧠 *Antigravity 実行中...*\n```\n{current_preview}\n```")
                        last_update_time = now
                    except Exception as e:
                        logger.debug(f"Progress update skipped: {e}")

            await process.wait()
            stderr_output = (await process.stderr.read()).decode("utf-8", errors="replace")

            if process.returncode != 0 and not collected_output:
                logger.error(f"agy CLI failed (code {process.returncode}): {stderr_output}")
                return f"⚠️ *Antigravity CLI 実行エラー (Exit Code {process.returncode})*:\n```{stderr_output}```"

            return "".join(collected_output) or stderr_output or "（完了しました）"

        except asyncio.CancelledError:
            logger.info("Terminating agy subprocess due to cancellation/timeout...")
            try:
                process.terminate()
                await asyncio.sleep(0.5)
                if process.returncode is None:
                    process.kill()
            except Exception as e:
                logger.warning(f"Error killing agy subprocess: {e}")
            raise

    async def _execute_agent_internal(
        self,
        full_prompt: str,
        session: ConversationSession,
        on_progress: Optional[Callable[[str], asyncio.Future]] = None,
    ) -> str:
        """Fallback internal runner executing SDK or compatibility response."""
        try:
            import google.antigravity as agy

            logger.info("Executing via google.antigravity SDK...")
            if on_progress:
                await on_progress("🧠 *思考中 (Google Pro)...*")

            agent_config = agy.LocalAgentConfig(
                workspace_dir=self.workspace_path,
                capabilities=agy.CapabilitiesConfig(
                    file_read=self.settings.ALLOW_FILE_READ,
                    file_write=self.settings.ALLOW_FILE_WRITE,
                    run_command=self.settings.ALLOW_RUN_COMMAND,
                ),
            )
            agent = agy.Agent(config=agent_config)

            if hasattr(agent, "run_async"):
                response = await agent.run_async(full_prompt)
                return response.text if hasattr(response, "text") else str(response)
            elif hasattr(agent, "run"):
                response = agent.run(full_prompt)
                return response.text if hasattr(response, "text") else str(response)
            else:
                return f"（Mock Antigravity 応答 - Google Pro 認証モード）\n受信プロンプト: `{full_prompt}`"

        except (ImportError, AttributeError, Exception) as e:
            logger.warning(f"SDK internal execution fallback to mock: {e}")
            if on_progress:
                await on_progress("🧠 *Antigravity CLI 実行中 (Mock Mode)...*")
                await asyncio.sleep(0.05)
            return f"（Mock Antigravity 応答 - Google Pro 認証モード）\n受信プロンプト: `{full_prompt}`"
