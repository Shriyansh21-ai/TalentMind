"""Memory interface for the AI Platform.

This milestone ships only lightweight, in-session memory, but the interface is
defined now so future milestones can add durable / vector / long-term memory
behind the same contract without touching agents.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, List, Optional


class BaseMemory(ABC):
    """Abstract, session-scoped key/value + append-log memory."""

    @abstractmethod
    def get(self, session_id: str, key: str, default: Any = None) -> Any:
        """Return a stored value for ``(session_id, key)``."""

    @abstractmethod
    def set(self, session_id: str, key: str, value: Any) -> None:
        """Store ``value`` under ``(session_id, key)``."""

    @abstractmethod
    def append(self, session_id: str, value: Any) -> None:
        """Append ``value`` to the session's ordered interaction log."""

    @abstractmethod
    def history(self, session_id: str) -> List[Any]:
        """Return the session's interaction log (oldest first)."""

    @abstractmethod
    def clear(self, session_id: Optional[str] = None) -> None:
        """Clear one session, or all sessions when ``session_id`` is ``None``."""
