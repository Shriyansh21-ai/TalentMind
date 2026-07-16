"""Incident management models (Module 12).

Incidents with severity, ownership, a status lifecycle, an append-only timeline,
root-cause and resolution tracking. Tenant-scoped. No ticketing integration —
this is a self-contained incident record.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import Field

from src.platform.common.models import PlatformModel, TenantScopedEntity
from src.platform.security.common.models import Severity


class IncidentStatus(str, Enum):
    """The lifecycle state of an incident."""

    OPEN = "open"
    INVESTIGATING = "investigating"
    IDENTIFIED = "identified"
    MITIGATED = "mitigated"
    RESOLVED = "resolved"
    CLOSED = "closed"

    @property
    def is_terminal(self) -> bool:
        """Return whether the incident is resolved/closed."""
        return self in (IncidentStatus.RESOLVED, IncidentStatus.CLOSED)


class TimelineEntry(PlatformModel):
    """A single append-only timeline event on an incident."""

    at: datetime
    status: IncidentStatus
    note: str = ""
    actor: str = ""


class Incident(TenantScopedEntity):
    """A tenant-scoped incident record."""

    title: str
    description: str = ""
    severity: Severity = Severity.MEDIUM
    status: IncidentStatus = IncidentStatus.OPEN
    owner: str = ""
    escalated: bool = False
    root_cause: str = ""
    resolution: str = ""
    timeline: list[TimelineEntry] = Field(default_factory=list)
    related_event_ids: list[str] = Field(default_factory=list)
    detected_at: datetime | None = None
    resolved_at: datetime | None = None

    @property
    def is_open(self) -> bool:
        """Return whether the incident is still open."""
        return not self.status.is_terminal
