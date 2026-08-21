"""Command Parser and Dispatcher for Antigravity Gateway (Issue #1 DRY Refactoring)."""

import logging
import re
import subprocess
from typing import Any, Optional, Tuple

logger = logging.getLogger("gateway.commands")


def get_git_branch(workspace_path: str) -> str:
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


def clean_mention(text: str) -> str:
    """Remove Slack mention tags (<@U12345...>)."""
    return re.sub(r"<@[A-Z0-9]+>", "", text).strip()


def parse_command(raw_text: str) -> Tuple[Optional[str], str]:
    """Parse raw text to extract command name (e.g. 'goal', 'btw', 'reset') and remaining argument."""
    text = clean_mention(raw_text).strip()
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


def build_help_card() -> str:
    """Generate the full Antigravity command help guide in Slack mrkdwn."""
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


def build_status_card(settings: Any) -> str:
    """Generate the status overview card in Slack mrkdwn."""
    branch = get_git_branch(getattr(settings, "TARGET_WORKSPACE_PATH", "/workspace"))
    session_mode = getattr(settings, "SESSION_MODE", "THREAD").upper()
    auto_join = getattr(settings, "AUTO_JOIN_CHANNELS", True)
    allow_read = getattr(settings, "ALLOW_FILE_READ", True)
    allow_write = getattr(settings, "ALLOW_FILE_WRITE", False)
    allow_cmd = getattr(settings, "ALLOW_RUN_COMMAND", False)
    ttl = getattr(settings, "SESSION_TTL_HOURS", 2)
    workspace = getattr(settings, "TARGET_WORKSPACE_PATH", "/workspace")

    return (
        "📊 *Antigravity Gateway 稼働状況*\n"
        f"• *作業リポジトリ:* `{workspace}`\n"
        f"• *Git ブランチ:* `{branch}`\n"
        f"• *セッションモード:* `{session_mode}`\n"
        f"• *自動チャンネル参加:* `{'有効' if auto_join else '無効'}`\n"
        f"• *実行権限 (Capabilities):* 読込=`{allow_read}` / 書込=`{allow_write}` / コマンド=`{allow_cmd}`\n"
        f"• *セッション有効期限:* `{ttl} 時間`"
    )


def transform_prompt_for_mode(cmd: Optional[str], arg: str, raw_text: str) -> Tuple[str, bool]:
    """Transform user prompt with appropriate mode system directives and return (prompt, is_btw)."""
    is_btw = (cmd == "btw")
    actual_prompt = arg if cmd else raw_text
    actual_prompt = clean_mention(actual_prompt)

    if not actual_prompt:
        return "", is_btw

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

    return actual_prompt, is_btw
