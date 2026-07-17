"""Built-in demonstration agents + a ready-to-run orchestrator.

These are **generic infrastructure agents**, not business agents: each is a thin
capability worker (``collection`` / ``analysis`` / ``synthesis`` / ``general``)
that produces a deterministic, offline result. They exist so the platform is
demonstrably functional end-to-end — the visualization page and boot checks can
plan, schedule, delegate and merge a real run without any dataset, provider or
LLM, and without the *business* agents that future milestones will add.

A future milestone registers real agents (ResumeAnalystAgent, JDAnalystAgent, …)
for these same capability names; because routing prefers the more specialised /
healthier agent and registration is by name, the real agents simply supersede
these demos with zero orchestration changes.
"""

from __future__ import annotations

from src.ai.orchestration.adapters import FunctionAgent
from src.ai.orchestration.context.context import SharedContext
from src.ai.orchestration.models import AgentOutput, Task
from src.ai.orchestration.orchestrator import AgentOrchestrator
from src.ai.orchestration.planner.planner import (
    CapabilityTaskPlanner,
    default_plan_templates,
)
from src.ai.orchestration.registry.agent_registry import (
    AgentDescriptor,
    OrchestrationRegistry,
)


def _collection_agent() -> FunctionAgent:
    """Generic 'collection' worker — gathers the subject's declared payload."""

    def run(task: Task, context: SharedContext) -> AgentOutput:
        subject = task.payload.get("subject_id", context.get("subject_id", "unknown"))
        return AgentOutput(
            task_id=task.id,
            agent="demo:collector",
            data={"subject_id": subject, "signals": ["signal_a", "signal_b"]},
            summary=f"Collected 2 signal group(s) for subject {subject!r}.",
            evidence_sources=["collection"],
        )

    return FunctionAgent(
        AgentDescriptor(
            name="demo:collector",
            capabilities=["collection"],
            description="Generic signal-collection worker (demo).",
            tags=["demo"],
        ),
        run,
    )


def _analysis_agent() -> FunctionAgent:
    """Generic 'analysis' worker — reports on a facet of collected signals."""

    def run(task: Task, context: SharedContext) -> AgentOutput:
        deps = context.dependency_outputs(task)
        signals = next(
            (d.get("signals") for d in deps.values() if isinstance(d, dict) and d.get("signals")),
            [],
        )
        return AgentOutput(
            task_id=task.id,
            agent="demo:analyst",
            data={"facet": task.goal, "signals_seen": len(signals), "finding": "nominal"},
            summary=f"Analysed facet ({len(signals)} upstream signal group(s)): nominal.",
            evidence_sources=["analysis"],
        )

    return FunctionAgent(
        AgentDescriptor(
            name="demo:analyst",
            capabilities=["analysis"],
            description="Generic facet-analysis worker (demo).",
            tags=["demo"],
        ),
        run,
    )


def _synthesis_agent() -> FunctionAgent:
    """Generic 'synthesis' worker — merges upstream findings into a summary."""

    def run(task: Task, context: SharedContext) -> AgentOutput:
        deps = context.dependency_outputs(task)
        findings = [
            d.get("finding") for d in deps.values() if isinstance(d, dict) and d.get("finding")
        ]
        synthesis = (
            f"Synthesised {len(deps)} upstream result(s); "
            f"findings: {', '.join(findings) or 'none'}."
        )
        return AgentOutput(
            task_id=task.id,
            agent="demo:synthesizer",
            data={"synthesis": synthesis, "inputs": len(deps)},
            summary=synthesis,
            evidence_sources=["synthesis"],
        )

    return FunctionAgent(
        AgentDescriptor(
            name="demo:synthesizer",
            capabilities=["synthesis", "general"],
            description="Generic synthesis / general-answer worker (demo).",
            tags=["demo"],
        ),
        run,
    )


def register_demo_agents(registry: OrchestrationRegistry) -> OrchestrationRegistry:
    """Register the generic demo agents into ``registry`` and return it."""
    registry.register(_collection_agent())
    registry.register(_analysis_agent())
    registry.register(_synthesis_agent())
    return registry


def build_demo_orchestrator() -> AgentOrchestrator:
    """Return an :class:`AgentOrchestrator` wired with demo agents + templates.

    Self-contained (private registry, no global state, no dataset/provider) so it
    is safe for the UI and for AppTest — it renders and runs instantly offline.
    """
    registry = register_demo_agents(OrchestrationRegistry())
    planner = CapabilityTaskPlanner(default_plan_templates())
    return AgentOrchestrator(registry=registry, planner=planner)
