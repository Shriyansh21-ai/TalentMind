"""Enterprise roles and the default RBAC matrix (Module 4).

Twelve built-in roles spanning the platform, organization, hiring and
governance domains. Each role maps to a concise set of (possibly wildcarded)
permissions following **least privilege**: a role receives only what its job
requires, and read-only/governance roles never receive mutating grants.

Roles are data, not code — :class:`~src.platform.rbac.models.RoleDefinition`
instances — so a future "custom role" feature can add entries without changing
the engine.
"""

from __future__ import annotations

from enum import Enum

from src.platform.rbac.permissions import Action, Resource
from src.platform.rbac.permissions import permission as p


class Role(str, Enum):
    """Built-in platform roles (ordered roughly by privilege)."""

    PLATFORM_ADMIN = "platform_admin"
    ORGANIZATION_ADMIN = "organization_admin"
    HR_DIRECTOR = "hr_director"
    RECRUITER = "recruiter"
    HIRING_MANAGER = "hiring_manager"
    INTERVIEWER = "interviewer"
    FINANCE = "finance"
    COMPLIANCE = "compliance"
    AUDITOR = "auditor"
    EXECUTIVE = "executive"
    VIEWER = "viewer"
    GUEST = "guest"


class ScopeType(str, Enum):
    """The level at which a role is granted."""

    PLATFORM = "platform"
    ORGANIZATION = "organization"
    WORKSPACE = "workspace"
    RESOURCE = "resource"


# Convenience grant helpers -------------------------------------------------

_CRUD = (Action.CREATE, Action.READ, Action.UPDATE, Action.DELETE)


def _manage(resource: Resource) -> list[str]:
    """Full management of a resource (all CRUD + manage)."""
    return [p(resource, a) for a in (*_CRUD, Action.MANAGE)]


def _readonly(*resources: Resource) -> list[str]:
    """Read-only grants for a set of resources."""
    return [p(r, Action.READ) for r in resources]


