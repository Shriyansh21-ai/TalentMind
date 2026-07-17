"""Decision trace engine (Module 1).

Reconstructs the chronological decision trace from the agents that actually
participated — derived from the observed evidence sources, never fabricated. An
agent whose evidence source is absent is recorded as Unavailable (not invented).
"""

from __future__ import annotations

from typing import Any

from src.ai.agents.audit.schemas import DecisionTraceStep
from src.ai.agents.audit.templates import AGENT_CATALOG, FINAL_DECISION_NODE


def build_decision_trace(context: dict[str, Any]) -> list[DecisionTraceStep]:
    """Reconstruct the chronological decision trace (Module 1)."""
    sources = set(context.get("evidence_sources", []))
    steps: list[DecisionTraceStep] = []

    for entry in AGENT_CATALOG:
        observed = entry.source in sources
        steps.append(
            DecisionTraceStep(
                order=entry.order,
                stage=entry.stage,
                origin_agent=entry.origin_agent,
                status="Observed" if observed else "Unavailable",
                summary=(
                    f"{entry.origin_agent} produced {entry.evidence_type.lower()}."
                    if observed
                    else f"{entry.stage} was not evidenced in this decision journey."
                ),
                evidence_source=entry.source,
                register="Observed" if observed else "Unavailable",
            )
        )

    # Terminal node: the final decision, anchored on the committee/compliance chain.
    committee_present = "AI Hiring Committee" in sources
    steps.append(
        DecisionTraceStep(
            order=len(AGENT_CATALOG) + 1,
            stage=FINAL_DECISION_NODE,
            origin_agent="Hiring workflow",
            status="Observed" if committee_present else "Unavailable",
            summary=(
                "Final decision synthesized from the committee and downstream governance."
                if committee_present
                else "No committee decision on record; final decision cannot be reconstructed."
            ),
            evidence_source=FINAL_DECISION_NODE,
            register="Observed" if committee_present else "Unavailable",
        )
    )
    return steps
