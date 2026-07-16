"""Module 4 — Role-Based Access Control.

Enterprise RBAC with twelve built-in roles (Platform Admin → Guest), a granular
``resource:action`` permission vocabulary with wildcard support, and scoped
grants (platform / organization / workspace / resource) enabling workspace-level
and resource-level access control. A pure :class:`PolicyEngine` makes every
decision; :class:`AccessControlService` is the public entry point.
"""

from __future__ import annotations

from src.platform.rbac.models import AccessRequest, RoleAssignment, RoleDefinition
from src.platform.rbac.permissions import (
    Action,
    Resource,
    all_permissions,
    matches,
    permission,
)
from src.platform.rbac.policy import PolicyEngine
from src.platform.rbac.roles import (
    DEFAULT_ROLE_PERMISSIONS,
    Role,
    ScopeType,
)
from src.platform.rbac.service import AccessControlService, build_default_definitions

__all__ = [
    "Role",
    "ScopeType",
    "Resource",
    "Action",
    "permission",
    "matches",
    "all_permissions",
    "DEFAULT_ROLE_PERMISSIONS",
    "RoleDefinition",
    "RoleAssignment",
    "AccessRequest",
    "PolicyEngine",
    "AccessControlService",
    "build_default_definitions",
]
