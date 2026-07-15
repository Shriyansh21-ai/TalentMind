"""Committee moderator (Modules 2, 3) — genuine multi-agent orchestration.

The moderator runs the members' **independent** reviews in parallel through the
existing orchestration :class:`WorkflowEngine`: each member becomes an
orchestration agent, the reviews form one dependency-free task layer (so no
member sees another's opinion), and the shared :class:`SharedContext` carries the
evidence bundle. Events flow to telemetry and the message bus — reusing the
orchestration platform end-to-end, not re-implementing it.

After the reviews, the moderator facilitates the discussion round.
"""

from __future__ import annotations

from typing import List

from src.ai.orchestration.adapters import FunctionAgent
from src.ai.orchestration.context.context import SharedContext
from src.ai.orchestration.events.emitter import TelemetryEventBridge
from src.ai.orchestration.models import AgentOutput, Priority, Task, TaskGraph
from src.ai.orchestration.registry.agent_registry import (
    AgentDescriptor,
    OrchestrationRegistry,
)
from src.ai.orchestration.workflow.engine import WorkflowEngine

from src.ai.committee.discussion import run_discussion
from src.ai.committee.members import CommitteeMember
from src.ai.committee.schemas import CommitteeMode, DiscussionRound, MemberOpinion


class CommitteeModerator:
    """Facilitates the parallel independent reviews + the discussion round."""

    def __init__(self, *, telemetry: bool = True) -> None:
        """Create a moderator; ``telemetry`` bridges orchestration events to telemetry."""
        self._telemetry = telemetry

    def collect_independent_reviews(
        self,
        panel: List[CommitteeMember],
        bundle,
        mode: CommitteeMode,
    ) -> List[MemberOpinion]:
        """Run every member's review in parallel via the workflow engine (Module 2)."""
        registry = OrchestrationRegistry()
        for member in panel:
            registry.register(self._as_agent(member))

        engine = WorkflowEngine(registry=registry)
        if self._telemetry:
            TelemetryEventBridge().attach(engine.events)

        graph = TaskGraph()
        for member in panel:
            graph.add(
                Task(
                    id=member.role,
                    goal=f"Independent review by {member.role_title}",
                    capability=member.capability,
                    priority=Priority.NORMAL,
                    payload={"role": member.role},
                )
            )

        context = SharedContext(candidate=getattr(bundle, "candidate", None))
        context.set("bundle", bundle)
        context.set("mode", mode)

        result = engine.run(graph, context=context, name="committee_reviews")

        opinions: List[MemberOpinion] = []
        for member in panel:  # preserve panel order for stable, testable output
            output = result.outputs.get(member.role)
            if output is not None and output.ok and output.data:
                opinions.append(MemberOpinion.from_dict(output.data))
        return opinions

    def discuss(self, opinions: List[MemberOpinion]) -> DiscussionRound:
        """Facilitate the discussion round over the collected opinions (Module 3)."""
        return run_discussion(opinions)

    # -- internals ----------------------------------------------------------

    def _as_agent(self, member: CommitteeMember) -> FunctionAgent:
        """Wrap a committee member as an orchestration agent for the engine."""

        def _run(task: Task, context: SharedContext) -> AgentOutput:
            bundle = context.get("bundle")
            mode = context.get("mode", CommitteeMode.BALANCED)
            opinion = member.review(bundle, mode)
            return AgentOutput(
                task_id=task.id,
                agent=member.role,
                ok=True,
                data=opinion.to_dict(),
                summary=f"{member.role_title}: {opinion.recommendation.value}",
                confidence=opinion.confidence,
                evidence_sources=list(opinion.evidence_sources),
            )

        descriptor = AgentDescriptor(
            name=member.role,
            capabilities=[member.capability],
            description=f"{member.role_title} committee reviewer",
            tags=["committee-member"],
        )
        return FunctionAgent(descriptor, _run)
