"""RBAC entities (Module 4).

A :class:`RoleDefinition` is the (data-driven) mapping from a role to its
permissions. A :class:`RoleAssignment` grants a role to a principal at a
particular scope (platform / organization / workspace / resource), enabling
workspace-level and resource-level access control on top of the global role.
"""

from __future__ import annotations

from pydantic import Field

from src.platform.common.models import Entity, PlatformModel, TenantScopedEntity
from src.platform.rbac.roles import ScopeType


class RoleDefinition(Entity):
    """The permissions a role confers.

    Built-in roles are seeded from ``DEFAULT_ROLE_PERMISSIONS``; ``is_custom``
    marks organization-defined roles added at runtime.
    """

    role: str
    description: str = ""
    permissions: list[str] = Field(default_factory=list)
    is_custom: bool = False


class RoleAssignment(TenantScopedEntity):
    """A grant of a role to a principal at a scope.

    Attributes:
        principal_id: The user id the role is granted to.
        role: The role name (see :class:`Role`).
        scope_type: The level of the grant.
        scope_id: The id of the scope target (workspace/resource id); ``None``
            for platform/organization scope.
        granted_by: The principal id that created the grant (for audit).
    """

    principal_id: str
    role: str
    scope_type: ScopeType = ScopeType.ORGANIZATION
    scope_id: str | None = None
    granted_by: str | None = None


class AccessRequest(PlatformModel):
    """A transient permission-check request against a target scope."""

    tenant_id: str
    principal_id: str
    permission: str
    workspace_id: str | None = None
    resource_id: str | None = None
