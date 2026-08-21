"""Configuration module using Pydantic Settings."""

import os
from pathlib import Path
from typing import List, Literal, Set
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings validated from environment variables and .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Slack Credentials
    SLACK_BOT_TOKEN: str = Field(
        ...,
        description="Slack Bot User OAuth Token (xoxb-...)",
    )
    SLACK_APP_TOKEN: str = Field(
        ...,
        description="Slack App-Level Token for Socket Mode (xapp-...)",
    )
    SLACK_SIGNING_SECRET: str = Field(
        default="",
        description="Slack Signing Secret (optional for Socket Mode)",
    )

    # Security & Access Control
    ALLOWED_USER_IDS_RAW: str = Field(
        default="",
        validation_alias="ALLOWED_USER_IDS",
        description="Comma-separated Slack user IDs allowed to interact with the bot",
    )
    ALLOWED_CHANNEL_IDS_RAW: str = Field(
        default="",
        validation_alias="ALLOWED_CHANNEL_IDS",
        description="Comma-separated Slack channel IDs allowed. Empty means all channels allowed.",
    )

    # Session & Interaction Mode
    SESSION_MODE: Literal["thread", "channel"] = Field(
        default="thread",
        description="Session scope: 'thread' (per Slack thread) or 'channel' (per Slack channel)",
    )
    AUTO_JOIN_CHANNELS: bool = Field(
        default=True,
        description="Automatically join public channels upon startup or mention",
    )

    # Antigravity Workspace & Capabilities
    TARGET_WORKSPACE_PATH: str = Field(
        default="/workspace",
        description="Absolute path to the target workspace/repository for Antigravity to operate on",
    )
    ALLOW_FILE_READ: bool = Field(
        default=True,
        description="Allow Antigravity to read/search files in the workspace",
    )
    ALLOW_FILE_WRITE: bool = Field(
        default=False,
        description="Allow Antigravity to create/edit files in the workspace",
    )
    ALLOW_RUN_COMMAND: bool = Field(
        default=False,
        description="Allow Antigravity to execute terminal commands",
    )

    # Session & Throttling
    SESSION_TTL_HOURS: int = Field(
        default=2,
        description="TTL (hours) before an inactive conversation session expires",
    )
    MAX_HISTORY_TURNS: int = Field(
        default=20,
        description="Max message turns retained in conversation session (FIFO rotation)",
    )
    THROTTLING_INTERVAL_SEC: float = Field(
        default=0.8,
        description="Minimum seconds between Slack message in-place updates to prevent rate limiting",
    )
    AGENT_TIMEOUT_SEC: int = Field(
        default=300,
        description="Maximum execution timeout in seconds for agent.chat (prevents hanging)",
    )

    # Logging
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR)",
    )
    LOG_FILE_PATH: str = Field(
        default="./logs/gateway.log",
        description="Path to the application log file",
    )
    AUDIT_LOG_PATH: str = Field(
        default="./logs/audit.log",
        description="Path to the security audit log file",
    )
    ARTIFACTS_DIR: str = Field(
        default="./artifacts",
        description="Directory to store generated artifacts (plans, walkthroughs)",
    )

    @property
    def allowed_user_ids(self) -> Set[str]:
        """Parsed set of allowed Slack user IDs."""
        if not self.ALLOWED_USER_IDS_RAW:
            return set()
        return {uid.strip() for uid in self.ALLOWED_USER_IDS_RAW.split(",") if uid.strip()}

    @property
    def allowed_channel_ids(self) -> Set[str]:
        """Parsed set of allowed Slack channel IDs."""
        if not self.ALLOWED_CHANNEL_IDS_RAW:
            return set()
        return {cid.strip() for cid in self.ALLOWED_CHANNEL_IDS_RAW.split(",") if cid.strip()}


def get_settings() -> Settings:
    """Load and return application settings singleton."""
    return Settings()
