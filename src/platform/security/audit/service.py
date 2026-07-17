"""Enterprise audit service (Module 3).

Records immutable, per-tenant hash-chained audit entries across every domain,
and provides correlation-aware search/filtering plus retention policies. The
chain links each entry to the previous one's hash, so any mutation of history is
detectable via :meth:`verify_chain`. Deterministic and clock-driven.
"""

from __future__ import annotations

import hashlib
from datetime import datetime

from src.platform.common.clock import Clock, SystemClock
from src.platform.common.ids import generate_id
from src.platform.common.models import Metadata
from src.platform.common.repository import InMemoryRepository
from src.platform.security.audit.models import (
    AuditEntry,
    AuditEventType,
    AuditOutcome,
    RetentionPolicy,
)
from src.platform.security.common.models import Severity


class EnterpriseAuditService:
    """Central, hash-chained, tenant-isolated audit log with retention."""

    def __init__(
        self,
        *,
        repository: InMemoryRepository[AuditEntry] | None = None,
        clock: Clock | None = None,
    ) -> None:
        self._clock = clock or SystemClock()
        self.repo: InMemoryRepository[AuditEntry] = repository or InMemoryRepository("audit_entry")
        self._sequence: dict[str, int] = {}
        self._retention: dict[str, RetentionPolicy] = {}

    # -- recording ----------------------------------------------------------

    def _entries_for(self, tenant_id: str) -> list[AuditEntry]:
        return sorted(self.repo.list(tenant_id=tenant_id), key=lambda e: e.sequence)

    @staticmethod
    def _compute_hash(entry: AuditEntry) -> str:
        payload = "|".join(
            [
                entry.tenant_id,
                str(entry.sequence),
                entry.event_type.value,
                entry.action,
                entry.actor_id,
                entry.resource_type,
                entry.resource_id,
                entry.correlation_id,
                entry.outcome.value,
                entry.prev_hash,
            ]
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def record(
        self,
        tenant_id: str,
        organization_id: str,
        event_type: AuditEventType,
        action: str,
        *,
        actor_id: str = "system",
        resource_type: str = "",
        resource_id: str = "",
        correlation_id: str = "",
        outcome: AuditOutcome = AuditOutcome.SUCCESS,
        severity: Severity = Severity.INFO,
        source: str = "",
        metadata: dict[str, object] | None = None,
    ) -> AuditEntry:
        """Append an immutable, hash-chained audit entry for a tenant."""
        seq = self._sequence.get(tenant_id, 0) + 1
        self._sequence[tenant_id] = seq
        existing = self._entries_for(tenant_id)
        prev_hash = existing[-1].hash if existing else ""
        now = self._clock.now()
        entry = AuditEntry(
            id=generate_id("aud"),
            tenant_id=tenant_id,
            organization_id=organization_id,
            sequence=seq,
            event_type=event_type,
            action=action,
            actor_id=actor_id,
            resource_type=resource_type,
            resource_id=resource_id,
            correlation_id=correlation_id or generate_id("corr"),
            outcome=outcome,
            severity=severity,
            source=source,
            metadata=Metadata(values=metadata or {}),
            prev_hash=prev_hash,
            created_at=now,
            updated_at=now,
        )
        entry.hash = self._compute_hash(entry)
        return self.repo.add(entry)

    # -- search & filter ----------------------------------------------------

    def search(
        self,
        tenant_id: str,
        *,
        event_type: AuditEventType | None = None,
        actor_id: str | None = None,
        outcome: AuditOutcome | None = None,
        correlation_id: str | None = None,
        action_contains: str | None = None,
        limit: int = 200,
    ) -> list[AuditEntry]:
        """Return matching entries, newest first."""

        def _predicate(entry: AuditEntry) -> bool:
            if event_type is not None and entry.event_type != event_type:
                return False
            if actor_id is not None and entry.actor_id != actor_id:
                return False
            if outcome is not None and entry.outcome != outcome:
                return False
            if correlation_id is not None and entry.correlation_id != correlation_id:
                return False
            if action_contains is not None and action_contains not in entry.action:
                return False
            return True

        rows = self.repo.list(tenant_id=tenant_id, where=_predicate)
        rows.sort(key=lambda e: e.sequence, reverse=True)
        return rows[:limit]

    def by_correlation(self, tenant_id: str, correlation_id: str) -> list[AuditEntry]:
        """Return every entry sharing a correlation id (chronological order)."""
        rows = self.repo.list(
            tenant_id=tenant_id, where=lambda e: e.correlation_id == correlation_id
        )
        rows.sort(key=lambda e: e.sequence)
        return rows

    # -- integrity & retention ---------------------------------------------

    def verify_chain(self, tenant_id: str) -> bool:
        """Return whether a tenant's audit chain is intact (untampered)."""
        prev_hash = ""
        for entry in self._entries_for(tenant_id):
            if entry.prev_hash != prev_hash:
                return False
            if entry.hash != self._compute_hash(entry):
                return False
            prev_hash = entry.hash
        return True

    def set_retention(
        self, tenant_id: str, organization_id: str, policy: RetentionPolicy
    ) -> RetentionPolicy:
        """Set the retention policy for a tenant."""
        self._retention[tenant_id] = policy
        return policy

    def apply_retention(self, tenant_id: str, *, now: datetime | None = None) -> int:
        """Delete entries older than their retention window; return count pruned."""
        policy = self._retention.get(tenant_id)
        if policy is None:
            return 0
        moment = now or self._clock.now()
        pruned = 0
        for entry in list(self._entries_for(tenant_id)):
            age_days = (moment - entry.created_at).days
            if age_days > policy.days_for(entry.event_type):
                self.repo.delete(entry.id, tenant_id=tenant_id)
                pruned += 1
        return pruned

    def count(self, tenant_id: str) -> int:
        """Return the number of audit entries for a tenant."""
        return self.repo.count(tenant_id=tenant_id)
