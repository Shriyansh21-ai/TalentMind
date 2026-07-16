"""Persistence for the workspace aggregate (Module 5)."""

from __future__ import annotations

from src.platform.common.repository import InMemoryRepository
from src.platform.workspaces.models import (
    AIAgentBinding,
    Dashboard,
    KnowledgeBase,
    Pipeline,
    Project,
    Report,
    Team,
    Workspace,
    WorkspaceMember,
)


class WorkspaceRepository:
    """Aggregate repository for workspaces and everything they own."""

    def __init__(self) -> None:
        self.workspaces: InMemoryRepository[Workspace] = InMemoryRepository("workspace")
        self.members: InMemoryRepository[WorkspaceMember] = InMemoryRepository(
            "workspace_member"
        )
        self.projects: InMemoryRepository[Project] = InMemoryRepository("project")
        self.teams: InMemoryRepository[Team] = InMemoryRepository("team")
        self.pipelines: InMemoryRepository[Pipeline] = InMemoryRepository("pipeline")
        self.reports: InMemoryRepository[Report] = InMemoryRepository("report")
        self.dashboards: InMemoryRepository[Dashboard] = InMemoryRepository("dashboard")
        self.agent_bindings: InMemoryRepository[AIAgentBinding] = InMemoryRepository(
            "ai_agent_binding"
        )
        self.knowledge_bases: InMemoryRepository[KnowledgeBase] = InMemoryRepository(
            "knowledge_base"
        )
