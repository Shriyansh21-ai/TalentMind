"""Module 3 tests — enterprise audit platform.

Hash-chained immutability + tamper detection, correlation, search/filtering,
retention policies and tenant isolation.
"""

from __future__ import annotations

from src.platform.common.clock import FrozenClock
from src.platform.security.audit import (
    AuditEventType,
    AuditOutcome,
    EnterpriseAuditService,
    RetentionPolicy,
)


def _service() -> EnterpriseAuditService:
    return EnterpriseAuditService(clock=FrozenClock())


def test_hash_chain_is_intact():
    svc = _service()
    svc.record("t1", "o1", AuditEventType.AUTHENTICATION, "login")
    svc.record("t1", "o1", AuditEventType.AUTHORIZATION, "access")
    assert svc.verify_chain("t1")
    assert svc.count("t1") == 2


def test_tampering_is_detected():
    svc = _service()
    e1 = svc.record("t1", "o1", AuditEventType.AUTHENTICATION, "login")
    svc.record("t1", "o1", AuditEventType.SECURITY, "alert")
    e1.action = "TAMPERED"
    svc.repo.update(e1)
    assert not svc.verify_chain("t1")


def test_search_and_filter():
    svc = _service()
    svc.record("t1", "o1", AuditEventType.AUTHENTICATION, "login", actor_id="alice")
    svc.record(
        "t1",
        "o1",
        AuditEventType.SECURITY,
        "threat",
        actor_id="system",
        outcome=AuditOutcome.FAILURE,
    )
    assert len(svc.search("t1", event_type=AuditEventType.AUTHENTICATION)) == 1
    assert len(svc.search("t1", actor_id="alice")) == 1
    assert len(svc.search("t1", outcome=AuditOutcome.FAILURE)) == 1


def test_correlation_groups_entries():
    svc = _service()
    first = svc.record("t1", "o1", AuditEventType.AUTHENTICATION, "login")
    svc.record(
        "t1", "o1", AuditEventType.AUTHORIZATION, "access", correlation_id=first.correlation_id
    )
    correlated = svc.by_correlation("t1", first.correlation_id)
    assert len(correlated) == 2


def test_retention_prunes_old_entries():
    clock = FrozenClock()
    svc = EnterpriseAuditService(clock=clock)
    svc.record("t1", "o1", AuditEventType.PLATFORM, "old.event")
    svc.set_retention(
        "t1", "o1", RetentionPolicy(id="r", tenant_id="t1", organization_id="o1", default_days=30)
    )
    clock.advance(days=40)
    svc.record("t1", "o1", AuditEventType.PLATFORM, "new.event")
    pruned = svc.apply_retention("t1")
    assert pruned == 1
    assert svc.count("t1") == 1


def test_chains_are_independent_per_tenant():
    svc = _service()
    svc.record("t1", "o1", AuditEventType.PLATFORM, "a")
    svc.record("t2", "o2", AuditEventType.PLATFORM, "b")
    assert svc.verify_chain("t1")
    assert svc.verify_chain("t2")
    assert svc.count("t1") == 1 and svc.count("t2") == 1
