"""Access-control service (Module 4).

The public RBAC entry point: seed built-in role definitions, grant/revoke role
assignments (tenant-scoped), and answer authorization questions
(:meth:`is_allowed` / :meth:`authorize`). Everything routes through the pure
:class:`PolicyEngine`, so the decision logic stays testable in isolation.
"""

from __future__ import annotations

from src.platform.common.clock import Clock, SystemClock
from src.platform.common.errors import PermissionDeniedError, PlatformValidationError
from src.platform.common.ids import generate_id
from src.platform.common.repository import InMemoryRepository
from src.platform.rbac.models import AccessRequest, RoleAssignment, RoleDefinition
from src.platform.rbac.policy import PolicyEngine
from src.platform.rbac.roles import (
    DEFAULT_ROLE_PERMISSIONS,
    PLATFORM_ONLY_ROLES,
    Role,
    ScopeType,
)


def build_default_definitions() -> dict[str, RoleDefinition]:
    """Return the built-in role definitions keyed by role name."""
    definitions: dict[str, RoleDefinition] = {}
    for role, perms in DEFAULT_ROLE_PERMISSIONS.items():
        definitions[role.value] = RoleDefinition(
            id=generate_id("roledef"),
            role=role.value,
            description=f"Built-in {role.value} role",
            permissions=list(perms),
        )
    return definitions


class AccessControlService:
    """Grant roles and evaluate authorization decisions."""

    def __init__(
        self,
        *,
        assignments: InMemoryRepository[RoleAssignment] | None = None,
        definitions: dict[str, RoleDefinition] | None = None,
        clock: Clock | None = None,
    ) -> None:
        self._clock = clock or SystemClock()
        self.assignments: InMemoryRepository[RoleAssignment] = assignments or InMemoryRepository(
            "role_assignment"
        )
        self.definitions = definitions or build_default_definitions()
        self.engine = PolicyEngine(self.definitions)

    # -- role catalogue -----------------------------------------------------

    def define_custom_role(
        self, role_name: str, permissions: list[str], *, description: str = ""
    ) -> RoleDefinition:
        """Register an organization-defined custom role (future-ready)."""
        if role_name in self.definitions:
            raise PlatformValidationError(f"role '{role_name}' already defined")
        definition = RoleDefinition(
            id=generate_id("roledef"),
            role=role_name,
            description=description,
            permissions=list(permissions),
            is_custom=True,
        )
        self.definitions[role_name] = definition
        self.engine = PolicyEngine(self.definitions)  # refresh engine view
        return definition

    # -- grants -------------------------------------------------------------

    def assign(
        self,
        tenant_id: str,
        organization_id: str,
        principal_id: str,
        role: Role | str,
        *,
        scope_type: ScopeType = ScopeType.ORGANIZATION,
        scope_id: str | None = None,
        granted_by: str | None = None,
    ) -> RoleAssignment:
        """Grant ``role`` to a principal at a scope.

        Raises:
            PlatformValidationError: If the role is unknown, or a platform-only
                role is granted below platform scope.
        """
        role_name = role.value if isinstance(role, Role) else role
        if role_name not in self.definitions:
            raise PlatformValidationError(f"unknown role '{role_name}'")
        if role_name in {r.value for r in PLATFORM_ONLY_ROLES} and (
            scope_type != ScopeType.PLATFORM
        ):
            raise PlatformValidationError(
                f"role '{role_name}' may only be granted at platform scope"
            )
        now = self._clock.now()
        assignment = RoleAssignment(
            id=generate_id("grant"),
            tenant_id=tenant_id,
            organization_id=organization_id,
            principal_id=principal_id,
            role=role_name,
            scope_type=scope_type,
            scope_id=scope_id,
            granted_by=granted_by,
            created_at=now,
            updated_at=now,
        )
        return self.assignments.add(assignment)

    def revoke(self, tenant_id: str, assignment_id: str) -> None:
        """Revoke a role assignment (tenant-isolation checked)."""
        self.assignments.delete(assignment_id, tenant_id=tenant_id)

    def assignments_for(self, tenant_id: str, principal_id: str) -> list[RoleAssignment]:
        """Return every assignment a principal holds within a tenant."""
        return self.assignments.list(
            tenant_id=tenant_id, where=lambda a: a.principal_id == principal_id
        )

    # -- decisions ----------------------------------------------------------

    def is_allowed(self, request: AccessRequest) -> bool:
        """Return whether ``request.principal_id`` may perform the permission."""
        assignments = self.assignments_for(request.tenant_id, request.principal_id)
        return self.engine.is_allowed(assignments, request)

    def authorize(self, request: AccessRequest) -> None:
        """Raise :class:`PermissionDeniedError` unless the request is allowed."""
        if not self.is_allowed(request):
            raise PermissionDeniedError(
                f"principal '{request.principal_id}' lacks '{request.permission}'"
            )

    def effective_permissions(
        self,
        tenant_id: str,
        principal_id: str,
        *,
        workspace_id: str | None = None,
        resource_id: str | None = None,
    ) -> set[str]:
        """Return a principal's effective permissions at an optional scope."""
        assignments = self.assignments_for(tenant_id, principal_id)
        probe = AccessRequest(
            tenant_id=tenant_id,
            principal_id=principal_id,
            permission="*:*",
            workspace_id=workspace_id,
            resource_id=resource_id,
        )
        scoped = None if (workspace_id is None and resource_id is None) else probe
        return self.engine.effective_permissions(assignments, scoped)
