"""In-memory, session-scoped memory implementation.

Suitable for a single Streamlit session. Deliberately simple and process-local;
durable backends can replace it later behind :class:`BaseMemory`.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.ai.memory.base import BaseMemory


class SessionMemory(BaseMemory):
    """A dict-backed :class:`BaseMemory` for transient, per-session state."""

    def __init__(self) -> None:
        self._store: Dict[str, Dict[str, Any]] = {}
        self._log: Dict[str, List[Any]] = {}

    def get(self, session_id: str, key: str, default: Any = None) -> Any:
        """Return the value for ``(session_id, key)`` or ``default``."""
        return self._store.get(session_id, {}).get(key, default)

    def set(self, session_id: str, key: str, value: Any) -> None:
        """Store ``value`` under ``(session_id, key)``."""
        self._store.setdefault(session_id, {})[key] = value

    def append(self, session_id: str, value: Any) -> None:
        """Append ``value`` to the session's interaction log."""
        self._log.setdefault(session_id, []).append(value)

    def history(self, session_id: str) -> List[Any]:
        """Return a copy of the session's interaction log."""
        return list(self._log.get(session_id, []))

    def clear(self, session_id: Optional[str] = None) -> None:
        """Clear one session or (when ``None``) all sessions."""
        if session_id is None:
            self._store.clear()
            self._log.clear()
        else:
            self._store.pop(session_id, None)
            self._log.pop(session_id, None)
