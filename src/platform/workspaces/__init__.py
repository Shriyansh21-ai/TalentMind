"""Module 5 — Workspace Management.

Organizations own workspaces; workspaces own projects, teams, recruiters
(members), pipelines, reports, dashboards, AI-agent bindings and knowledge
bases. Every resource is tenant-scoped and isolated. The service references
existing AI agents by key only — it never modifies their logic.
"""

from __future__ import annotations

from src.platform.workspaces.models import (
    AIAgentBinding,
    Dashboard,
    KnowledgeBase,
    Pipeline,
    Project,
    ProjectStatus,
    Report,
    Team,
    Workspace,
    WorkspaceKind,
    WorkspaceMember,
)
from src.platform.workspaces.repository import WorkspaceRepository
from src.platform.workspaces.service import WorkspaceService

__all__ = [
    "Workspace",
    "WorkspaceKind",
    "WorkspaceMember",
    "Project",
    "ProjectStatus",
    "Team",
    "Pipeline",
    "Report",
    "Dashboard",
    "AIAgentBinding",
    "KnowledgeBase",
    "WorkspaceRepository",
    "WorkspaceService",
]
