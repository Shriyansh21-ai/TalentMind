"""Module 4 — Calendar Integration.

Scheduling, availability, interview-slot and timezone-conversion architecture,
plus swappable provider interfaces for Google Calendar, Microsoft Outlook,
Exchange and Apple Calendar. Architecture only — no API implementation.
"""

from __future__ import annotations

from src.platform.integrations.calendar.models import (
    Availability,
    InterviewSlot,
    MeetingMetadata,
    MeetingProvider,
    SlotStatus,
    TimeWindow,
    convert_timezone,
)
from src.platform.integrations.calendar.providers import (
    AppleCalendarProvider,
    ExchangeCalendarProvider,
    GoogleCalendarProvider,
    OutlookCalendarProvider,
    all_providers,
)

__all__ = [
    "TimeWindow",
    "Availability",
    "InterviewSlot",
    "SlotStatus",
    "MeetingMetadata",
    "MeetingProvider",
    "convert_timezone",
    "GoogleCalendarProvider",
    "OutlookCalendarProvider",
    "ExchangeCalendarProvider",
    "AppleCalendarProvider",
    "all_providers",
]
