"""Security Guard implementing the 5-layer defense model."""

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Set

logger = logging.getLogger("gateway.security")


class SecurityGuard:
    """Security Guard providing User Whitelist, Channel Check, Safe Path Validation,

    Secret Redaction, and Audit Logging.
    """

    # Secret masking patterns (Slack tokens, Gemini/OpenAI/Anthropic keys, OAuth tokens)
    SECRET_PATTERNS = [
        (re.compile(r"xoxb-[0-9]{10,13}-[0-9]{10,13}-[a-zA-Z0-9]{24,32}"), "[REDACTED_SLACK_BOT_TOKEN]"),
        (re.compile(r"xapp-[0-9]-[a-zA-Z0-9]+-[0-9]+-[a-zA-Z0-9]+"), "[REDACTED_SLACK_APP_TOKEN]"),
        (re.compile(r"xoxp-[0-9]{10,13}-[0-9]{10,13}-[0-9]{10,13}-[a-zA-Z0-9]{24,32}"), "[REDACTED_SLACK_USER_TOKEN]"),
        (re.compile(r"AIza[0-9A-Za-z-_]{35}"), "[REDACTED_GEMINI_API_KEY]"),
        (re.compile(r"sk-ant-[a-zA-Z0-9_-]{20,}"), "[REDACTED_ANTHROPIC_API_KEY]"),
        (re.compile(r"sk-[a-zA-Z0-9_-]{20,}"), "[REDACTED_OPENAI_API_KEY]"),
        (re.compile(r"Bearer\s+[a-zA-Z0-9_\-\.]{20,}", re.IGNORECASE), "Bearer [REDACTED_BEARER_TOKEN]"),
        (re.compile(r"ghp_[a-zA-Z0-9]{36}"), "[REDACTED_GITHUB_TOKEN]"),
        (re.compile(r"AKIA[0-9A-Z]{16}"), "[REDACTED_AWS_KEY]"),
        (re.compile(r"\"(access_token|refresh_token)\"\s*:\s*\"[^\"]+\""), r'"\1": "[REDACTED_OAUTH_TOKEN]"'),
    ]

    # Sensitive files and patterns forbidden from agent file tools
    BLOCKED_FILE_PATTERNS = [
        re.compile(r"\.env(\..+)?$", re.IGNORECASE),
        re.compile(r".*\.pem$", re.IGNORECASE),
        re.compile(r".*\.key$", re.IGNORECASE),
        re.compile(r".*id_rsa.*", re.IGNORECASE),
        re.compile(r".*credentials\.json$", re.IGNORECASE),
        re.compile(r".*jetski-standalone-oauth-token.*", re.IGNORECASE),
        re.compile(r".*oauth.*token.*", re.IGNORECASE),
    ]

    # Dangerous command patterns forbidden from command execution tool
    DANGEROUS_COMMAND_PATTERNS = [
        re.compile(r"rm\s+-rf\s+/"),
        re.compile(r"\bmkfs\b"),
        re.compile(r"\bdd\s+if="),
        re.compile(r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:"),  # Fork bomb
        re.compile(r"\bshutdown\b"),
        re.compile(r"\breboot\b"),
        re.compile(r"\bsudo\b"),
    ]

    def __init__(
        self,
        allowed_user_ids: Set[str],
        allowed_channel_ids: Set[str],
        audit_log_path: str = "/app/logs/audit.log",
    ):
        self.allowed_user_ids = allowed_user_ids
        self.allowed_channel_ids = allowed_channel_ids
        self.audit_log_path = audit_log_path

        # Ensure audit log directory exists
        Path(self.audit_log_path).parent.mkdir(parents=True, exist_ok=True)

    def is_user_authorized(self, user_id: str) -> bool:
        """Check if a user is in the allowed whitelist."""
        if not self.allowed_user_ids or "*" in self.allowed_user_ids:
            return True
        return user_id in self.allowed_user_ids

    def is_channel_allowed(self, channel_id: str, is_dm: bool = False) -> bool:
        """Check if a channel is allowed.

        DMs are always allowed unless explicitly restricted.
        """
        if is_dm:
            return True
        if not self.allowed_channel_ids:
            return True
        return channel_id in self.allowed_channel_ids

    def is_safe_file_path(
        self,
        target_path: str,
        root_workspace: Optional[str] = None,
        workspace_root: Optional[str] = None,
    ) -> bool:
        """Verify path is strictly within workspace and does not point to sensitive files.

        Uses Path.is_relative_to for robust path traversal prevention (Issue #5).
        Allows GEMINI.md and rule markdown files while strictly blocking auth tokens.
        """
        effective_root = root_workspace or workspace_root or "/workspace"
        try:
            target = Path(target_path).resolve()
            root = Path(effective_root).resolve()

            # Robust Path Traversal Prevention
            if not target.is_relative_to(root):
                logger.warning(
                    f"Blocked path traversal attempt: {target} (root: {root})"
                )
                return False

            # Check sensitive file patterns first
            for pattern in self.BLOCKED_FILE_PATTERNS:
                if pattern.search(str(target)):
                    logger.warning(f"Blocked sensitive file access: {target}")
                    return False

            return True
        except Exception as e:
            logger.error(f"Error checking file path safety: {e}")
            return False

    def is_safe_command(self, command: str) -> bool:
        """Check if a terminal command is safe to execute."""
        for pattern in self.DANGEROUS_COMMAND_PATTERNS:
            if pattern.search(command):
                logger.warning(f"Blocked dangerous command: {command}")
                return False
        return True

    def mask_secrets(self, text: str) -> str:
        """Scan and mask any secrets, tokens, or API keys in outgoing text."""
        masked_text = text
        for pattern, replacement in self.SECRET_PATTERNS:
            masked_text = pattern.sub(replacement, masked_text)
        return masked_text

    def write_audit_log(
        self,
        event_type: str,
        user_id: str,
        channel_id: str,
        command_or_prompt: str,
        status: str,
        details: Optional[dict] = None,
    ):
        """Append an event to the structured audit log."""
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "user_id": user_id,
            "channel_id": channel_id,
            "command_or_prompt": self.mask_secrets(command_or_prompt),
            "status": status,
            "details": details or {},
        }
        try:
            with open(self.audit_log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"Failed to write to audit log: {e}")
