"""Governance service (Module 7).

A policy registry + evaluation engine. Each policy's rules are required
attribute conditions; a policy is compliant when all its rules hold (or an
active exception waives it). :meth:`enforce` raises on a violated ENFORCE
policy; WARN/AUDIT policies only report. Produces explainable
:class:`PolicyReport` objects. Tenant-isolated and clock-driven.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from src.platform.common.clock import Clock, SystemClock
from src.platform.common.ids import generate_id
from src.platform.common.repository import InMemoryRepository
from src.platform.security.common.errors import PolicyViolationError
from src.platform.security.common.models import Decision
from src.platform.security.governance.models import (
    Enforcement,
    GovernanceDomain,
    GovernanceException,
    GovernancePolicy,
    GovernanceRule,
    PolicyReport,
    RuleViolation,
)


class GovernanceService:
    """Register, evaluate and enforce governance policies."""

    def __init__(self, *, clock: Clock | None = None) -> None:
        self._clock = clock or SystemClock()
        self.policies: InMemoryRepository[GovernancePolicy] = InMemoryRepository(
            "governance_policy"
        )
        self.exceptions: InMemoryRepository[GovernanceException] = InMemoryRepository(
            "governance_exception"
        )

    # -- registry -----------------------------------------------------------

    def register_policy(
        self,
        tenant_id: str,
        organization_id: str,
        name: str,
        *,
        domain: GovernanceDomain = GovernanceDomain.OPERATIONAL,
        enforcement: Enforcement = Enforcement.ENFORCE,
        rules: list[GovernanceRule] | None = None,
        requires_approval: bool = False,
        approvers: list[str] | None = None,
        description: str = "",
    ) -> GovernancePolicy:
        """Register a governance policy for a tenant."""
        now = self._clock.now()
        policy = GovernancePolicy(
            id=generate_id("gov"),
            tenant_id=tenant_id,
            organization_id=organization_id,
            name=name,
            domain=domain,
            enforcement=enforcement,
            rules=rules or [],
            requires_approval=requires_approval,
            approvers=approvers or [],
            description=description,
            created_at=now,
            updated_at=now,
        )
        return self.policies.add(policy)

    def grant_exception(
        self,
        tenant_id: str,
        organization_id: str,
        policy_id: str,
        *,
        reason: str,
        approved_by: str,
        ttl_days: int | None = None,
    ) -> GovernanceException:
        """Grant a time-bounded, approved waiver for a policy."""
        now = self._clock.now()
        exception = GovernanceException(
            id=generate_id("govexc"),
            tenant_id=tenant_id,
            organization_id=organization_id,
            policy_id=policy_id,
            reason=reason,
            approved_by=approved_by,
            expires_at=(now + timedelta(days=ttl_days)) if ttl_days else None,
            created_at=now,
            updated_at=now,
        )
        return self.exceptions.add(exception)

    def policies_for(
        self, tenant_id: str, *, domain: GovernanceDomain | None = None
    ) -> list[GovernancePolicy]:
        """Return a tenant's policies, optionally by domain."""
        where = None
        if domain is not None:
            where = lambda p: p.domain == domain  # noqa: E731
        return self.policies.list(tenant_id=tenant_id, where=where)

    # -- evaluation ---------------------------------------------------------

    def _active_exception(self, tenant_id: str, policy_id: str) -> bool:
        now = self._clock.now()
        return any(
            e.is_active(now)
            for e in self.exceptions.list(
                tenant_id=tenant_id, where=lambda e: e.policy_id == policy_id
            )
        )

    def evaluate_policy(
        self, policy: GovernancePolicy, attributes: dict[str, object]
    ) -> PolicyReport:
        """Evaluate one policy against ``attributes`` (an ABAC attribute bag)."""
        violations = [
            RuleViolation(
                rule_key=rule.key,
                description=rule.description,
                remediation=rule.remediation,
            )
            for rule in policy.rules
            if not rule.condition.evaluate(attributes)
        ]
        waived = bool(violations) and self._active_exception(policy.tenant_id, policy.id)
        compliant = not violations or waived
        report = PolicyReport(
            policy_id=policy.id,
            name=policy.name,
            domain=policy.domain,
            enforcement=policy.enforcement,
            compliant=compliant,
            waived=waived,
            violations=violations,
            decision=Decision.ALLOW if compliant else Decision.DENY,
        )
        return report

    def evaluate(
        self,
        tenant_id: str,
        attributes: dict[str, object],
        *,
        domain: GovernanceDomain | None = None,
    ) -> list[PolicyReport]:
        """Evaluate every enabled policy (optionally in a domain)."""
        reports: list[PolicyReport] = []
        for policy in self.policies_for(tenant_id, domain=domain):
            if not policy.enabled:
                continue
            reports.append(self.evaluate_policy(policy, attributes))
        return reports

    def enforce(
        self,
        tenant_id: str,
        attributes: dict[str, object],
        *,
        domain: GovernanceDomain | None = None,
    ) -> list[PolicyReport]:
        """Evaluate and raise if any ENFORCE policy is violated (unwaived)."""
        reports = self.evaluate(tenant_id, attributes, domain=domain)
        blocking = [
            r
            for r in reports
            if not r.compliant and r.enforcement == Enforcement.ENFORCE
        ]
        if blocking:
            names = ", ".join(r.name for r in blocking)
            raise PolicyViolationError(f"governance policy violated: {names}")
        return reports
