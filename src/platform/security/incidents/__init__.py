"""Module 12 — Incident Management.

Incidents with severity, ownership, escalation, a status lifecycle, an
append-only timeline, root-cause and resolution/recovery tracking, and incident
reports via :class:`IncidentService`. No ticketing integration.
"""

from __future__ import annotations

from src.platform.security.incidents.models import (
    Incident,
    IncidentStatus,
    TimelineEntry,
)
from src.platform.security.incidents.service import IncidentService

__all__ = [
    "IncidentStatus",
    "TimelineEntry",
    "Incident",
    "IncidentService",
]
