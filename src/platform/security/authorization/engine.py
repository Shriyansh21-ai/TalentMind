"""Authorization engine (Module 2 — combined RBAC + ABAC).

The single decision point. It combines the role hierarchy (RBAC) with the
attribute-based policies (ABAC) using a **deny-overrides**, **default-deny**
algorithm and produces an explainable :class:`DecisionReport`:

1. An explicit ABAC **DENY** that matches always denies (deny-overrides).
2. Otherwise, an ABAC **ALLOW** that matches, *or* RBAC granting the permission
   through the role hierarchy, allows.
3. Otherwise, deny (least privilege).

Policies and role definitions are tenant-scoped, so a decision for one tenant
can never be influenced by another's rules.
"""

from __future__ import annotations

from src.platform.common.clock import Clock, SystemClock
from src.platform.common.ids import generate_id
from src.platform.common.repository import InMemoryRepository
from src.platform.security.authorization.abac import AbacEngine
from src.platform.security.authorization.models import (
    AbacPolicy,
    AttributeCondition,
    AuthorizationRequest,
    DecisionReport,
    PolicyEffect,
)
from src.platform.security.authorization.rbac import RoleHierarchy
from src.platform.security.common.models import Decision


class AuthorizationEngine:
    """Combines RBAC and ABAC into one explainable, tenant-isolated decision."""

    def __init__(
        self,
        *,
        hierarchy: RoleHierarchy | None = None,
        clock: Clock | None = None,
    ) -> None:
        self._clock = clock or SystemClock()
        self.hierarchy = hierarchy or RoleHierarchy(clock=self._clock)
        self.abac = AbacEngine()
        self.policies: InMemoryRepository[AbacPolicy] = InMemoryRepository("abac_policy")

    # -- policy management --------------------------------------------------

    def add_policy(
        self,
        tenant_id: str,
        organization_id: str,
        name: str,
        *,
        effect: PolicyEffect = PolicyEffect.ALLOW,
        resource: str = "*",
        action: str = "*",
        conditions: list[AttributeCondition] | None = None,
        priority: int = 0,
        description: str = "",
    ) -> AbacPolicy:
        """Register an ABAC policy for a tenant."""
        now = self._clock.now()
        policy = AbacPolicy(
            id=generate_id("pol"),
            tenant_id=tenant_id,
            organization_id=organization_id,
            name=name,
            effect=effect,
            resource=resource,
            action=action,
            conditions=conditions or [],
            priority=priority,
            description=description,
            created_at=now,
            updated_at=now,
        )
        return self.policies.add(policy)

    def policies_for(self, tenant_id: str) -> list[AbacPolicy]:
        """Return a tenant's ABAC policies."""
        return self.policies.list(tenant_id=tenant_id)

    # -- decision -----------------------------------------------------------

    def evaluate(self, request: AuthorizationRequest) -> DecisionReport:
        """Return an explainable authorization decision for ``request``."""
        report = DecisionReport(permission=request.permission, subject=request.subject)

        matched = self.abac.evaluate(request, self.policies_for(request.tenant_id))
        report.matched_policies = matched
        combined = AbacEngine.combined_effect(matched)

        # 1. Deny-overrides.
        if combined == PolicyEffect.DENY:
            report.decision = Decision.DENY
            report.reasons.append("explicit ABAC deny policy matched")
            return report

        # 2. RBAC grant.
        report.rbac_granted = self.hierarchy.grants(
            request.tenant_id, request.roles, request.permission
        )
        if report.rbac_granted:
            report.reasons.append("granted by role hierarchy (RBAC)")

        # 3. ABAC allow.
        abac_allow = combined == PolicyEffect.ALLOW
        if abac_allow:
            report.reasons.append("granted by ABAC allow policy")

        if report.rbac_granted or abac_allow:
            report.decision = Decision.ALLOW
        else:
            report.decision = Decision.DENY
            report.reasons.append("no grant found — default deny (least privilege)")
        return report

    def is_allowed(self, request: AuthorizationRequest) -> bool:
        """Return whether ``request`` is permitted."""
        return self.evaluate(request).allowed
