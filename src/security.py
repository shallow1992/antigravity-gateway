"""Security and Authorization Guard module."""

import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger("gateway.security")

# Regex patterns for identifying common API keys and tokens to mask
SECRET_PATTERNS = [
    # Slack Tokens
    (re.compile(r"xoxb-[0-9]{10,14}-[0-9]{10,14}-[a-zA-Z0-9]{24}"), "[REDACTED_SLACK_BOT_TOKEN]"),
    (re.compile(r"xapp-[0-9]-[a-zA-Z0-9]+-[0-9]+-[a-zA-Z0-9]+"), "[REDACTED_SLACK_APP_TOKEN]"),
    (re.compile(r"xoxp-[0-9]{10,14}-[0-9]{10,14}-[a-zA-Z0-9]{24}"), "[REDACTED_SLACK_USER_TOKEN]"),
    # Google / Gemini API Keys
    (re.compile(r"AIza[0-9A-Za-z-_]{35}"), "[REDACTED_GEMINI_API_KEY]"),
    # GitHub Personal Access Tokens
    (re.compile(r"ghp_[a-zA-Z0-9]{36}"), "[REDACTED_GITHUB_TOKEN]"),
    (re.compile(r"github_pat_[a-zA-Z0-9_]{82}"), "[REDACTED_GITHUB_PAT]"),
    # AWS Access Keys
    (re.compile(r"(?:AKIA|ABIA|ACCA|ASIA)[0-9A-Z]{16}"), "[REDACTED_AWS_KEY]"),
    # Generic Private Keys
    (
        re.compile(r"-----BEGIN [A-Z ]+ PRIVATE KEY-----[^-]+-----END [A-Z ]+ PRIVATE KEY-----", re.DOTALL),
        "[REDACTED_PRIVATE_KEY]",
    ),
]

# Sensitive file and directory blacklists
BLOCKED_FILE_PATTERNS = [
    re.compile(r"^\.env(\..+)?$", re.IGNORECASE),
    re.compile(r"^.*\.(pem|key|pfx|p12|pkcs12)$", re.IGNORECASE),
    re.compile(r"^id_(rsa|dsa|ecdsa|ed25519)(\.pub)?$", re.IGNORECASE),
    re.compile(r"^credentials\.json$", re.IGNORECASE),
    re.compile(r"^service_account.*\.json$", re.IGNORECASE),
    re.compile(r"^\.git/config$", re.IGNORECASE),
]

# Prohibited destructive / external commands
BLOCKED_COMMAND_PREFIXES = [
    "rm -rf /",
    "rm -rf *",
    "mkfs",
    "dd if=",
    "chmod -R 777",
    "chown -R",
    ":(){ :|:& };:", # Fork bomb
    "sudo",
]


class SecurityGuard:
    """Handles authentication, authorization, secret redaction, and audit logging."""

    def __init__(
        self,
        allowed_user_ids: Set[str],
        allowed_channel_ids: Set[str],
        audit_log_path: str = "./logs/audit.log",
    ):
        self.allowed_user_ids = allowed_user_ids
        self.allowed_channel_ids = allowed_channel_ids
        self.audit_log_path = audit_log_path

        # Ensure audit log directory exists
        Path(audit_log_path).parent.mkdir(parents=True, exist_ok=True)

    def is_user_authorized(self, user_id: Optional[str]) -> bool:
        """Check if the given Slack user ID is authorized."""
        if not user_id:
            return False
        # If whitelist is empty or contains wildcard "*", allow all
        if not self.allowed_user_ids or "*" in self.allowed_user_ids:
            return True
        return user_id in self.allowed_user_ids

    def is_channel_allowed(self, channel_id: Optional[str], is_dm: bool = False) -> bool:
        """Check if interaction in the given channel is allowed."""
        if is_dm:
            # Direct Messages are always allowed if user is authorized
            return True
        if not channel_id:
            return False
        # If whitelist is empty, allow all channels
        if not self.allowed_channel_ids or "*" in self.allowed_channel_ids:
            return True
        return channel_id in self.allowed_channel_ids

    def mask_secrets(self, text: str) -> str:
        """Redact known API keys, tokens, and private keys from the text."""
        if not text:
            return text
        sanitized = text
        for pattern, replacement in SECRET_PATTERNS:
            sanitized = pattern.sub(replacement, sanitized)
        return sanitized

    def is_safe_file_path(self, file_path: str, workspace_root: str = "/workspace") -> bool:
        """Validate that a file path is within workspace and not on the sensitive file blacklist."""
        try:
            target = Path(file_path).resolve()
            root = Path(workspace_root).resolve()

            # Path traversal check
            if not str(target).startswith(str(root)):
                logger.warning(f"Blocked path traversal attempt: {file_path} (root: {workspace_root})")
                return False

            # Check against blocked file patterns
            filename = target.name
            rel_path = str(target.relative_to(root))
            for pattern in BLOCKED_FILE_PATTERNS:
                if pattern.match(filename) or pattern.match(rel_path):
                    logger.warning(f"Blocked sensitive file access: {file_path}")
                    return False

            return True
        except Exception as e:
            logger.error(f"Error checking file path safety: {e}")
            return False

    def is_safe_command(self, command_line: str) -> bool:
        """Check if a shell command contains known dangerous commands."""
        normalized = command_line.strip().lower()
        for prefix in BLOCKED_COMMAND_PREFIXES:
            if prefix in normalized:
                logger.warning(f"Blocked dangerous command: {command_line}")
                return False
        return True

    def record_audit_log(
        self,
        user_id: str,
        channel_id: str,
        thread_ts: Optional[str],
        action: str,
        details: Dict[str, Any],
    ) -> None:
        """Write an audit entry to the audit log file."""
        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "user_id": user_id,
            "channel_id": channel_id,
            "thread_ts": thread_ts,
            "action": action,
            "details": details,
        }
        try:
            with open(self.audit_log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")