# The default role -> permission matrix. Values are permission strings that may
# contain wildcards; the policy engine expands/matches them at check time.
DEFAULT_ROLE_PERMISSIONS: dict[Role, list[str]] = {
    # Platform operator: everything, everywhere.
    Role.PLATFORM_ADMIN: [p("*", "*")],
    # Full control within their organization (but not the platform itself).
    Role.ORGANIZATION_ADMIN: [
        p(Resource.ORGANIZATION, Action.MANAGE),
        p(Resource.ORGANIZATION, Action.READ),
        p(Resource.ORGANIZATION, Action.UPDATE),
        *_manage(Resource.WORKSPACE),
        *_manage(Resource.USER),
        *_manage(Resource.ROLE),
        *_manage(Resource.CONFIG),
        *_manage(Resource.NOTIFICATION),
        p(Resource.SUBSCRIPTION, Action.READ),
        p(Resource.SUBSCRIPTION, Action.UPDATE),
        p(Resource.AUDIT, Action.READ),
        p(Resource.AUDIT, Action.EXPORT),
        p(Resource.PROJECT, "*"),
        p(Resource.PIPELINE, "*"),
        p(Resource.CANDIDATE, "*"),
        p(Resource.REPORT, "*"),
        p(Resource.DASHBOARD, "*"),
        p(Resource.AI_AGENT, "*"),
        p(Resource.KNOWLEDGE_BASE, "*"),
    ],
    # Runs hiring across workspaces.
    Role.HR_DIRECTOR: [
        *_manage(Resource.WORKSPACE),
        *_manage(Resource.PROJECT),
        *_manage(Resource.PIPELINE),
        *_manage(Resource.TEAM),
        p(Resource.CANDIDATE, "*"),
        p(Resource.REPORT, "*"),
        p(Resource.DASHBOARD, "*"),
        p(Resource.COMPENSATION, Action.READ),
        p(Resource.COMPENSATION, Action.APPROVE),
        p(Resource.AI_AGENT, Action.EXECUTE),
        p(Resource.AI_AGENT, Action.READ),
        p(Resource.USER, Action.READ),
        p(Resource.AUDIT, Action.READ),
    ],
    # Day-to-day sourcing and pipeline work.
    Role.RECRUITER: [
        p(Resource.CANDIDATE, Action.CREATE),
        p(Resource.CANDIDATE, Action.READ),
        p(Resource.CANDIDATE, Action.UPDATE),
        p(Resource.CANDIDATE, Action.EXPORT),
        p(Resource.PIPELINE, Action.READ),
        p(Resource.PIPELINE, Action.UPDATE),
        p(Resource.PROJECT, Action.READ),
        p(Resource.REPORT, Action.READ),
        p(Resource.DASHBOARD, Action.READ),
        p(Resource.AI_AGENT, Action.EXECUTE),
        p(Resource.AI_AGENT, Action.READ),
        p(Resource.KNOWLEDGE_BASE, Action.READ),
    ],
    # Owns a requisition; reviews and advances candidates.
    Role.HIRING_MANAGER: [
        p(Resource.CANDIDATE, Action.READ),
        p(Resource.CANDIDATE, Action.UPDATE),
        p(Resource.PIPELINE, Action.READ),
        p(Resource.PIPELINE, Action.UPDATE),
        p(Resource.PIPELINE, Action.APPROVE),
        p(Resource.PROJECT, Action.READ),
        p(Resource.REPORT, Action.READ),
        p(Resource.DASHBOARD, Action.READ),
        p(Resource.AI_AGENT, Action.READ),
    ],
    # Conducts interviews; scoped access to assigned candidates.
    Role.INTERVIEWER: [
        p(Resource.CANDIDATE, Action.READ),
        p(Resource.PIPELINE, Action.READ),
        p(Resource.REPORT, Action.CREATE),
        p(Resource.REPORT, Action.READ),
    ],
    # Compensation and budget governance.
    Role.FINANCE: [
        p(Resource.COMPENSATION, "*"),
        p(Resource.SUBSCRIPTION, Action.READ),
        p(Resource.BILLING, "*"),
        p(Resource.REPORT, Action.READ),
        p(Resource.DASHBOARD, Action.READ),
    ],
    # Ensures policy adherence; read + approve, never mutate hiring data.
    Role.COMPLIANCE: [
        *_readonly(
            Resource.CANDIDATE,
            Resource.PIPELINE,
            Resource.PROJECT,
            Resource.REPORT,
            Resource.COMPENSATION,
            Resource.CONFIG,
        ),
        p(Resource.AUDIT, Action.READ),
        p(Resource.AUDIT, Action.EXPORT),
        p(Resource.COMPENSATION, Action.APPROVE),
    ],
    # Read-only access to the audit trail and evidence.
    Role.AUDITOR: [
        p(Resource.AUDIT, Action.READ),
        p(Resource.AUDIT, Action.EXPORT),
        *_readonly(
            Resource.REPORT,
            Resource.PIPELINE,
            Resource.CANDIDATE,
            Resource.CONFIG,
        ),
    ],
    # Leadership dashboards and reports.
    Role.EXECUTIVE: [
        *_readonly(
            Resource.DASHBOARD,
            Resource.REPORT,
            Resource.PIPELINE,
            Resource.COMPENSATION,
        ),
        p(Resource.REPORT, Action.EXPORT),
    ],
    # Generic read-only member.
    Role.VIEWER: [
        *_readonly(
            Resource.DASHBOARD,
            Resource.REPORT,
            Resource.PROJECT,
            Resource.CANDIDATE,
            Resource.PIPELINE,
        ),
    ],
    # External/limited: dashboards only.
    Role.GUEST: [
        p(Resource.DASHBOARD, Action.READ),
    ],
}


# Roles that may only ever be granted at platform scope.
PLATFORM_ONLY_ROLES = frozenset({Role.PLATFORM_ADMIN})
