"""Simulation runner (Module 14).

Lets you exercise the *entire* orchestration pipeline — planner, scheduler,
delegation, engine, events, monitoring — with **no LLM calls and no providers**.
It works by registering :class:`SimulatedAgent` stand-ins for whatever
capabilities a plan needs, each returning a canned, deterministic output.

Uses:
* **Dry-run workflows** — see the plan + execution order a goal would produce.
* **Planner validation** — assert a goal decomposes into the expected graph.
* **Testing without LLM calls / providers** — the whole unit-test story.

The runner never touches the process-wide registry; it builds its own isolated
:class:`OrchestrationRegistry` so simulations can't leak into real runs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from src.ai.orchestration.adapters import FunctionAgent
from src.ai.orchestration.context.context import SharedContext
from src.ai.orchestration.models import AgentOutput, Goal, Task, TaskGraph
from src.ai.orchestration.orchestrator import AgentOrchestrator, OrchestrationResult
from src.ai.orchestration.planner.planner import (
    CapabilityTaskPlanner,
    TaskPlanner,
    default_plan_templates,
)
from src.ai.orchestration.registry.agent_registry import (
    AgentDescriptor,
    OrchestrationRegistry,
)
from src.ai.orchestration.workflow.engine import WorkflowEngine

CannedFn = Callable[[Task, SharedContext], Dict]


class SimulatedAgent(FunctionAgent):
    """A deterministic stand-in agent for one capability (no side effects)."""

    def __init__(
        self,
        capability: str,
        *,
        name: Optional[str] = None,
        responder: Optional[CannedFn] = None,
        fail: bool = False,
    ) -> None:
        """Create a simulated agent for ``capability``.

        Args:
            capability: The capability this agent advertises.
            name: Agent name (defaults to ``sim:{capability}``).
            responder: Optional ``(task, context) -> data`` producing canned data.
            fail: If ``True``, the agent always returns a failed output (for
                testing retry / fallback / degradation paths).
        """
        descriptor = AgentDescriptor(
            name=name or f"sim:{capability}",
            capabilities=[capability],
            description=f"Simulated agent for {capability!r}.",
            tags=["simulated"],
        )
        self._responder = responder
        self._fail = fail
        super().__init__(descriptor, self._respond)

    def _respond(self, task: Task, context: SharedContext) -> AgentOutput:
        """Return the canned output for ``task`` (deterministic)."""
        if self._fail:
            return AgentOutput(
                task_id=task.id,
                agent=self.descriptor.name,
                ok=False,
                error=f"Simulated failure for capability {task.capability!r}.",
            )
        data = self._responder(task, context) if self._responder else {
            "simulated": True,
            "capability": task.capability,
            "goal": task.goal,
        }
        return AgentOutput(
            task_id=task.id,
            agent=self.descriptor.name,
            ok=True,
            data=data,
            summary=f"[dry-run] {task.capability}: {task.goal}",
            evidence_sources=[f"simulation:{task.capability}"],
        )


@dataclass
class SimulationReport:
    """The result of a dry-run simulation.

    Attributes:
        goal: The simulated goal.
        graph: The planned :class:`TaskGraph`.
        execution_order: Task ids in the order they would run (by layer).
        layers: The parallel groups (list of task-id lists).
        result: The :class:`OrchestrationResult` from the dry execution.
        missing_capabilities: Capabilities in the plan with no simulated agent.
    """

    goal: Goal
    graph: TaskGraph
    execution_order: List[str]
    layers: List[List[str]]
    result: Optional[OrchestrationResult] = None
    missing_capabilities: List[str] = field(default_factory=list)


class SimulationRunner:
    """Runs goals/workflows against simulated agents (offline, deterministic)."""

    def __init__(self, planner: Optional[TaskPlanner] = None) -> None:
        """Bind the runner to a planner (defaults to the example templates)."""
        self.planner = planner or CapabilityTaskPlanner(default_plan_templates())
        self.registry = OrchestrationRegistry()

    def register(self, agent: SimulatedAgent) -> SimulatedAgent:
        """Register a simulated agent into the isolated simulation registry."""
        self.registry.register(agent)
        return agent

    def autoprovision(self, graph: TaskGraph) -> List[str]:
        """Ensure every capability in ``graph`` has a simulated agent.

        Returns the list of capabilities it had to create a stand-in for (useful
        to assert a plan only needs capabilities you expected).
        """
        provisioned: List[str] = []
        for task in graph:
            if not self.registry.discover(task.capability, healthy_only=False):
                self.register(SimulatedAgent(task.capability))
                provisioned.append(task.capability)
        return provisioned

    def dry_run(
        self, goal: Goal, *, autoprovision: bool = True
    ) -> SimulationReport:
        """Plan ``goal`` and execute it against simulated agents.

        Args:
            goal: The goal to simulate.
            autoprovision: If ``True``, create stand-ins for any capability the
                plan needs but that has no registered simulated agent.
        """
        graph = self.planner.plan(goal)
        layers = [[t.id for t in layer] for layer in graph.execution_layers()]
        order = [t.id for layer in graph.execution_layers() for t in layer]

        missing = self.autoprovision(graph) if autoprovision else [
            t.capability
            for t in graph
            if not self.registry.discover(t.capability, healthy_only=False)
        ]

        result: Optional[OrchestrationResult] = None
        if not missing or autoprovision:
            engine = WorkflowEngine(registry=self.registry)
            orchestrator = AgentOrchestrator(
                registry=self.registry,
                planner=self.planner,
                engine=engine,
                telemetry_bridge=False,
            )
            result = orchestrator.run(goal)

        return SimulationReport(
            goal=goal,
            graph=graph,
            execution_order=order,
            layers=layers,
            result=result,
            missing_capabilities=missing,
        )
