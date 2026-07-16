"""Calendar integration models (Module 4).

Architecture for scheduling, availability, interview slots, timezone conversion
and meeting metadata. Pure, dependency-light domain models plus a small,
deterministic timezone-offset helper — **no calendar API is implemented**. A
production calendar connector produces/consumes these models behind the provider
seam.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from enum import Enum

from pydantic import Field

from src.platform.common.models import Metadata, PlatformModel, TenantScopedEntity


class SlotStatus(str, Enum):
    """The booking state of an interview slot."""

    OPEN = "open"
    HELD = "held"
    BOOKED = "booked"
    CANCELLED = "cancelled"


class MeetingProvider(str, Enum):
    """The conferencing surface a meeting is hosted on."""

    GOOGLE_MEET = "google_meet"
    MICROSOFT_TEAMS = "microsoft_teams"
    ZOOM = "zoom"
    WEBEX = "webex"
    IN_PERSON = "in_person"
    PHONE = "phone"


def convert_timezone(moment: datetime, offset_minutes: int) -> datetime:
    """Convert a timezone-aware ``moment`` to a fixed UTC offset.

    A dependency-light stand-in for full IANA timezone handling: it shifts an
    aware datetime to a fixed offset (in minutes). Naive datetimes are assumed
    UTC. A production deployment can swap this for ``zoneinfo`` without changing
    callers.
    """
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    target = timezone(timedelta(minutes=offset_minutes))
    return moment.astimezone(target)


class TimeWindow(PlatformModel):
    """A half-open ``[start, end)`` time window (timezone-aware)."""

    start: datetime
    end: datetime

    @property
    def duration_minutes(self) -> int:
        """Return the window length in whole minutes."""
        return int((self.end - self.start).total_seconds() // 60)

    def overlaps(self, other: "TimeWindow") -> bool:
        """Return whether this window overlaps ``other``."""
        return self.start < other.end and other.start < self.end


class Availability(PlatformModel):
    """A participant's free/busy availability for scheduling.

    Availability is expressed as a list of free :class:`TimeWindow` s in the
    participant's timezone (as a fixed UTC offset, in minutes).
    """

    participant_id: str
    timezone_offset_minutes: int = 0
    free_windows: list[TimeWindow] = Field(default_factory=list)

    def is_free_at(self, window: TimeWindow) -> bool:
        """Return whether ``window`` fits entirely inside a free window."""
        return any(
            fw.start <= window.start and window.end <= fw.end
            for fw in self.free_windows
        )


class MeetingMetadata(PlatformModel):
    """Conferencing/meeting details attached to a booked slot."""

    provider: MeetingProvider = MeetingProvider.GOOGLE_MEET
    join_url: str = ""
    conference_id: str = ""
    location: str = ""
    dial_in: str = ""
    notes: str = ""


class InterviewSlot(TenantScopedEntity):
    """A tenant-scoped interview slot that can be offered and booked."""

    calendar_integration_id: str = ""
    window: TimeWindow
    timezone_offset_minutes: int = 0
    status: SlotStatus = SlotStatus.OPEN
    interviewer_ids: list[str] = Field(default_factory=list)
    candidate_id: str = ""
    meeting: MeetingMetadata = Field(default_factory=MeetingMetadata)
    metadata: Metadata = Field(default_factory=Metadata)

    def local_window(self) -> TimeWindow:
        """Return the slot window converted to its own timezone offset."""
        return TimeWindow(
            start=convert_timezone(self.window.start, self.timezone_offset_minutes),
            end=convert_timezone(self.window.end, self.timezone_offset_minutes),
        )
