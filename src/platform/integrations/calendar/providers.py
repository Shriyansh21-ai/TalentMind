"""Calendar provider interfaces (Module 4).

Provider interfaces for Google Calendar, Microsoft Outlook, Exchange and Apple
Calendar. Architecture only — no API implementation. Calendar providers are
bidirectional (read availability, write interview slots) and several support
realtime push, so their capability profiles reflect scheduling entities.
"""

from __future__ import annotations

from src.platform.integrations.common.models import (
    AuthScheme,
    IntegrationCapabilities,
    IntegrationMetadata,
    ProviderCategory,
    SyncDirection,
)
from src.platform.integrations.common.provider import BaseIntegrationProvider

_CAL_ENTITIES = ["calendar", "event", "availability", "interview_slot"]


def _calendar_capabilities(*, realtime: bool = False) -> IntegrationCapabilities:
    """Return a standard calendar capability profile (bidirectional)."""
    return IntegrationCapabilities(
        supports_read=True,
        supports_write=True,
        supports_full_sync=True,
        supports_incremental_sync=True,
        supports_webhooks=True,
        supports_realtime=realtime,
        supports_bulk=False,
        direction=SyncDirection.BIDIRECTIONAL,
        entities=list(_CAL_ENTITIES),
        scopes=["calendar:read", "calendar:write", "availability:read"],
    )


class _CalendarProvider(BaseIntegrationProvider):
    """Base for calendar providers."""

    capabilities = _calendar_capabilities()


class GoogleCalendarProvider(_CalendarProvider):
    key = "google_calendar"
    metadata = IntegrationMetadata(
        display_name="Google Calendar",
        vendor="Google LLC",
        category=ProviderCategory.CALENDAR,
        description="Google Calendar scheduling, availability and Google Meet links.",
        website="https://calendar.google.com",
        docs_url="https://developers.google.com/calendar",
        logo_emoji="📅",
        auth_schemes=[AuthScheme.OAUTH2],
        tags=["calendar", "google", "workspace"],
    )
    capabilities = _calendar_capabilities(realtime=True)


class OutlookCalendarProvider(_CalendarProvider):
    key = "microsoft_outlook"
    metadata = IntegrationMetadata(
        display_name="Microsoft Outlook Calendar",
        vendor="Microsoft Corporation",
        category=ProviderCategory.CALENDAR,
        description="Outlook / Microsoft 365 calendar and Teams meeting links.",
        website="https://outlook.com",
        docs_url="https://learn.microsoft.com/graph/api/resources/calendar",
        logo_emoji="📆",
        auth_schemes=[AuthScheme.OAUTH2],
        tags=["calendar", "microsoft", "m365"],
    )
    capabilities = _calendar_capabilities(realtime=True)


class ExchangeCalendarProvider(_CalendarProvider):
    key = "exchange"
    metadata = IntegrationMetadata(
        display_name="Microsoft Exchange",
        vendor="Microsoft Corporation",
        category=ProviderCategory.CALENDAR,
        description="On-premises / hybrid Exchange calendar via EWS.",
        website="https://www.microsoft.com/exchange",
        logo_emoji="🗓️",
        auth_schemes=[AuthScheme.OAUTH2, AuthScheme.BASIC],
        tags=["calendar", "exchange", "on-prem"],
    )


class AppleCalendarProvider(_CalendarProvider):
    key = "apple_calendar"
    metadata = IntegrationMetadata(
        display_name="Apple Calendar (iCloud)",
        vendor="Apple Inc.",
        category=ProviderCategory.CALENDAR,
        description="iCloud calendar via CalDAV.",
        website="https://www.icloud.com/calendar",
        logo_emoji="🍎",
        auth_schemes=[AuthScheme.BASIC, AuthScheme.OAUTH2],
        tags=["calendar", "apple", "caldav"],
    )
    capabilities = _calendar_capabilities()


def all_providers() -> list[BaseIntegrationProvider]:
    """Return one instance of every built-in calendar provider interface."""
    return [
        GoogleCalendarProvider(),
        OutlookCalendarProvider(),
        ExchangeCalendarProvider(),
        AppleCalendarProvider(),
    ]
