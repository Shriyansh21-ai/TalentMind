"""Conversation manager — session lifecycle + turn recording.

Thin coordinator between the controller and the session store so the controller
does not manipulate history/state storage directly (single responsibility). This
is also the seam where future durable/long-term memory will attach.
"""

from __future__ import annotations

from src.ai.copilot.models import CopilotTurn
from src.ai.copilot.session import CopilotSession, SessionStore


class ConversationManager:
    """Manages copilot sessions and records completed turns."""

    def __init__(self, store: SessionStore | None = None) -> None:
        """Bind to a :class:`SessionStore` (a fresh in-memory one by default)."""
        self.store = store or SessionStore()

    def get_or_create(self, session_id: str) -> CopilotSession:
        """Return (creating if needed) the session for ``session_id``."""
        return self.store.get_or_create(session_id)

    def record(self, session: CopilotSession, message: str, turn: CopilotTurn) -> None:
        """Append the exchange to history and advance the turn counter."""
        session.history.add_user(message)
        session.history.add_assistant(turn.answer)
        session.turn_count += 1

    def reset(self, session_id: str) -> None:
        """Reset a conversation."""
        self.store.reset(session_id)
