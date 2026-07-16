"""Pluggable clock abstraction.

Time is injected rather than read directly from :func:`datetime.now` so that
services are deterministic and testable. :class:`SystemClock` is the production
default; :class:`FrozenClock` gives tests full control over "now".
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Protocol, runtime_checkable


def utcnow() -> datetime:
    """Return the current timezone-aware UTC time."""
    return datetime.now(timezone.utc)


@runtime_checkable
class Clock(Protocol):
    """A source of the current time (dependency-injected into services)."""

    def now(self) -> datetime:
        """Return the current timezone-aware time."""
        ...


class SystemClock:
    """Production clock backed by the wall clock (UTC)."""

    def now(self) -> datetime:
        """Return the current timezone-aware UTC time."""
        return utcnow()


class FrozenClock:
    """Deterministic clock for tests.

    The time only advances when :meth:`advance` (or :meth:`set`) is called, so
    session-expiry and audit-ordering logic can be exercised precisely.
    """

    def __init__(self, start: datetime | None = None) -> None:
        self._now = start or datetime(2026, 1, 1, tzinfo=timezone.utc)

    def now(self) -> datetime:
        """Return the frozen current time."""
        return self._now

    def advance(self, seconds: float = 0.0, *, days: float = 0.0) -> datetime:
        """Advance the clock and return the new time."""
        self._now = self._now + timedelta(seconds=seconds, days=days)
        return self._now

    def set(self, moment: datetime) -> None:
        """Pin the clock to an explicit moment."""
        self._now = moment
