"""Application entrypoint with Socket Mode, Auto-Join, and Graceful Task Shutdown (Issue #6)."""

import asyncio
import logging
import signal
import sys
from pathlib import Path
from typing import Set

# Ensure project root is in sys.path across all execution modes
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
from slack_sdk.errors import SlackApiError

from src.agent_runner import AgentRunner
from src.bot import create_app
from src.config import get_settings
from src.security import SecurityGuard
from src.session import SessionManager


def setup_logging(log_level: str, log_file_path: str):
    """Configure structured logging for stdout and file."""
    Path(log_file_path).parent.mkdir(parents=True, exist_ok=True)
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_file_path, encoding="utf-8"),
        ],
    )


async def auto_join_public_channels(app, logger):
    """Fetch all public channels and automatically join them upon startup."""
    try:
        cursor = None
        joined_count = 0
        while True:
            resp = await app.client.conversations_list(
                types="public_channel",
                exclude_archived=True,
                limit=100,
                cursor=cursor,
            )
            channels = resp.get("channels", [])
            for ch in channels:
                ch_id = ch["id"]
                if not ch.get("is_member"):
                    try:
                        await app.client.conversations_join(channel=ch_id)
                        joined_count += 1
                        logger.info(f"Auto-joined public channel: #{ch.get('name')} ({ch_id})")
                    except SlackApiError as e:
                        logger.debug(f"Could not auto-join #{ch.get('name')}: {e}")
            cursor = resp.get("response_metadata", {}).get("next_cursor")
            if not cursor:
                break
        if joined_count > 0:
            logger.info(f"✨ Successfully auto-joined {joined_count} public channel(s).")
    except asyncio.CancelledError:
        logger.debug("Auto-join background task cancelled.")
    except Exception as e:
        logger.warning(f"Auto-join channels scan encountered an error: {e}")


async def main():
    """Initialize and run the Antigravity Gateway."""
    try:
        settings = get_settings()
    except Exception as e:
        print(f"❌ Configuration Error: Failed to load and validate settings.\n{e}", file=sys.stderr)
        sys.exit(1)

    setup_logging(settings.LOG_LEVEL, settings.LOG_FILE_PATH)
    logger = logging.getLogger("gateway.main")

    logger.info("==================================================")
    logger.info("🚀 Starting Antigravity Gateway (Socket Mode)")
    logger.info(f"📁 Target Workspace: {settings.TARGET_WORKSPACE_PATH}")
    logger.info(f"🎛️  Session Mode: {settings.SESSION_MODE.upper()}")
    logger.info(f"🤖 Auto-Join Channels: {settings.AUTO_JOIN_CHANNELS}")
    logger.info(f"⏱️  Agent Timeout: {settings.AGENT_TIMEOUT_SEC}s / Max Turns: {settings.MAX_HISTORY_TURNS}")
    logger.info(f"🔒 Allowed Users: {settings.allowed_user_ids or 'All (Wildcard)'}")
    logger.info(f"💬 Allowed Channels: {settings.allowed_channel_ids or 'All'}")
    logger.info(
        f"⚙️  Capabilities: Read={settings.ALLOW_FILE_READ}, "
        f"Write={settings.ALLOW_FILE_WRITE}, Commands={settings.ALLOW_RUN_COMMAND}"
    )
    logger.info("==================================================")

    # Initialize components
    security_guard = SecurityGuard(
        allowed_user_ids=settings.allowed_user_ids,
        allowed_channel_ids=settings.allowed_channel_ids,
        audit_log_path=settings.AUDIT_LOG_PATH,
    )
    session_manager = SessionManager(
        ttl_hours=settings.SESSION_TTL_HOURS,
        mode=settings.SESSION_MODE,
        max_history_turns=settings.MAX_HISTORY_TURNS,
    )
    agent_runner = AgentRunner(settings=settings)

    # Create Slack App
    app = create_app(
        settings=settings,
        security_guard=security_guard,
        session_manager=session_manager,
        agent_runner=agent_runner,
    )

    # Track all background tasks for graceful shutdown (Issue #6)
    background_tasks: Set[asyncio.Task] = set()

    if settings.AUTO_JOIN_CHANNELS:
        task = asyncio.create_task(auto_join_public_channels(app, logger))
        background_tasks.add(task)
        task.add_done_callback(background_tasks.discard)

    handler = AsyncSocketModeHandler(app, settings.SLACK_APP_TOKEN)

    # Setup graceful shutdown handlers
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def _shutdown_signal_handler(sig_name):
        logger.info(f"Received shutdown signal ({sig_name}). Gracefully stopping...")
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, lambda s=sig.name: _shutdown_signal_handler(s))
        except NotImplementedError:
            pass

    logger.info("⚡️ Antigravity Gateway is connecting to Slack Socket Mode...")

    handler_task = asyncio.create_task(handler.start_async())
    background_tasks.add(handler_task)
    handler_task.add_done_callback(background_tasks.discard)

    try:
        await stop_event.wait()
    except asyncio.CancelledError:
        pass
    finally:
        logger.info("Closing Socket Mode connection and cleaning up background tasks...")
        await handler.close_async()

        # Cancel all remaining background tasks cleanly
        for task in background_tasks:
            task.cancel()
        if background_tasks:
            await asyncio.gather(*background_tasks, return_exceptions=True)

        logger.info("🛑 Gateway stopped gracefully.")


if __name__ == "__main__":
    asyncio.run(main())
