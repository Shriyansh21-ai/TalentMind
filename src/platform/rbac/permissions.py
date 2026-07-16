"""Permission vocabulary (Module 4).

Permissions are expressed as ``"<resource>:<action>"`` strings so they are
compact, greppable and easy to serialise over the API. Wildcards are supported
at both positions (``"workspace:*"``, ``"*:read"``, ``"*:*"``) to keep role
definitions concise while still resolving to concrete grants.
"""

from __future__ import annotations

from enum import Enum


class Resource(str, Enum):
    """A protected resource type."""

    PLATFORM = "platform"
    ORGANIZATION = "organization"
    WORKSPACE = "workspace"
    PROJECT = "project"
    TEAM = "team"
    CANDIDATE = "candidate"
    PIPELINE = "pipeline"
    REPORT = "report"
    DASHBOARD = "dashboard"
    USER = "user"
    ROLE = "role"
    SUBSCRIPTION = "subscription"
    BILLING = "billing"
    AUDIT = "audit"
    CONFIG = "config"
    NOTIFICATION = "notification"
    AI_AGENT = "ai_agent"
    KNOWLEDGE_BASE = "knowledge_base"
    COMPENSATION = "compensation"


class Action(str, Enum):
    """An operation performed on a resource."""

    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    MANAGE = "manage"
    EXPORT = "export"
    APPROVE = "approve"
    EXECUTE = "execute"


WILDCARD = "*"


def permission(resource: Resource | str, action: Action | str) -> str:
    """Build a canonical ``"resource:action"`` permission string."""
    r = resource.value if isinstance(resource, Resource) else resource
    a = action.value if isinstance(action, Action) else action
    return f"{r}:{a}"


def matches(granted: str, required: str) -> bool:
    """Return whether a ``granted`` permission satisfies a ``required`` one.

    ``granted`` may use wildcards (``*``) in either position; ``required`` must
    be concrete. ``"workspace:*"`` grants ``"workspace:read"``; ``"*:*"`` grants
    everything.
    """
    g_res, _, g_act = granted.partition(":")
    r_res, _, r_act = required.partition(":")
    res_ok = g_res == WILDCARD or g_res == r_res
    act_ok = g_act == WILDCARD or g_act == r_act
    return res_ok and act_ok


def all_permissions() -> list[str]:
    """Return every concrete resource:action permission (for docs/catalogues)."""
    return [permission(r, a) for r in Resource for a in Action]
