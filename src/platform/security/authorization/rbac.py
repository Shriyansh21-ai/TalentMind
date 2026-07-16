"""Role hierarchy & permission groups (Module 2 — RBAC).

Adds role *hierarchies* and reusable *permission groups* on top of the Milestone
1 permission grammar (``resource:action`` with wildcards), which is reused
verbatim — the existing roles and permissions are untouched. A role's effective
permissions are its own permissions, plus those of every group it references,
plus (transitively) the permissions of every role it inherits.
"""

from __future__ import annotations

from src.platform.common.clock import Clock, SystemClock
from src.platform.common.ids import generate_id
from src.platform.common.repository import InMemoryRepository
from src.platform.rbac import matches  # reuse M1 permission-matching grammar
from src.platform.security.authorization.models import PermissionGroup, RoleNode


class RoleHierarchy:
    """Manages a tenant's role hierarchy and permission groups."""

    def __init__(self, *, clock: Clock | None = None) -> None:
        self._clock = clock or SystemClock()
        self.roles: InMemoryRepository[RoleNode] = InMemoryRepository("role_node")
        self.groups: InMemoryRepository[PermissionGroup] = InMemoryRepository(
            "permission_group"
        )

    # -- definition ---------------------------------------------------------

    def define_group(
        self, tenant_id: str, organization_id: str, name: str, permissions: list[str]
    ) -> PermissionGroup:
        """Define a reusable permission group."""
        now = self._clock.now()
        group = PermissionGroup(
            id=generate_id("pgrp"),
            tenant_id=tenant_id,
            organization_id=organization_id,
            name=name,
            permissions=permissions,
            created_at=now,
            updated_at=now,
        )
        return self.groups.add(group)

    def define_role(
        self,
        tenant_id: str,
        organization_id: str,
        role: str,
        *,
        inherits: list[str] | None = None,
        groups: list[str] | None = None,
        permissions: list[str] | None = None,
    ) -> RoleNode:
        """Define a role node with optional inheritance, groups and permissions."""
        now = self._clock.now()
        node = RoleNode(
            id=generate_id("role"),
            tenant_id=tenant_id,
            organization_id=organization_id,
            role=role,
            inherits=inherits or [],
            groups=groups or [],
            permissions=permissions or [],
            created_at=now,
            updated_at=now,
        )
        return self.roles.add(node)

    # -- resolution ---------------------------------------------------------

    def _role_node(self, tenant_id: str, role: str) -> RoleNode | None:
        matches_ = self.roles.list(tenant_id=tenant_id, where=lambda n: n.role == role)
        return matches_[0] if matches_ else None

    def _group_permissions(self, tenant_id: str, group_name: str) -> list[str]:
        found = self.groups.list(
            tenant_id=tenant_id, where=lambda g: g.name == group_name
        )
        return found[0].permissions if found else []

    def effective_permissions(self, tenant_id: str, role: str) -> set[str]:
        """Return the transitive set of permissions granted to ``role``."""
        resolved: set[str] = set()
        seen: set[str] = set()
        stack = [role]
        while stack:
            current = stack.pop()
            if current in seen:
                continue
            seen.add(current)
            node = self._role_node(tenant_id, current)
            if node is None:
                continue
            resolved.update(node.permissions)
            for group in node.groups:
                resolved.update(self._group_permissions(tenant_id, group))
            stack.extend(node.inherits)
        return resolved

    def grants(self, tenant_id: str, roles: list[str], required_permission: str) -> bool:
        """Return whether any of ``roles`` grants ``required_permission``."""
        for role in roles:
            for granted in self.effective_permissions(tenant_id, role):
                if matches(granted, required_permission):
                    return True
        return False
