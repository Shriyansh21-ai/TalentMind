"""Workspace domain models (Module 5).

An organization owns one or more :class:`Workspace` containers, and every hiring
resource (projects, teams, pipelines, reports, dashboards, AI-agent bindings and
knowledge bases) lives inside exactly one workspace. All are
:class:`TenantScopedEntity` subclasses, so isolation is enforced automatically
by the repository layer.

Note: :class:`AIAgentBinding` and :class:`KnowledgeBase` only *reference* the
existing Phase 1-5 AI agents by key — they never wrap or modify their logic.
"""

from __future__ import annotations

from enum import Enum

from pydantic import Field

from src.platform.common.models import TenantScopedEntity


class WorkspaceKind(str, Enum):
    """The purpose of a workspace."""

    HIRING = "hiring"
    ANALYTICS = "analytics"
    GENERAL = "general"


class ProjectStatus(str, Enum):
    """Lifecycle of a hiring project / requisition."""

    DRAFT = "draft"
    OPEN = "open"
    ON_HOLD = "on_hold"
    CLOSED = "closed"


class Workspace(TenantScopedEntity):
    """A logical container owned by an organization."""

    name: str
    slug: str = ""
    kind: WorkspaceKind = WorkspaceKind.HIRING
    description: str = ""
    archived: bool = False


class WorkspaceMember(TenantScopedEntity):
    """A user's membership of a workspace with a role (e.g. a recruiter)."""

    workspace_id: str
    user_id: str
    role: str = "recruiter"


class Project(TenantScopedEntity):
    """A hiring project / requisition inside a workspace."""

    workspace_id: str
    name: str
    status: ProjectStatus = ProjectStatus.DRAFT
    requisition_ref: str = ""


class Team(TenantScopedEntity):
    """A hiring team inside a workspace."""

    workspace_id: str
    name: str
    member_ids: list[str] = Field(default_factory=list)


class Pipeline(TenantScopedEntity):
    """A hiring pipeline with ordered stages, scoped to a project."""

    workspace_id: str
    project_id: str | None = None
    name: str
    stages: list[str] = Field(
        default_factory=lambda: ["Applied", "Screen", "Interview", "Offer", "Hired"]
    )


class Report(TenantScopedEntity):
    """A saved report inside a workspace."""

    workspace_id: str
    name: str
    kind: str = "summary"


class Dashboard(TenantScopedEntity):
    """A saved analytics dashboard inside a workspace."""

    workspace_id: str
    name: str
    layout: dict[str, object] = Field(default_factory=dict)


class AIAgentBinding(TenantScopedEntity):
    """A workspace's binding to an existing platform AI agent (by key)."""

    workspace_id: str
    agent_key: str
    enabled: bool = True


class KnowledgeBase(TenantScopedEntity):
    """A knowledge base attached to a workspace."""

    workspace_id: str
    name: str
    source_kind: str = "documents"
    document_count: int = 0
