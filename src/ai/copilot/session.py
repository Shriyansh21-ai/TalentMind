"""Copilot session + in-memory session store.

A session bundles a conversation's history and working state under a stable id.
The store is process-local for now; the interface is intentionally minimal so a
durable / distributed store can replace it later without touching callers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict

from src.ai.copilot.history import ConversationHistory
from src.ai.copilot.state import ConversationState


@dataclass
class CopilotSession:
    """One recruiter conversation.

    Attributes:
        session_id: Stable session identifier.
        history: The conversation message log.
        state: The conversation working state.
        turn_count: Number of completed copilot turns.
    """

    session_id: str
    history: ConversationHistory = field(default_factory=ConversationHistory)
    state: ConversationState = field(default_factory=ConversationState)
    turn_count: int = 0


class SessionStore:
    """In-memory ``session_id -> CopilotSession`` store."""

    def __init__(self) -> None:
        self._sessions: Dict[str, CopilotSession] = {}

    def get_or_create(self, session_id: str) -> CopilotSession:
        """Return the session for ``session_id``, creating it if new."""
        if session_id not in self._sessions:
            self._sessions[session_id] = CopilotSession(session_id=session_id)
        return self._sessions[session_id]

    def get(self, session_id: str) -> CopilotSession | None:
        """Return the session for ``session_id`` (or ``None``)."""
        return self._sessions.get(session_id)

    def reset(self, session_id: str) -> None:
        """Drop a session's history + state."""
        self._sessions.pop(session_id, None)
