"""Module 2 tests — enterprise RBAC & ABAC.

Role hierarchy inheritance, permission groups, ABAC attribute conditions,
deny-overrides, default-deny, explainable decision reports and tenant isolation.
"""

from __future__ import annotations

from src.platform.common.clock import FrozenClock
from src.platform.security.authorization import (
    AttributeCondition,
    AttributeOperator,
    AuthorizationEngine,
    AuthorizationRequest,
    PolicyEffect,
)
from src.platform.security.common.models import Decision


def _engine() -> AuthorizationEngine:
    engine = AuthorizationEngine(clock=FrozenClock())
    engine.hierarchy.define_group("t1", "o1", "recruiting", ["candidate:read", "candidate:update"])
    engine.hierarchy.define_role("t1", "o1", "recruiter", groups=["recruiting"])
    engine.hierarchy.define_role(
        "t1", "o1", "hr_director", inherits=["recruiter"], permissions=["compensation:approve"]
    )
    return engine


def test_rbac_group_grant():
    engine = _engine()
    req = AuthorizationRequest(tenant_id="t1", roles=["recruiter"], permission="candidate:read")
    report = engine.evaluate(req)
    assert report.allowed and report.rbac_granted


def test_rbac_inheritance():
    engine = _engine()
    # hr_director inherits recruiter's group permissions.
    req = AuthorizationRequest(tenant_id="t1", roles=["hr_director"], permission="candidate:update")
    assert engine.is_allowed(req)
    # ...and has its own compensation:approve.
    req2 = AuthorizationRequest(
        tenant_id="t1", roles=["hr_director"], permission="compensation:approve"
    )
    assert engine.is_allowed(req2)


def test_default_deny():
    engine = _engine()
    req = AuthorizationRequest(tenant_id="t1", roles=["recruiter"], permission="billing:delete")
    report = engine.evaluate(req)
    assert report.decision == Decision.DENY
    assert "default deny" in " ".join(report.reasons)


def test_abac_allow_policy_grants_without_role():
    engine = _engine()
    engine.add_policy(
        "t1",
        "o1",
        "owner-can-read",
        effect=PolicyEffect.ALLOW,
        resource="report",
        action="read",
        conditions=[
            AttributeCondition(
                attribute="resource.owner", operator=AttributeOperator.EQ, value="alice"
            )
        ],
    )
    req = AuthorizationRequest(
        tenant_id="t1",
        subject="alice",
        roles=[],
        permission="report:read",
        resource_attributes={"owner": "alice"},
    )
    report = engine.evaluate(req)
    assert report.allowed
    assert any("ABAC allow" in r for r in report.reasons)


def test_abac_deny_overrides_rbac():
    engine = _engine()
    engine.add_policy(
        "t1",
        "o1",
        "no-offhours",
        effect=PolicyEffect.DENY,
        resource="candidate",
        action="update",
        conditions=[
            AttributeCondition(
                attribute="environment.after_hours", operator=AttributeOperator.EQ, value=True
            )
        ],
        priority=100,
    )
    req = AuthorizationRequest(
        tenant_id="t1",
        roles=["recruiter"],
        permission="candidate:update",
        environment={"after_hours": True},
    )
    report = engine.evaluate(req)
    assert report.decision == Decision.DENY
    assert "deny" in " ".join(report.reasons)


def test_abac_condition_not_met_falls_through_to_rbac():
    engine = _engine()
    engine.add_policy(
        "t1",
        "o1",
        "no-offhours",
        effect=PolicyEffect.DENY,
        resource="candidate",
        action="update",
        conditions=[
            AttributeCondition(
                attribute="environment.after_hours", operator=AttributeOperator.EQ, value=True
            )
        ],
    )
    req = AuthorizationRequest(
        tenant_id="t1",
        roles=["recruiter"],
        permission="candidate:update",
        environment={"after_hours": False},
    )
    assert engine.is_allowed(req)  # deny condition not met → RBAC grants


def test_policies_are_tenant_isolated():
    engine = _engine()
    engine.add_policy("t1", "o1", "p", effect=PolicyEffect.DENY, resource="*", action="*")
    # Tenant t2 has no policies, so its evaluation is unaffected.
    req = AuthorizationRequest(tenant_id="t2", roles=["recruiter"], permission="candidate:read")
    report = engine.evaluate(req)
    assert report.matched_policies == []
