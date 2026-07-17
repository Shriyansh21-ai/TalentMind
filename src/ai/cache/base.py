"""Cache interface for the AI Platform.

A minimal, storage-agnostic contract so the runner depends on an abstraction, not
a concrete store. Swapping the file cache for Redis/SQLite later is a matter of
implementing this interface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseCache(ABC):
    """Abstract key/value cache for JSON-serializable payloads."""

    @abstractmethod
    def get(self, key: str) -> dict[str, Any] | None:
        """Return the cached payload for ``key`` (or ``None`` if absent)."""

    @abstractmethod
    def set(self, key: str, value: dict[str, Any]) -> None:
        """Store ``value`` under ``key``."""

    @abstractmethod
    def delete(self, key: str) -> None:
        """Remove ``key`` if present."""

    @abstractmethod
    def clear(self) -> None:
        """Remove all entries."""


class NullCache(BaseCache):
    """A no-op cache (used when caching is disabled)."""

    def get(self, key: str) -> dict[str, Any] | None:
        """Always miss."""
        return None

    def set(self, key: str, value: dict[str, Any]) -> None:
        """Discard writes."""

    def delete(self, key: str) -> None:
        """No-op."""

    def clear(self) -> None:
        """No-op."""
