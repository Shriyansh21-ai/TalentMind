"""Module 2 — Enterprise RBAC & ABAC.

Role hierarchies, permission groups and inheritance (RBAC) plus attribute-based
policies (ABAC), combined by a deny-overrides, default-deny
:class:`AuthorizationEngine` that produces explainable decision reports. Reuses
the Milestone 1 permission grammar without modifying it.
"""

from __future__ import annotations

from src.platform.security.authorization.abac import AbacEngine
from src.platform.security.authorization.engine import AuthorizationEngine
from src.platform.security.authorization.models import (
    AbacPolicy,
    AttributeCondition,
    AttributeOperator,
    AuthorizationRequest,
    DecisionReport,
    PermissionGroup,
    PolicyEffect,
    PolicyMatch,
    RoleNode,
)
from src.platform.security.authorization.rbac import RoleHierarchy

__all__ = [
    "PolicyEffect",
    "AttributeOperator",
    "AttributeCondition",
    "PermissionGroup",
    "RoleNode",
    "AbacPolicy",
    "AuthorizationRequest",
    "PolicyMatch",
    "DecisionReport",
    "RoleHierarchy",
    "AbacEngine",
    "AuthorizationEngine",
]
