"""Incident management service (Module 12).

Opens incidents, assigns ownership, escalates severity, drives the status
lifecycle (each transition appended to an immutable timeline), records root
cause and resolution, and produces incident reports. Tenant-isolated and
clock-driven; no external ticketing.
"""

from __future__ import annotations

from src.platform.common.clock import Clock, SystemClock
from src.platform.common.ids import generate_id
from src.platform.common.repository import InMemoryRepository
from src.platform.security.common.models import Severity
from src.platform.security.incidents.models import (
    Incident,
    IncidentStatus,
    TimelineEntry,
)

_ESCALATION = {
    Severity.INFO: Severity.LOW,
    Severity.LOW: Severity.MEDIUM,
    Severity.MEDIUM: Severity.HIGH,
    Severity.HIGH: Severity.CRITICAL,
    Severity.CRITICAL: Severity.CRITICAL,
}


class IncidentService:
    """Create and manage the lifecycle of incidents (tenant-isolated)."""

    def __init__(self, *, clock: Clock | None = None) -> None:
        self._clock = clock or SystemClock()
        self.repo: InMemoryRepository[Incident] = InMemoryRepository("incident")

    # -- creation -----------------------------------------------------------

    def open_incident(
        self,
        tenant_id: str,
        organization_id: str,
        title: str,
        *,
        severity: Severity = Severity.MEDIUM,
        description: str = "",
        owner: str = "",
        related_event_ids: list[str] | None = None,
    ) -> Incident:
        """Open a new incident (status OPEN, initial timeline entry)."""
        now = self._clock.now()
        incident = Incident(
            id=generate_id("inc"),
            tenant_id=tenant_id,
            organization_id=organization_id,
            title=title,
            description=description,
            severity=severity,
            status=IncidentStatus.OPEN,
            owner=owner,
            related_event_ids=related_event_ids or [],
            detected_at=now,
            timeline=[TimelineEntry(at=now, status=IncidentStatus.OPEN, note="opened", actor=owner)],
            created_at=now,
            updated_at=now,
        )
        return self.repo.add(incident)

    # -- lifecycle ----------------------------------------------------------

    def _append(self, incident: Incident, status: IncidentStatus, note: str, actor: str) -> None:
        now = self._clock.now()
        incident.timeline.append(
            TimelineEntry(at=now, status=status, note=note, actor=actor)
        )
        incident.status = status
        incident.touch(now)
        self.repo.update(incident)

    def assign(self, tenant_id: str, incident_id: str, owner: str) -> Incident:
        """Assign an owner to an incident."""
        incident = self.repo.require(incident_id, tenant_id=tenant_id)
        incident.owner = owner
        self._append(incident, incident.status, f"assigned to {owner}", owner)
        return incident

    def escalate(self, tenant_id: str, incident_id: str, *, actor: str = "") -> Incident:
        """Escalate an incident's severity one level."""
        incident = self.repo.require(incident_id, tenant_id=tenant_id)
        incident.severity = _ESCALATION[incident.severity]
        incident.escalated = True
        self._append(
            incident, incident.status,
            f"escalated to {incident.severity.value}", actor,
        )
        return incident

    def update_status(
        self, tenant_id: str, incident_id: str, status: IncidentStatus,
        *, note: str = "", actor: str = "",
    ) -> Incident:
        """Transition an incident to a new status (recorded on the timeline)."""
        incident = self.repo.require(incident_id, tenant_id=tenant_id)
        self._append(incident, status, note, actor)
        return incident

    def set_root_cause(self, tenant_id: str, incident_id: str, root_cause: str) -> Incident:
        """Record the root cause of an incident."""
        incident = self.repo.require(incident_id, tenant_id=tenant_id)
        incident.root_cause = root_cause
        self._append(incident, IncidentStatus.IDENTIFIED, "root cause identified", incident.owner)
        return incident

    def resolve(
        self, tenant_id: str, incident_id: str, *, resolution: str, actor: str = ""
    ) -> Incident:
        """Resolve an incident with a resolution note."""
        incident = self.repo.require(incident_id, tenant_id=tenant_id)
        incident.resolution = resolution
        incident.resolved_at = self._clock.now()
        self._append(incident, IncidentStatus.RESOLVED, resolution, actor)
        return incident

    def close(self, tenant_id: str, incident_id: str, *, actor: str = "") -> Incident:
        """Close a resolved incident."""
        incident = self.repo.require(incident_id, tenant_id=tenant_id)
        self._append(incident, IncidentStatus.CLOSED, "closed", actor)
        return incident

    # -- queries ------------------------------------------------------------

    def get(self, tenant_id: str, incident_id: str) -> Incident:
        """Return one incident (tenant-isolated)."""
        return self.repo.require(incident_id, tenant_id=tenant_id)

    def list(
        self, tenant_id: str, *, open_only: bool = False
    ) -> list[Incident]:
        """Return a tenant's incidents."""
        where = (lambda i: i.is_open) if open_only else None
        return self.repo.list(tenant_id=tenant_id, where=where)

    def report(self, tenant_id: str) -> dict[str, object]:
        """Return an incident summary report for a tenant."""
        incidents = self.list(tenant_id)
        by_status: dict[str, int] = {}
        by_severity: dict[str, int] = {}
        for incident in incidents:
            by_status[incident.status.value] = by_status.get(incident.status.value, 0) + 1
            by_severity[incident.severity.value] = by_severity.get(incident.severity.value, 0) + 1
        return {
            "total": len(incidents),
            "open": sum(1 for i in incidents if i.is_open),
            "escalated": sum(1 for i in incidents if i.escalated),
            "by_status": by_status,
            "by_severity": by_severity,
        }
