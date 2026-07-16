"""Modules 7 & 8 tests — governance and compliance.

Governance: policy evaluation, enforcement (raise on violation), time-bounded
exceptions. Compliance: standards catalogue, evidence collection, coverage
assessment and gap analysis.
"""

from __future__ import annotations

import pytest

from src.platform.common.clock import FrozenClock
from src.platform.security.authorization import AttributeCondition, AttributeOperator
from src.platform.security.common.errors import PolicyViolationError
from src.platform.security.compliance import ComplianceService, ComplianceStandard
from src.platform.security.governance import (
    Enforcement,
    GovernanceDomain,
    GovernanceRule,
    GovernanceService,
)


def _mfa_rule() -> GovernanceRule:
    return GovernanceRule(
        key="mfa",
        description="MFA required",
        condition=AttributeCondition(
            attribute="identity.mfa", operator=AttributeOperator.EQ, value=True
        ),
    )


# -- governance -------------------------------------------------------------


def test_policy_compliant_when_rules_hold():
    gov = GovernanceService(clock=FrozenClock())
    gov.register_policy("t1", "o1", "MFA", domain=GovernanceDomain.SECURITY, rules=[_mfa_rule()])
    reports = gov.evaluate("t1", {"identity.mfa": True})
    assert reports[0].compliant


def test_enforce_raises_on_violation():
    gov = GovernanceService(clock=FrozenClock())
    gov.register_policy("t1", "o1", "MFA", enforcement=Enforcement.ENFORCE, rules=[_mfa_rule()])
    with pytest.raises(PolicyViolationError):
        gov.enforce("t1", {"identity.mfa": False})


def test_warn_policy_does_not_raise():
    gov = GovernanceService(clock=FrozenClock())
    gov.register_policy("t1", "o1", "MFA", enforcement=Enforcement.WARN, rules=[_mfa_rule()])
    reports = gov.enforce("t1", {"identity.mfa": False})  # WARN → no raise
    assert not reports[0].compliant


def test_active_exception_waives_violation():
    gov = GovernanceService(clock=FrozenClock())
    policy = gov.register_policy("t1", "o1", "MFA", enforcement=Enforcement.ENFORCE, rules=[_mfa_rule()])
    gov.grant_exception("t1", "o1", policy.id, reason="legacy system", approved_by="ciso", ttl_days=30)
    reports = gov.enforce("t1", {"identity.mfa": False})  # waived, no raise
    assert reports[0].waived and reports[0].compliant


def test_expired_exception_no_longer_waives():
    clock = FrozenClock()
    gov = GovernanceService(clock=clock)
    policy = gov.register_policy("t1", "o1", "MFA", enforcement=Enforcement.ENFORCE, rules=[_mfa_rule()])
    gov.grant_exception("t1", "o1", policy.id, reason="temp", approved_by="ciso", ttl_days=1)
    clock.advance(days=2)
    with pytest.raises(PolicyViolationError):
        gov.enforce("t1", {"identity.mfa": False})


# -- compliance -------------------------------------------------------------


def test_all_standards_have_catalogues():
    comp = ComplianceService(clock=FrozenClock())
    assert len(comp.standards()) == 6
    for standard in comp.standards():
        assert len(comp.controls(standard)) > 0


def test_evidence_drives_coverage():
    comp = ComplianceService(clock=FrozenClock())
    controls = comp.controls(ComplianceStandard.SOC2)
    # Two pieces of evidence satisfies a control; one is partial.
    comp.collect_evidence("t1", "o1", ComplianceStandard.SOC2, controls[0].code)
    comp.collect_evidence("t1", "o1", ComplianceStandard.SOC2, controls[0].code)
    comp.collect_evidence("t1", "o1", ComplianceStandard.SOC2, controls[1].code)
    report = comp.assess("t1", ComplianceStandard.SOC2)
    assert report.satisfied == 1
    assert report.partial == 1
    assert 0 < report.coverage < 1


def test_gap_analysis_lists_unmet_controls():
    comp = ComplianceService(clock=FrozenClock())
    gaps = comp.gap_analysis("t1", ComplianceStandard.GDPR)
    # No evidence yet → every control is a gap.
    assert gaps.gap_count == len(comp.controls(ComplianceStandard.GDPR))
    assert len(gaps.recommendations) == gaps.gap_count
