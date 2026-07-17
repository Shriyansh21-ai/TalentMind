"""Platform audit service (Module 9).

Records tamper-evident audit events into a per-tenant hash chain and answers
audit queries. Each event's ``hash`` is derived from the previous event's hash
plus its own content, so any later mutation or deletion breaks the chain and is
caught by :meth:`verify_chain` — the basis for future compliance attestations.
"""

from __future__ import annotations

import hashlib

from src.platform.audit.models import AuditCategory, AuditEvent, AuditOutcome
from src.platform.audit.sink import AuditSink
from src.platform.common.clock import Clock, SystemClock
from src.platform.common.ids import generate_id
from src.platform.common.models import Metadata
from src.platform.common.repository import InMemoryRepository


class PlatformAuditService:
    """Append-only, hash-chained platform audit log."""

    def __init__(
        self,
        *,
        repository: InMemoryRepository[AuditEvent] | None = None,
        sinks: list[AuditSink] | None = None,
        clock: Clock | None = None,
    ) -> None:
        self.repo = repository or InMemoryRepository("audit_event")
        self._sinks = list(sinks or [])
        self._clock = clock or SystemClock()

    def add_sink(self, sink: AuditSink) -> None:
        """Register an additional fan-out sink."""
        self._sinks.append(sink)

    # -- recording ----------------------------------------------------------

    def _chain_tip(self, tenant_id: str) -> tuple[int, str]:
        """Return the current ``(sequence, hash)`` tip for a tenant's chain."""
        events = self.repo.list(tenant_id=tenant_id)
        if not events:
            return 0, ""
        last = events[-1]
        return last.sequence, last.hash

    @staticmethod
    def _digest(event: AuditEvent) -> str:
        """Compute the chain hash for an event from its content + prev_hash."""
        material = "|".join(
            [
                event.prev_hash,
                str(event.sequence),
                event.tenant_id,
                event.category.value,
                event.action,
                event.actor_id,
                event.target_type,
                event.target_id,
                event.outcome.value,
                event.created_at.isoformat(),
            ]
        )
        return hashlib.sha256(material.encode("utf-8")).hexdigest()

    def record(
        self,
        tenant_id: str,
        organization_id: str,
        category: AuditCategory,
        action: str,
        *,
        actor_id: str = "system",
        target_type: str = "",
        target_id: str = "",
        outcome: AuditOutcome = AuditOutcome.SUCCESS,
        ip_address: str = "",
        metadata: dict[str, object] | None = None,
    ) -> AuditEvent:
        """Append an audit event to the tenant's chain and fan out to sinks."""
        prev_seq, prev_hash = self._chain_tip(tenant_id)
        now = self._clock.now()
        event = AuditEvent(
            id=generate_id("audit"),
            tenant_id=tenant_id,
            organization_id=organization_id,
            sequence=prev_seq + 1,
            category=category,
            action=action,
            actor_id=actor_id,
            target_type=target_type,
            target_id=target_id,
            outcome=outcome,
            ip_address=ip_address,
            metadata=Metadata(values=dict(metadata or {})),
            prev_hash=prev_hash,
            created_at=now,
            updated_at=now,
        )
        event.hash = self._digest(event)
        self.repo.add(event)
        for sink in self._sinks:
            sink.emit(event)
        return event

    # -- querying -----------------------------------------------------------

    def query(
        self,
        tenant_id: str,
        *,
        category: AuditCategory | None = None,
        actor_id: str | None = None,
        outcome: AuditOutcome | None = None,
    ) -> list[AuditEvent]:
        """Return matching events for a tenant, in chain order."""

        def _match(e: AuditEvent) -> bool:
            if category is not None and e.category != category:
                return False
            if actor_id is not None and e.actor_id != actor_id:
                return False
            if outcome is not None and e.outcome != outcome:
                return False
            return True

        return self.repo.list(tenant_id=tenant_id, where=_match)

    def recent(self, tenant_id: str, limit: int = 50) -> list[AuditEvent]:
        """Return the most recent events for a tenant (newest first)."""
        events = self.repo.list(tenant_id=tenant_id)
        return list(reversed(events))[:limit]

    def verify_chain(self, tenant_id: str) -> bool:
        """Return whether a tenant's audit chain is intact (untampered)."""
        prev_hash = ""
        expected_seq = 1
        for event in self.repo.list(tenant_id=tenant_id):
            if event.sequence != expected_seq or event.prev_hash != prev_hash:
                return False
            if event.hash != self._digest(event):
                return False
            prev_hash = event.hash
            expected_seq += 1
        return True
