"""Task planner (Module 2).

Turns a high-level :class:`Goal` into a composable :class:`TaskGraph`. The
default planner is **deterministic and data-driven**: it matches the goal text
against a registry of :class:`PlanTemplate` records (keyword-weighted, exactly
like the copilot's intent classifier) and compiles the winning template's
declarative :class:`WorkflowDefinition` into a task graph.

Why templates and not code: adding a new plan is *data* — register a template
(or let a future agent contribute one). The planner itself never changes, and it
holds no hiring logic; a template just names capabilities + dependencies.

:class:`TaskPlanner` is the injectable seam, so a future milestone can drop in an
LLM-backed planner (build a graph via a :class:`~src.ai.core.base_agent.BaseAgent`)
behind the same interface with no orchestrator change.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from src.ai.orchestration.models import Goal, Priority, Task, TaskGraph
from src.ai.orchestration.workflow.definition import (
    ExecutionMode,
    WorkflowDefinition,
    WorkflowStep,
)


@dataclass
class PlanTemplate:
    """A reusable, keyword-matched plan the planner can select.

    Attributes:
        name: Template name (also the workflow name it produces).
        keywords: ``(phrase, weight)`` pairs scored against the goal text.
        definition: The declarative workflow this template expands to.
    """

    name: str
    keywords: list[tuple[str, int]] = field(default_factory=list)
    definition: WorkflowDefinition = field(default_factory=lambda: WorkflowDefinition(name="empty"))

    def score(self, text: str) -> int:
        """Return the summed weight of keyword phrases present in ``text``."""
        return sum(weight for phrase, weight in self.keywords if phrase in text)


class TaskPlanner(ABC):
    """Contract for planners: :class:`Goal` in, :class:`TaskGraph` out."""

    @abstractmethod
    def plan(self, goal: Goal) -> TaskGraph:
        """Return a validated, composable task graph for ``goal``."""


class CapabilityTaskPlanner(TaskPlanner):
    """Deterministic, template-driven planner (offline, no LLM)."""

    def __init__(
        self,
        templates: list[PlanTemplate] | None = None,
        *,
        default_capability: str = "general",
    ) -> None:
        """Bind the planner to a template list + a default single-task capability."""
        self.templates: list[PlanTemplate] = list(templates or [])
        self.default_capability = default_capability

    def register_template(self, template: PlanTemplate) -> PlanTemplate:
        """Add a template (future agents contribute plans without code changes)."""
        self.templates.append(template)
        return template

    def match(self, goal: Goal) -> tuple[PlanTemplate | None, float]:
        """Return the best-matching template + a 0-100 confidence."""
        text = f" {goal.description.lower().strip()} "
        best: PlanTemplate | None = None
        best_score = 0
        for template in self.templates:
            score = template.score(text)
            if score > best_score:
                best, best_score = template, score
        if best is None:
            return None, 40.0
        confidence = min(100.0, 50.0 + best_score * 10.0)
        return best, confidence

    def plan(self, goal: Goal) -> TaskGraph:
        """Build a task graph from the best template, or a single default task."""
        template, confidence = self.match(goal)
        base_payload = {
            "subject_id": goal.subject_id,
            "goal": goal.description,
            **goal.constraints,
        }

        if template is None:
            graph = self._single_task_graph(goal, base_payload, confidence)
        else:
            graph = template.definition.build_graph(base_payload)
            for task in graph:
                task.confidence = confidence
                task.metadata.setdefault("plan_template", template.name)
        graph.goal = goal
        graph.validate()
        return graph

    def _single_task_graph(self, goal: Goal, base_payload: dict, confidence: float) -> TaskGraph:
        """Fall back to a one-task graph using the default capability."""
        graph = TaskGraph()
        graph.add(
            Task(
                id="task_1",
                goal=goal.description,
                capability=self.default_capability,
                priority=Priority.NORMAL,
                expected_output="A single-agent response to the goal.",
                confidence=confidence,
                payload=base_payload,
                metadata={"plan_template": "(default)"},
            )
        )
        return graph


def default_plan_templates() -> list[PlanTemplate]:
    """Return a small, generic set of example templates.

    These are **infrastructure examples**, not business agents: they wire
    together *capabilities* (opaque strings) so the platform is demonstrably
    functional end-to-end. Future milestones add real templates whose
    capabilities are served by real agents; nothing here needs to change.
    """
    analysis = WorkflowDefinition(
        name="entity_analysis",
        description="Analyse a subject across independent facets, then summarise.",
        mode=ExecutionMode.AUTO,
        steps=[
            WorkflowStep(
                id="collect",
                capability="collection",
                goal="Collect the raw signals for the subject.",
                priority=Priority.HIGH,
                expected_output="Structured signal bundle.",
                output_slot="signals",
            ),
            WorkflowStep(
                id="facet_a",
                capability="analysis",
                goal="Analyse facet A of the subject.",
                depends_on=["collect"],
                expected_output="Facet A findings.",
            ),
            WorkflowStep(
                id="facet_b",
                capability="analysis",
                goal="Analyse facet B of the subject.",
                depends_on=["collect"],
                expected_output="Facet B findings.",
            ),
            WorkflowStep(
                id="summary",
                capability="synthesis",
                goal="Merge the facet findings into one summary.",
                depends_on=["facet_a", "facet_b"],
                expected_output="Unified summary.",
                output_slot="summary",
            ),
        ],
    )

    quick = WorkflowDefinition(
        name="quick_answer",
        description="Answer a simple goal with a single synthesis step.",
        steps=[
            WorkflowStep(
                id="answer",
                capability="synthesis",
                goal="Produce a direct answer to the goal.",
                expected_output="A direct answer.",
            )
        ],
    )

    return [
        PlanTemplate(
            name="entity_analysis",
            keywords=[
                ("analyze", 3),
                ("analyse", 3),
                ("assess", 3),
                ("evaluate", 2),
                ("deep dive", 2),
                ("full", 1),
            ],
            definition=analysis,
        ),
        PlanTemplate(
            name="quick_answer",
            keywords=[("summary", 2), ("quick", 3), ("answer", 2), ("what", 1)],
            definition=quick,
        ),
    ]
