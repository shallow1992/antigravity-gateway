"""Slack Bolt AsyncApp definition and event routing (Issue #1 Clean Routing)."""

import logging
from typing import Any, Dict, Optional
from slack_bolt.async_app import AsyncApp
from slack_sdk.errors import SlackApiError

from src.agent_runner import AgentRunner
from src.commands import (
    build_help_card,
    build_status_card,
    parse_command,
    transform_prompt_for_mode,
)
from src.config import Settings
from src.converter import convert_gfm_to_slack_mrkdwn, split_message_for_slack
from src.security import SecurityGuard
from src.session import SessionManager

logger = logging.getLogger("gateway.bot")


def create_app(
    settings: Settings,
    security_guard: SecurityGuard,
    session_manager: SessionManager,
    agent_runner: AgentRunner,
) -> AsyncApp:
    """Initialize and configure the Slack Bolt AsyncApp."""

    app = AsyncApp(
        token=settings.SLACK_BOT_TOKEN,
        signing_secret=settings.SLACK_SIGNING_SECRET or None,
    )

    async def _ensure_channel_joined(client: Any, channel_id: str):
        if not settings.AUTO_JOIN_CHANNELS:
            return
        try:
            await client.conversations_join(channel=channel_id)
            logger.info(f"Auto-joined channel: {channel_id}")
        except SlackApiError as e:
            logger.debug(f"Channel join status for {channel_id}: {e.response.get('error')}")

    # Core execution pipeline
    async def _handle_user_prompt(
        client: Any,
        channel_id: str,
        thread_ts: Optional[str],
        user_id: str,
        raw_text: str,
        message_ts: Optional[str] = None,
    ) -> None:
        effective_thread_ts = thread_ts if settings.SESSION_MODE == "thread" else thread_ts
        cmd, arg = parse_command(raw_text)

        # 1. System Control Commands
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
                text=build_status_card(settings),
            )
            return

        if cmd in ("help", "guide"):
            await client.chat_postMessage(
                channel=channel_id,
                thread_ts=effective_thread_ts,
                text=build_help_card(),
            )
            return

        # 2. Prompt Transformation for Specific Modes
        actual_prompt, is_btw = transform_prompt_for_mode(cmd, arg, raw_text)

        if not actual_prompt:
            await client.chat_postMessage(
                channel=channel_id,
                thread_ts=effective_thread_ts,
                text="👋 こんにちは！何か質問や依頼があれば入力してください。\nヒント: `/agy help` で全コマンドを確認できます。",
            )
            return

        # 3. Session Management
        session = session_manager.get_or_create_session(channel_id, effective_thread_ts, user_id)
        if not is_btw:
            session.add_user_message(actual_prompt)

        # 4. Reactions and Placeholder
        target_ts = message_ts or thread_ts
        if target_ts:
            try:
                await client.reactions_add(channel=channel_id, timestamp=target_ts, name="eyes")
            except SlackApiError as e:
                logger.debug(f"Could not add reaction: {e}")

        placeholder_ts: Optional[str] = None
        prefix_title = "💬 *[BTW]* " if is_btw else "🧠 "
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
                    await client.chat_update(channel=channel_id, ts=placeholder_ts, text=status_text)
                except SlackApiError as e:
                    logger.debug(f"Failed to update progress: {e}")

        # 5. Agent Execution
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

        # 6. Response Formatting and Delivery
        formatted_response = convert_gfm_to_slack_mrkdwn(response_text)
        if is_btw:
            formatted_response = f"💡 *[BTW 回答]*\n{formatted_response}"
        safe_response = security_guard.mask_secrets(formatted_response)

        chunks = split_message_for_slack(safe_response)
        if placeholder_ts and chunks:
            try:
                await client.chat_update(channel=channel_id, ts=placeholder_ts, text=chunks[0])
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

        # 7. Reaction Cleanup
        if target_ts:
            try:
                await client.reactions_remove(channel=channel_id, timestamp=target_ts, name="eyes")
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

        cmd, arg = parse_command(text)

        # Fast Ephemeral replies for status and help
        if cmd == "status":
            await client.chat_postEphemeral(channel=channel_id, user=user_id, text=build_status_card(settings))
            return

        if cmd in ("help", "guide") or not text:
            await client.chat_postEphemeral(channel=channel_id, user=user_id, text=build_help_card())
            return

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
        user_id = event.get("user")
        channel_id = event.get("channel")
        thread_ts = event.get("thread_ts")
        message_ts = event.get("ts")
        raw_text = event.get("text", "")

        await _ensure_channel_joined(client, channel_id)

        if not security_guard.is_user_authorized(user_id):
            effective_ts = thread_ts or message_ts if settings.SESSION_MODE == "thread" else None
            await client.chat_postMessage(
                channel=channel_id,
                thread_ts=effective_ts,
                text=f"⚠️ *実行権限がありません。* (User ID: `{user_id}`)",
            )
            return

        if not security_guard.is_channel_allowed(channel_id, is_dm=False):
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

        # Case 2: Channel Mode (single timeline)
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
