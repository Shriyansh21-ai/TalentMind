"""RBAC policy engine (Module 4 / Module 15).

Pure, side-effect-free decision logic: given a principal's role assignments and
the definitions those roles resolve to, decide whether a concrete permission is
allowed at a target scope. Defaults to **deny** (least privilege / Zero Trust);
an allow only results from an explicit matching grant whose scope covers the
target.
"""

from __future__ import annotations

from src.platform.rbac.models import AccessRequest, RoleAssignment, RoleDefinition
from src.platform.rbac.permissions import matches
from src.platform.rbac.roles import ScopeType


class PolicyEngine:
    """Evaluate access decisions from role assignments + definitions."""

    def __init__(self, definitions: dict[str, RoleDefinition]) -> None:
        # Keyed by role name for O(1) resolution.
        self._definitions = definitions

    def permissions_for_role(self, role: str) -> list[str]:
        """Return the permission strings a role confers (empty if unknown)."""
        definition = self._definitions.get(role)
        return list(definition.permissions) if definition else []

    def _scope_covers(self, assignment: RoleAssignment, request: AccessRequest) -> bool:
        """Return whether an assignment's scope covers the requested target."""
        scope = assignment.scope_type
        if scope == ScopeType.PLATFORM:
            return True
        if scope == ScopeType.ORGANIZATION:
            # Org grants cover every target inside the same tenant/org.
            return True
        if scope == ScopeType.WORKSPACE:
            # Covers the workspace itself or any resource within it.
            return assignment.scope_id is not None and assignment.scope_id in (
                request.workspace_id,
                request.resource_id,
            )
        if scope == ScopeType.RESOURCE:
            return assignment.scope_id is not None and (
                assignment.scope_id == request.resource_id
            )
        return False

    def effective_permissions(
        self, assignments: list[RoleAssignment], request: AccessRequest | None = None
    ) -> set[str]:
        """Return the union of granted permissions.

        If ``request`` is provided, only assignments whose scope covers the
        request's target contribute — giving the *effective* permission set at
        that scope. Otherwise every assignment contributes.
        """
        granted: set[str] = set()
        for assignment in assignments:
            if request is not None and not self._scope_covers(assignment, request):
                continue
            granted.update(self.permissions_for_role(assignment.role))
        return granted

    def is_allowed(
        self, assignments: list[RoleAssignment], request: AccessRequest
    ) -> bool:
        """Return whether any scoped assignment grants the requested permission."""
        for assignment in assignments:
            if not self._scope_covers(assignment, request):
                continue
            for granted in self.permissions_for_role(assignment.role):
                if matches(granted, request.permission):
                    return True
        return False
