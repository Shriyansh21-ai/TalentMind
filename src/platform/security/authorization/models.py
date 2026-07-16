"""Authorization models (Module 2 — RBAC & ABAC).

The vocabulary for enterprise authorization on top of the Milestone 1 RBAC
grammar (which is reused, not modified): permission groups, role-hierarchy
nodes, attribute-based access-control policies (target + conditions + effect),
the authorization request threaded through evaluation, and the decision report
returned. Policies and groups are tenant-scoped so isolation is preserved.
"""

from __future__ import annotations

from enum import Enum

from pydantic import Field

from src.platform.common.models import PlatformModel, TenantScopedEntity
from src.platform.security.common.models import Decision


class PolicyEffect(str, Enum):
    """The effect an ABAC policy asserts when it matches."""

    ALLOW = "allow"
    DENY = "deny"


class AttributeOperator(str, Enum):
    """The comparison an ABAC condition performs."""

    EQ = "eq"
    NE = "ne"
    IN = "in"
    NOT_IN = "not_in"
    GT = "gt"
    LT = "lt"
    CONTAINS = "contains"
    EXISTS = "exists"


class AttributeCondition(PlatformModel):
    """A single attribute test evaluated against the request's attribute bag.

    ``attribute`` is a dotted path into the flattened request attributes, e.g.
    ``identity.role``, ``resource.owner`` or ``environment.mfa``.
    """

    attribute: str
    operator: AttributeOperator = AttributeOperator.EQ
    value: object = None

    def evaluate(self, attributes: dict[str, object]) -> bool:
        """Return whether this condition holds for ``attributes``."""
        present = self.attribute in attributes
        actual = attributes.get(self.attribute)
        op = self.operator
        if op == AttributeOperator.EXISTS:
            return present
        if not present:
            return False
        if op == AttributeOperator.EQ:
            return actual == self.value
        if op == AttributeOperator.NE:
            return actual != self.value
        if op == AttributeOperator.IN:
            return actual in (self.value or [])
        if op == AttributeOperator.NOT_IN:
            return actual not in (self.value or [])
        if op == AttributeOperator.CONTAINS:
            try:
                return self.value in actual  # type: ignore[operator]
            except TypeError:
                return False
        if op in (AttributeOperator.GT, AttributeOperator.LT):
            try:
                if op == AttributeOperator.GT:
                    return actual > self.value  # type: ignore[operator]
                return actual < self.value  # type: ignore[operator]
            except TypeError:
                return False
        return False


class PermissionGroup(TenantScopedEntity):
    """A named, reusable bundle of ``resource:action`` permissions."""

    name: str
    permissions: list[str] = Field(default_factory=list)


class RoleNode(TenantScopedEntity):
    """A node in a tenant's role hierarchy.

    A role inherits the permissions of every role in ``inherits`` (transitively)
    plus the permissions of the groups it is assigned.
    """

    role: str
    inherits: list[str] = Field(default_factory=list)
    groups: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)


class AbacPolicy(TenantScopedEntity):
    """An attribute-based access-control policy (target + conditions + effect)."""

    name: str
    effect: PolicyEffect = PolicyEffect.ALLOW
    resource: str = "*"  # resource pattern (wildcards allowed)
    action: str = "*"  # action pattern (wildcards allowed)
    conditions: list[AttributeCondition] = Field(default_factory=list)
    priority: int = 0  # higher priority wins ties; DENY still overrides
    description: str = ""


class AuthorizationRequest(PlatformModel):
    """Everything an authorization decision is made from."""

    tenant_id: str
    subject: str = ""
    roles: list[str] = Field(default_factory=list)
    permission: str  # concrete "resource:action"
    resource_attributes: dict[str, object] = Field(default_factory=dict)
    identity_attributes: dict[str, object] = Field(default_factory=dict)
    environment: dict[str, object] = Field(default_factory=dict)

    def attribute_bag(self) -> dict[str, object]:
        """Flatten identity/resource/environment into dotted attribute keys."""
        bag: dict[str, object] = {"subject": self.subject, "roles": self.roles}
        for key, value in self.identity_attributes.items():
            bag[f"identity.{key}"] = value
        for key, value in self.resource_attributes.items():
            bag[f"resource.{key}"] = value
        for key, value in self.environment.items():
            bag[f"environment.{key}"] = value
        return bag


class PolicyMatch(PlatformModel):
    """A record of one policy that matched during evaluation."""

    policy_id: str
    name: str
    effect: PolicyEffect
    priority: int = 0


class DecisionReport(PlatformModel):
    """A structured, explainable authorization decision."""

    decision: Decision = Decision.DENY
    permission: str = ""
    subject: str = ""
    rbac_granted: bool = False
    matched_policies: list[PolicyMatch] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)

    @property
    def allowed(self) -> bool:
        """Return whether the decision permits the action."""
        return self.decision == Decision.ALLOW
