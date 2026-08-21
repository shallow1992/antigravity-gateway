"""Conversation Session Manager with TTL and FIFO history rotation (Issue #3, #12)."""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Literal, Optional

logger = logging.getLogger("gateway.session")


@dataclass
class ConversationSession:
    """Represents an active multi-turn conversation in a Slack thread or channel."""

    session_key: str  # "{channel_id}:{thread_ts}" or "{channel_id}"
    channel_id: str
    thread_ts: Optional[str]
    user_id: str
    max_history_turns: int = 20
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_active_at: datetime = field(default_factory=datetime.utcnow)
    history: List[Dict[str, str]] = field(default_factory=list)  # [{"role": "user"|"assistant", "content": "..."}]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_expired(self, ttl_hours: int = 2) -> bool:
        """Check if session has exceeded the inactivity TTL."""
        expiry_threshold = datetime.utcnow() - timedelta(hours=ttl_hours)
        return self.last_active_at < expiry_threshold

    def touch(self) -> None:
        """Update last active timestamp."""
        self.last_active_at = datetime.utcnow()

    def add_user_message(self, content: str) -> None:
        """Append a user message to session history with FIFO rotation."""
        self.history.append({"role": "user", "content": content})
        self._trim_history()
        self.touch()

    def add_assistant_message(self, content: str) -> None:
        """Append an assistant response to session history with FIFO rotation."""
        self.history.append({"role": "assistant", "content": content})
        self._trim_history()
        self.touch()

    def get_formatted_history(self) -> str:
        """Format history list into a clean readable string for prompt context."""
        lines = []
        for msg in self.history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            lines.append(f"{role}: {content}")
        return "\n".join(lines)

    def _trim_history(self) -> None:
        """Keep only the latest max_history_turns messages to prevent memory/context explosion."""
        if len(self.history) > self.max_history_turns:
            trimmed_count = len(self.history) - self.max_history_turns
            self.history = self.history[-self.max_history_turns:]
            logger.debug(f"Trimmed {trimmed_count} older turns from session {self.session_key}")


class SessionManager:
    """Thread-safe in-memory session manager supporting both thread-scoped and channel-scoped sessions."""

    def __init__(
        self,
        ttl_hours: int = 2,
        mode: Literal["thread", "channel"] = "thread",
        max_history_turns: int = 20,
    ):
        self.ttl_hours = ttl_hours
        self.mode = mode
        self.max_history_turns = max_history_turns
        self._sessions: Dict[str, ConversationSession] = {}

    def _make_key(self, channel_id: str, thread_ts: Optional[str] = None) -> str:
        if self.mode == "channel" or not thread_ts:
            return channel_id
        return f"{channel_id}:{thread_ts}"

    def get_session(
        self, channel_id: str, thread_ts: Optional[str] = None
    ) -> Optional[ConversationSession]:
        """Retrieve an active session if it exists and has not expired."""
        self.cleanup_expired()
        key = self._make_key(channel_id, thread_ts)
        session = self._sessions.get(key)
        if session:
            if session.is_expired(self.ttl_hours):
                del self._sessions[key]
                logger.info(f"Session expired and removed: {key}")
                return None
            session.touch()
            return session
        return None

    def get_or_create_session(
        self, channel_id: str, thread_ts: Optional[str], user_id: str
    ) -> ConversationSession:
        """Get existing session or create a new one."""
        self.cleanup_expired()
        key = self._make_key(channel_id, thread_ts)
        session = self._sessions.get(key)
        if not session or session.is_expired(self.ttl_hours):
            session = ConversationSession(
                session_key=key,
                channel_id=channel_id,
                thread_ts=thread_ts if self.mode == "thread" else None,
                user_id=user_id,
                max_history_turns=self.max_history_turns,
            )
            self._sessions[key] = session
            logger.info(f"Created new conversation session: {key} (mode={self.mode}) for user {user_id}")
        else:
            session.touch()
        return session

    def has_active_session(self, channel_id: str, thread_ts: Optional[str] = None) -> bool:
        """Check if an active, non-expired session exists."""
        return self.get_session(channel_id, thread_ts) is not None

    def clear_session(self, channel_id: str, thread_ts: Optional[str] = None) -> bool:
        """Manually remove/reset a session."""
        key = self._make_key(channel_id, thread_ts)
        if key in self._sessions:
            del self._sessions[key]
            logger.info(f"Manually cleared session: {key}")
            return True
        return False

    def cleanup_expired(self) -> int:
        """Evict all expired sessions."""
        now = datetime.utcnow()
        threshold = now - timedelta(hours=self.ttl_hours)
        expired_keys = [
            k for k, s in self._sessions.items() if s.last_active_at < threshold
        ]
        for k in expired_keys:
            del self._sessions[k]
        if expired_keys:
            logger.debug(f"Evicted {len(expired_keys)} expired sessions")
        return len(expired_keys)
