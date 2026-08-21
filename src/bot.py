"""Slack Bolt AsyncApp definition and event routing with full Antigravity slash commands suite."""

import logging
import os
import re
import subprocess
from typing import Any, Dict, Optional, Tuple
from slack_bolt.async_app import AsyncApp
from slack_sdk.errors import SlackApiError

from src.agent_runner import AgentRunner
from src.config import Settings
from src.converter import convert_gfm_to_slack_mrkdwn, split_message_for_slack
from src.security import SecurityGuard
from src.session import ConversationSession, SessionManager

logger = logging.getLogger("gateway.bot")


def _get_git_branch(workspace_path: str) -> str:
    """Helper to get current git branch of target workspace."""
    try:
        res = subprocess.run(
            ["git", "-C", workspace_path, "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if res.returncode == 0:
            return res.stdout.strip()
    except Exception:
        pass
    return "unknown"


def create_app(
    settings: Settings,
    security_guard: SecurityGuard,
    session_manager: SessionManager,
    agent_runner: AgentRunner,
) -> AsyncApp:
    """Initialize and configure the Slack Bolt AsyncApp with full Antigravity command support."""

    app = AsyncApp(
        token=settings.SLACK_BOT_TOKEN,
        signing_secret=settings.SLACK_SIGNING_SECRET or None,
    )

    # Helper: clean mention text
    def _clean_prompt(text: str) -> str:
        return re.sub(r"<@[A-Z0-9]+>", "", text).strip()

    # Helper: auto join channel if needed
    async def _ensure_channel_joined(client: Any, channel_id: str):
        if not settings.AUTO_JOIN_CHANNELS:
            return
        try:
            await client.conversations_join(channel=channel_id)
            logger.info(f"Auto-joined channel: {channel_id}")
        except SlackApiError as e:
            logger.debug(f"Channel join status for {channel_id}: {e.response.get('error')}")

    # =========================================================================
    # Command Dispatcher Core
    # =========================================================================

    def _parse_command(raw_text: str) -> Tuple[Optional[str], str]:
        """Parse raw text to extract command name (e.g. 'goal', 'btw', 'reset') and remaining argument."""
        text = _clean_prompt(raw_text).strip()
        if not text.startswith("/"):
            # Check if first word matches a known command
            parts = text.split(maxsplit=1)
            if parts and parts[0].lower() in (
                "reset", "clear", "status", "help", "btw", "goal",
                "schedule", "browser", "grill-me", "teamwork", "learn",
                "guide", "customs"
            ):
                cmd = parts[0].lower()
                arg = parts[1].strip() if len(parts) > 1 else ""
                return cmd, arg
            return None, text

        # Strips leading '/'
        command_line = text[1:].strip()
        parts = command_line.split(maxsplit=1)
        cmd = parts[0].lower() if parts else ""
        arg = parts[1].strip() if len(parts) > 1 else ""
        return cmd, arg

    def _build_help_card() -> str:
        return (
            "🏛️ *Antigravity 公式スラッシュコマンド一覧*\n\n"
            "*【コア制御】*\n"
            "• `/agy reset` / `/agy clear` : 会話セッション履歴を初期化\n"
            "• `/agy status` : 稼働状況、Gitブランチ、権限の確認\n"
            "• `/agy btw <質問>` : メインの会話履歴を汚さずに単発で質問に回答\n"
            "• `/agy help` : このヘルプを表示\n\n"
            "*【公式エージェントワークフロー】*\n"
            "• `/agy goal <目標>` : ゴール達成まで自律的にツールを実行・完遂\n"
            "• `/agy grill-me <テーマ>` : 設計・実装プランを詰める壁打ちインタビュー\n"
            "• `/agy browser <URL/指示>` : Webページ調査・ブラウザ自動化\n"
            "• `/agy teamwork <タスク>` : 複数エージェント協調による大規模タスク実行\n"
            "• `/agy schedule <指示>` : タイマー・定期実行タスクの登録\n"
            "• `/agy learn` : 直前の修正・成功からルールを抽出して永続化\n"
            "• `/agy guide` : 公式ガイド・リファレンスの確認\n"
            "• `/agy customs` : カスタマイズ仕様（Skills/Rules/Hooks）の確認\n\n"
            "_※ `/antigravity <command>` でも同様に実行できます。_"
        )

    def _build_status_card() -> str:
        branch = _get_git_branch(settings.TARGET_WORKSPACE_PATH)
        return (
            "📊 *Antigravity Gateway 稼働状況*\n"
            f"• *作業リポジトリ:* `{settings.TARGET_WORKSPACE_PATH}`\n"
            f"• *Git ブランチ:* `{branch}`\n"
            f"• *セッションモード:* `{settings.SESSION_MODE.upper()}`\n"
            f"• *自動チャンネル参加:* `{'有効' if settings.AUTO_JOIN_CHANNELS else '無効'}`\n"
            f"• *実行権限 (Capabilities):* 読込=`{settings.ALLOW_FILE_READ}` / 書込=`{settings.ALLOW_FILE_WRITE}` / コマンド=`{settings.ALLOW_RUN_COMMAND}`\n"
            f"• *セッション有効期限:* `{settings.SESSION_TTL_HOURS} 時間`"
        )

    # Core processing pipeline
    async def _handle_user_prompt(
        client: Any,
        channel_id: str,
        thread_ts: Optional[str],
        user_id: str,
        raw_text: str,
        message_ts: Optional[str] = None,
        is_ephemeral: bool = False,
    ) -> None:
        effective_thread_ts = thread_ts if settings.SESSION_MODE == "thread" else thread_ts
        cmd, arg = _parse_command(raw_text)

        # 1. Core Control Commands
        if cmd in ("reset", "clear"):
            session_manager.clear_session(channel_id, effective_thread_ts)
            await client.chat_postMessage(
                channel=channel_id,
                thread_ts=effective_thread_ts,
                text="🧹 *会話コンテキストをリセットしました。* 新しい質問をどうぞ！",
            )
            return

        if cmd == "status":
            await client.chat_postMessage(
                channel=channel_id,
                thread_ts=effective_thread_ts,
                text=_build_status_card(),
            )
            return

        if cmd in ("help", "guide"):
            await client.chat_postMessage(
                channel=channel_id,
                thread_ts=effective_thread_ts,
                text=_build_help_card(),
            )
            return

        # 2. Side-question Command (/btw) - does NOT pollute session history
        is_btw = (cmd == "btw")
        actual_prompt = arg if cmd else raw_text
        actual_prompt = _clean_prompt(actual_prompt)

        if not actual_prompt:
            await client.chat_postMessage(
                channel=channel_id,
                thread_ts=effective_thread_ts,
                text="👋 こんにちは！何か質問や依頼があれば入力してください。\nヒント: `/agy help` で全コマンドを確認できます。",
            )
            return

        # Wrap prompt if specialized mode command is invoked
        if cmd == "goal":
            actual_prompt = f"[GOAL MODE: Run until the specified goal is completely finished]\n{actual_prompt}"
        elif cmd == "grill-me":
            actual_prompt = f"[GRILL-ME MODE: Interview the user to align on and refine the plan]\n{actual_prompt}"
        elif cmd == "browser":
            actual_prompt = f"[BROWSER MODE: Invoke browser tools for web inspection and tasks]\n{actual_prompt}"
        elif cmd == "teamwork":
            actual_prompt = f"[TEAMWORK MODE: Coordinate subagents to tackle the task concurrently]\n{actual_prompt}"
        elif cmd == "schedule":
            actual_prompt = f"[SCHEDULE MODE: Set up recurring schedule or one-time timer]\n{actual_prompt}"
        elif cmd == "learn":
            actual_prompt = "[LEARN MODE: Reflect on recent successes or corrections to capture reusable rules/skills]"
        elif cmd == "customs":
            actual_prompt = "Explain the Antigravity Customization System (Skills, Rules, Hooks, MCP) and how to configure them."

        # 3. Session handling
        session = session_manager.get_or_create_session(channel_id, effective_thread_ts, user_id)
        if not is_btw:
            session.add_user_message(actual_prompt)

        # 4. Reaction and Placeholder
        target_ts = message_ts or thread_ts
        if target_ts:
            try:
                await client.reactions_add(
                    channel=channel_id,
                    timestamp=target_ts,
                    name="eyes",
                )
            except SlackApiError as e:
                logger.debug(f"Could not add reaction: {e}")

        placeholder_ts: Optional[str] = None
        prefix_title = f"💬 *[BTW]* " if is_btw else "🧠 "
        try:
            resp = await client.chat_postMessage(
                channel=channel_id,
                thread_ts=effective_thread_ts,
                text=f"{prefix_title}*考え中... (準備中)*",
            )
            placeholder_ts = resp["ts"]
        except SlackApiError as e:
            logger.error(f"Failed to post placeholder message: {e}")

        async def _update_progress(status_text: str):
            if placeholder_ts:
                try:
                    await client.chat_update(
                        channel=channel_id,
                        ts=placeholder_ts,
                        text=status_text,
                    )
                except SlackApiError as e:
                    logger.debug(f"Failed to update progress: {e}")

        # 5. Execute Agent
        error_occurred = False
        try:
            response_text = await agent_runner.execute_prompt(
                prompt=actual_prompt,
                session=session,
                on_progress=_update_progress,
            )
            if not is_btw:
                session.add_assistant_message(response_text)
            security_guard.record_audit_log(
                user_id=user_id,
                channel_id=channel_id,
                thread_ts=effective_thread_ts,
                action=f"execute_{cmd or 'prompt'}_success",
                details={"prompt_len": len(actual_prompt), "response_len": len(response_text), "is_btw": is_btw},
            )
        except Exception as e:
            logger.error(f"Agent execution failed: {e}", exc_info=True)
            response_text = f"⚠️ *処理中にエラーが発生しました:*\n```{str(e)}```"
            error_occurred = True
            security_guard.record_audit_log(
                user_id=user_id,
                channel_id=channel_id,
                thread_ts=effective_thread_ts,
                action=f"execute_{cmd or 'prompt'}_error",
                details={"error": str(e)},
            )

        # 6. Format and mask response
        formatted_response = convert_gfm_to_slack_mrkdwn(response_text)
        if is_btw:
            formatted_response = f"💡 *[BTW 回答]*\n{formatted_response}"
        safe_response = security_guard.mask_secrets(formatted_response)

        # 7. Deliver response
        chunks = split_message_for_slack(safe_response)
        if placeholder_ts and chunks:
            try:
                await client.chat_update(
                    channel=channel_id,
                    ts=placeholder_ts,
                    text=chunks[0],
                )
                for extra_chunk in chunks[1:]:
                    await client.chat_postMessage(
                        channel=channel_id,
                        thread_ts=effective_thread_ts,
                        text=extra_chunk,
                    )
            except SlackApiError as e:
                logger.error(f"Failed to deliver final message: {e}")
        else:
            for chunk in chunks:
                await client.chat_postMessage(
                    channel=channel_id,
                    thread_ts=effective_thread_ts,
                    text=chunk,
                )

        # 8. Reactions update
        if target_ts:
            try:
                await client.reactions_remove(
                    channel=channel_id,
                    timestamp=target_ts,
                    name="eyes",
                )
                await client.reactions_add(
                    channel=channel_id,
                    timestamp=target_ts,
                    name="x" if error_occurred else "white_check_mark",
                )
            except SlackApiError as e:
                logger.debug(f"Could not update final reaction: {e}")

    # =========================================================================
    # Slack Native Slash Commands (/agy and /antigravity)
    # =========================================================================

    async def _handle_slash_command_core(ack: Any, command: Dict[str, Any], client: Any):
        await ack()

        user_id = command.get("user_id")
        channel_id = command.get("channel_id")
        text = command.get("text", "").strip()

        # Authorization check
        if not security_guard.is_user_authorized(user_id):
            await client.chat_postEphemeral(
                channel=channel_id,
                user=user_id,
                text=f"⚠️ *実行権限がありません。* (User ID: `{user_id}`)",
            )
            return

        if not security_guard.is_channel_allowed(channel_id, is_dm=False):
            await client.chat_postEphemeral(
                channel=channel_id,
                user=user_id,
                text="⚠️ *このチャンネルでは Antigravity Gateway は許可されていません。*",
            )
            return

        cmd, arg = _parse_command(text)

        # Fast Ephemeral replies for status and help
        if cmd == "status":
            await client.chat_postEphemeral(
                channel=channel_id,
                user=user_id,
                text=_build_status_card(),
            )
            return

        if cmd in ("help", "guide") or not text:
            await client.chat_postEphemeral(
                channel=channel_id,
                user=user_id,
                text=_build_help_card(),
            )
            return

        # Execute prompt or workflow command
        await _handle_user_prompt(
            client=client,
            channel_id=channel_id,
            thread_ts=None,
            user_id=user_id,
            raw_text=text,
            message_ts=None,
        )

    @app.command("/agy")
    async def handle_agy_command(ack: Any, command: Dict[str, Any], client: Any):
        await _handle_slash_command_core(ack, command, client)

    @app.command("/antigravity")
    async def handle_antigravity_command(ack: Any, command: Dict[str, Any], client: Any):
        await _handle_slash_command_core(ack, command, client)

    # =========================================================================
    # Event Handlers (Mentions and Messages)
    # =========================================================================

    @app.event("app_mention")
    async def handle_app_mention(event: Dict[str, Any], client: Any):
        """Handle direct mentions (@bot) in channels."""
        user_id = event.get("user")
        channel_id = event.get("channel")
        thread_ts = event.get("thread_ts")
        message_ts = event.get("ts")
        raw_text = event.get("text", "")

        await _ensure_channel_joined(client, channel_id)

        if not security_guard.is_user_authorized(user_id):
            logger.warning(f"Unauthorized mention from user: {user_id}")
            effective_ts = thread_ts or message_ts if settings.SESSION_MODE == "thread" else None
            await client.chat_postMessage(
                channel=channel_id,
                thread_ts=effective_ts,
                text=f"⚠️ *実行権限がありません。* (User ID: `{user_id}`)",
            )
            return

        if not security_guard.is_channel_allowed(channel_id, is_dm=False):
            logger.warning(f"Mention in unauthorized channel: {channel_id}")
            return

        target_thread = thread_ts or (message_ts if settings.SESSION_MODE == "thread" else None)
        await _handle_user_prompt(
            client=client,
            channel_id=channel_id,
            thread_ts=target_thread,
            user_id=user_id,
            raw_text=raw_text,
            message_ts=message_ts,
        )

    @app.event("message")
    async def handle_message(event: Dict[str, Any], client: Any):
        """Handle incoming messages (DMs, thread continuations, or channel-scoped chats)."""
        if event.get("bot_id") or event.get("subtype"):
            return

        user_id = event.get("user")
        channel_id = event.get("channel")
        channel_type = event.get("channel_type")
        thread_ts = event.get("thread_ts")
        message_ts = event.get("ts")
        raw_text = event.get("text", "")

        is_dm = channel_type == "im"

        # Case 1: Direct Message (DM)
        if is_dm:
            if not security_guard.is_user_authorized(user_id):
                await client.chat_postMessage(
                    channel=channel_id,
                    text=f"⚠️ *実行権限がありません。* (User ID: `{user_id}`)",
                )
                return

            dm_thread_ts = thread_ts or message_ts
            await _handle_user_prompt(
                client=client,
                channel_id=channel_id,
                thread_ts=dm_thread_ts,
                user_id=user_id,
                raw_text=raw_text,
                message_ts=message_ts,
            )
            return

        # Case 2: Channel Mode (single timeline per channel)
        if settings.SESSION_MODE == "channel" and not thread_ts:
            if session_manager.has_active_session(channel_id):
                if not security_guard.is_user_authorized(user_id):
                    await client.chat_postMessage(
                        channel=channel_id,
                        text=f"⚠️ *実行権限がありません。* (User ID: `{user_id}`)",
                    )
                    return

                if not security_guard.is_channel_allowed(channel_id, is_dm=False):
                    return

                await _handle_user_prompt(
                    client=client,
                    channel_id=channel_id,
                    thread_ts=None,
                    user_id=user_id,
                    raw_text=raw_text,
                    message_ts=message_ts,
                )
                return

        # Case 3: Thread Mode (thread continuation)
        if thread_ts and session_manager.has_active_session(channel_id, thread_ts):
            if not security_guard.is_user_authorized(user_id):
                await client.chat_postMessage(
                    channel=channel_id,
                    thread_ts=thread_ts,
                    text=f"⚠️ *実行権限がありません。* (User ID: `{user_id}`)",
                )
                return

            if not security_guard.is_channel_allowed(channel_id, is_dm=False):
                return

            await _handle_user_prompt(
                client=client,
                channel_id=channel_id,
                thread_ts=thread_ts,
                user_id=user_id,
                raw_text=raw_text,
                message_ts=message_ts,
            )
            return

    return app
