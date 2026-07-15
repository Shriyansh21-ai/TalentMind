"""Multi-Agent Orchestration Framework (Phase 3 / Milestone 3).

This package turns TalentMind's AI Platform into an *agentic* platform: it can
coordinate many specialized agents to satisfy a single high-level recruiter goal.

Design contract — the whole reason this milestone exists:

    Future milestones should only need to *create new agents*. No orchestration
    code should need modification.

Every module here is independent and depends only on small, typed contracts
(``models``) plus dependency-injected collaborators. There is **no hiring
business logic** anywhere in this package — the orchestrator plans, schedules,
delegates, executes, monitors and merges; the *agents* (built in future
milestones) hold the domain knowledge.

Public surface (import from here, not from submodules, wherever possible)::

    from src.ai.orchestration import AgentOrchestrator, Goal

Layers (each in its own subpackage, matching the milestone brief):

    planner/        Goal -> TaskGraph
    orchestrator/   the top-level coordinator
    workflow/       reusable, config-driven execution engine
    delegation/     capability-based agent selection + routing
    communication/  message bus + typed messages (no agent-to-agent coupling)
    context/        the SharedContext every agent receives
    registry/       Agent Registry v2 (capabilities, health, discovery)
    scheduler/      execution order, priority, parallel groups
    memory/         workflow / shared / task / execution memory interfaces
    events/         typed lifecycle events that feed telemetry
    state/          execution state + snapshots for resume/recovery
    safety/         loop / cycle / duplicate / health guards
    simulation/     dry-run engine (no LLM, no providers) for tests
    monitoring/     latency / failure / success-rate tracking + visual logs
"""

from __future__ import annotations

from src.ai.orchestration.models import (
    AgentOutput,
    Goal,
    Priority,
    Task,
    TaskGraph,
    TaskStatus,
)
from src.ai.orchestration.context.context import SharedContext
from src.ai.orchestration.registry.agent_registry import (
    AgentDescriptor,
    HealthStatus,
    OrchestrationAgent,
    OrchestrationRegistry,
    orchestration_registry,
)
from src.ai.orchestration.orchestrator.orchestrator import (
    AgentOrchestrator,
    OrchestrationResult,
)
from src.ai.orchestration.workflow.engine import WorkflowEngine, WorkflowResult
from src.ai.orchestration.workflow.definition import ExecutionMode, WorkflowDefinition
from src.ai.orchestration.planner.planner import CapabilityTaskPlanner, TaskPlanner

__all__ = [
    "AgentOrchestrator",
    "OrchestrationResult",
    "Goal",
    "Task",
    "TaskGraph",
    "TaskStatus",
    "Priority",
    "AgentOutput",
    "SharedContext",
    "AgentDescriptor",
    "HealthStatus",
    "OrchestrationAgent",
    "OrchestrationRegistry",
    "orchestration_registry",
    "WorkflowEngine",
    "WorkflowResult",
    "WorkflowDefinition",
    "ExecutionMode",
    "TaskPlanner",
    "CapabilityTaskPlanner",
]
