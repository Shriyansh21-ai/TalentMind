"""Workspace application service (Module 5).

Creates and manages workspaces and the resources they own, enforcing tenant
isolation on every parent lookup so a resource can never be attached to another
tenant's workspace. Optional per-tenant workspace quotas are honoured when a
limit is supplied by the caller (the platform facade passes the org's limit).
"""

from __future__ import annotations

from src.platform.common.clock import Clock, SystemClock
from src.platform.common.errors import QuotaExceededError
from src.platform.common.ids import generate_id
from src.platform.common.models import TenantScopedEntity
from src.platform.common.ids import slugify
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


class WorkspaceService:
    """Manage workspaces and their owned resources within a tenant."""

    def __init__(
        self,
        repository: WorkspaceRepository | None = None,
        *,
        clock: Clock | None = None,
    ) -> None:
        self.repo = repository or WorkspaceRepository()
        self._clock = clock or SystemClock()

    # -- workspaces ---------------------------------------------------------

    def create_workspace(
        self,
        tenant_id: str,
        organization_id: str,
        name: str,
        *,
        kind: WorkspaceKind = WorkspaceKind.HIRING,
        description: str = "",
        max_workspaces: int | None = None,
    ) -> Workspace:
        """Create a workspace, optionally enforcing a per-tenant quota."""
        if max_workspaces is not None:
            current = self.repo.workspaces.count(tenant_id=tenant_id)
            if current >= max_workspaces:
                raise QuotaExceededError(
                    f"workspace limit ({max_workspaces}) reached for tenant"
                )
        now = self._clock.now()
        workspace = Workspace(
            id=generate_id("ws"),
            tenant_id=tenant_id,
            organization_id=organization_id,
            name=name,
            slug=slugify(name),
            kind=kind,
            description=description,
            created_at=now,
            updated_at=now,
        )
        return self.repo.workspaces.add(workspace)

    def get_workspace(self, tenant_id: str, workspace_id: str) -> Workspace | None:
        """Return a workspace within a tenant (or ``None``)."""
        return self.repo.workspaces.get(workspace_id, tenant_id=tenant_id)

    def list_workspaces(self, tenant_id: str) -> list[Workspace]:
        """Return all workspaces for a tenant."""
        return self.repo.workspaces.list(tenant_id=tenant_id)

    def archive_workspace(self, tenant_id: str, workspace_id: str) -> Workspace:
        """Archive a workspace (soft delete)."""
        ws = self.repo.workspaces.require(workspace_id, tenant_id=tenant_id)
        ws.archived = True
        ws.touch(self._clock.now())
        return self.repo.workspaces.update(ws)

    # -- generic child creation --------------------------------------------

    def _require_workspace(self, tenant_id: str, workspace_id: str) -> Workspace:
        """Return the parent workspace, tenant-isolation checked."""
        return self.repo.workspaces.require(workspace_id, tenant_id=tenant_id)

    def _new_child(self, cls, tenant_id: str, workspace_id: str, prefix: str, **fields):
        """Construct a tenant-scoped child of ``workspace_id``."""
        ws = self._require_workspace(tenant_id, workspace_id)
        now = self._clock.now()
        return cls(
            id=generate_id(prefix),
            tenant_id=tenant_id,
            organization_id=ws.organization_id,
            workspace_id=workspace_id,
            created_at=now,
            updated_at=now,
            **fields,
        )

    # -- owned resources ----------------------------------------------------

    def add_member(
        self, tenant_id: str, workspace_id: str, user_id: str, *, role: str = "recruiter"
    ) -> WorkspaceMember:
        """Add a member (e.g. a recruiter) to a workspace."""
        member = self._new_child(
            WorkspaceMember, tenant_id, workspace_id, "wsm",
            user_id=user_id, role=role,
        )
        return self.repo.members.add(member)

    def add_project(
        self,
        tenant_id: str,
        workspace_id: str,
        name: str,
        *,
        status: ProjectStatus = ProjectStatus.DRAFT,
        requisition_ref: str = "",
    ) -> Project:
        """Create a project inside a workspace."""
        project = self._new_child(
            Project, tenant_id, workspace_id, "proj",
            name=name, status=status, requisition_ref=requisition_ref,
        )
        return self.repo.projects.add(project)

    def add_team(self, tenant_id: str, workspace_id: str, name: str) -> Team:
        """Create a team inside a workspace."""
        team = self._new_child(Team, tenant_id, workspace_id, "team", name=name)
        return self.repo.teams.add(team)

    def add_pipeline(
        self,
        tenant_id: str,
        workspace_id: str,
        name: str,
        *,
        project_id: str | None = None,
        stages: list[str] | None = None,
    ) -> Pipeline:
        """Create a pipeline inside a workspace."""
        fields = {"name": name, "project_id": project_id}
        if stages is not None:
            fields["stages"] = stages
        pipeline = self._new_child(Pipeline, tenant_id, workspace_id, "pipe", **fields)
        return self.repo.pipelines.add(pipeline)

    def add_report(
        self, tenant_id: str, workspace_id: str, name: str, *, kind: str = "summary"
    ) -> Report:
        """Create a report inside a workspace."""
        report = self._new_child(
            Report, tenant_id, workspace_id, "rpt", name=name, kind=kind
        )
        return self.repo.reports.add(report)

    def add_dashboard(self, tenant_id: str, workspace_id: str, name: str) -> Dashboard:
        """Create a dashboard inside a workspace."""
        dashboard = self._new_child(
            Dashboard, tenant_id, workspace_id, "dash", name=name
        )
        return self.repo.dashboards.add(dashboard)

    def bind_agent(
        self, tenant_id: str, workspace_id: str, agent_key: str, *, enabled: bool = True
    ) -> AIAgentBinding:
        """Bind an existing platform AI agent (by key) to a workspace."""
        binding = self._new_child(
            AIAgentBinding, tenant_id, workspace_id, "bind",
            agent_key=agent_key, enabled=enabled,
        )
        return self.repo.agent_bindings.add(binding)

    def add_knowledge_base(
        self, tenant_id: str, workspace_id: str, name: str, *, source_kind: str = "documents"
    ) -> KnowledgeBase:
        """Create a knowledge base attached to a workspace."""
        kb = self._new_child(
            KnowledgeBase, tenant_id, workspace_id, "kb",
            name=name, source_kind=source_kind,
        )
        return self.repo.knowledge_bases.add(kb)

    # -- listings -----------------------------------------------------------

    def _by_workspace(
        self, repo, tenant_id: str, workspace_id: str
    ) -> list[TenantScopedEntity]:
        """Return a repo's children belonging to ``workspace_id`` within tenant."""
        return repo.list(
            tenant_id=tenant_id, where=lambda e: e.workspace_id == workspace_id
        )

    def projects(self, tenant_id: str, workspace_id: str) -> list[Project]:
        """Return the workspace's projects."""
        return self._by_workspace(self.repo.projects, tenant_id, workspace_id)

    def pipelines(self, tenant_id: str, workspace_id: str) -> list[Pipeline]:
        """Return the workspace's pipelines."""
        return self._by_workspace(self.repo.pipelines, tenant_id, workspace_id)

    def members(self, tenant_id: str, workspace_id: str) -> list[WorkspaceMember]:
        """Return the workspace's members."""
        return self._by_workspace(self.repo.members, tenant_id, workspace_id)

    def teams(self, tenant_id: str, workspace_id: str) -> list[Team]:
        """Return the workspace's teams."""
        return self._by_workspace(self.repo.teams, tenant_id, workspace_id)

    def reports(self, tenant_id: str, workspace_id: str) -> list[Report]:
        """Return the workspace's reports."""
        return self._by_workspace(self.repo.reports, tenant_id, workspace_id)

    def dashboards(self, tenant_id: str, workspace_id: str) -> list[Dashboard]:
        """Return the workspace's dashboards."""
        return self._by_workspace(self.repo.dashboards, tenant_id, workspace_id)

    def agent_bindings(self, tenant_id: str, workspace_id: str) -> list[AIAgentBinding]:
        """Return the workspace's AI-agent bindings."""
        return self._by_workspace(self.repo.agent_bindings, tenant_id, workspace_id)

    def knowledge_bases(self, tenant_id: str, workspace_id: str) -> list[KnowledgeBase]:
        """Return the workspace's knowledge bases."""
        return self._by_workspace(self.repo.knowledge_bases, tenant_id, workspace_id)
