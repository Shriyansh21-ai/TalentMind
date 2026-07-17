"""Evaluation rubrics (Module 7).

Generates the scoring dimensions the panel evaluates against — technical,
communication, leadership, problem solving, architecture, learning, culture,
ownership, collaboration and decision making. Each dimension carries a
qualitative bar for Strong / Solid / Mixed / Weak plus the concrete evidence
interviewers should look for, drawn from the candidate's own intelligence
(Modules 7 / 16). Deterministic, offline, nothing invented.
"""

from __future__ import annotations

from typing import Any

from src.ai.agents.interview_studio.schemas import RubricDimension
from src.ai.agents.interview_studio.templates import RoleProfile


def _levels(strong: str, solid: str, mixed: str, weak: str) -> dict[str, str]:
    """Build the qualitative level ladder for a rubric dimension."""
    return {"Strong": strong, "Solid": solid, "Mixed": mixed, "Weak": weak}


# The ten core scoring dimensions (Module 7). Each is a (name, description,
# levels, base signals) tuple; role/evidence enrichment happens in build_rubrics.
_CORE_DIMENSIONS = [
    (
        "Technical Depth",
        "Command of the role's core technologies and fundamentals.",
        _levels(
            "Deep, first-principles command; teaches the interviewer something.",
            "Solid working depth appropriate to the seniority.",
            "Some depth but gaps in fundamentals.",
            "Surface-level; cannot go beyond buzzwords.",
        ),
    ),
    (
        "Problem Solving",
        "Structured reasoning through ambiguous or novel problems.",
        _levels(
            "Decomposes cleanly, explores trade-offs, converges fast.",
            "Reaches a correct solution with light guidance.",
            "Needs significant hints; reasoning is uneven.",
            "Struggles to structure the problem.",
        ),
    ),
    (
        "Architecture",
        "System-design maturity and trade-off reasoning at the right scope.",
        _levels(
            "Designs for scale and failure; justifies every trade-off.",
            "Sound design with reasonable trade-offs.",
            "Design works but misses scale or failure modes.",
            "Cannot structure a design at this level.",
        ),
    ),
    (
        "Communication",
        "Clarity, structure and audience awareness when explaining.",
        _levels(
            "Crisp, structured, adapts to the audience.",
            "Clear and easy to follow.",
            "Understandable but rambling or unstructured.",
            "Hard to follow; loses the thread.",
        ),
    ),
    (
        "Ownership",
        "Accountability and proactivity beyond the assigned scope.",
        _levels(
            "Drives outcomes end-to-end; owns failures.",
            "Reliably owns their scope.",
            "Owns tasks but not outcomes.",
            "Deflects responsibility.",
        ),
    ),
    (
        "Collaboration",
        "Working effectively with peers and across functions.",
        _levels(
            "Multiplies the team; handles conflict constructively.",
            "Works well with others.",
            "Collaborates but with friction.",
            "Works in isolation or creates friction.",
        ),
    ),
    (
        "Decision Making",
        "Judgment and reasoning under incomplete information.",
        _levels(
            "Makes sound calls fast; reasons about reversibility.",
            "Makes reasonable decisions with light support.",
            "Hesitant or inconsistent judgment.",
            "Avoids decisions or reasons poorly.",
        ),
    ),
    (
        "Leadership",
        "Influence, direction-setting and developing others.",
        _levels(
            "Sets direction and grows people at scale.",
            "Leads projects and mentors peers.",
            "Emerging leadership signals.",
            "No leadership evidence where the role needs it.",
        ),
    ),
    (
        "Learning",
        "Learning velocity and growth mindset.",
        _levels(
            "Learns fast; actively seeks and applies feedback.",
            "Grows steadily; open to feedback.",
            "Learns slowly or defensively.",
            "Fixed mindset; resists feedback.",
        ),
    ),
    (
        "Culture & Values",
        "Alignment with the team's working norms and integrity.",
        _levels(
            "Strong add; models the values.",
            "Good fit with the team's norms.",
            "Some misalignment to explore.",
            "Clear values or integrity concerns.",
        ),
    ),
]


def build_rubrics(evidence: dict[str, Any], role: RoleProfile) -> list[RubricDimension]:
    """Assemble the evaluation rubric, weighting + enriching by role/evidence.

    Args:
        evidence: The aggregated interview evidence dict.
        role: The resolved role profile.

    Returns:
        The list of :class:`RubricDimension` the panel scores against.
    """
    intelligence = evidence.get("intelligence") or {}
    strengths = list(intelligence.get("strengths") or [])
    weaknesses = list(intelligence.get("weaknesses") or [])

    # Role emphasis raises the weight label on the dimensions that matter most.
    heavy: set = set()
    if role.emphasize_system_design:
        heavy.add("Architecture")
    if role.emphasize_leadership:
        heavy.update({"Leadership", "Decision Making"})
    heavy.add("Technical Depth")

    dimensions: list[RubricDimension] = []
    for name, description, levels in _CORE_DIMENSIONS:
        evidence_to_look_for: list[str] = []
        # Point interviewers at the candidate's own signals for this dimension.
        for s in strengths:
            if _related(name, s):
                evidence_to_look_for.append(f"Confirm claimed strength: {s}")
        for w in weaknesses:
            if _related(name, w):
                evidence_to_look_for.append(f"Probe development area: {w}")
        if not evidence_to_look_for:
            evidence_to_look_for.append(
                f"Look for concrete, first-person evidence of {name.lower()}."
            )

        dimensions.append(
            RubricDimension(
                name=name,
                description=description,
                weight="Critical" if name in heavy else "Standard",
                levels=levels,
                evidence_to_look_for=evidence_to_look_for[:3],
                source="Candidate Intelligence + Interview Intelligence",
            )
        )
    return dimensions


# Keyword hints linking a candidate strength/weakness phrase to a rubric dimension.
_DIMENSION_HINTS = {
    "Technical Depth": ("technical", "engineering", "coding", "depth", "stack", "expertise"),
    "Architecture": ("architecture", "system design", "scalab", "design", "distributed"),
    "Communication": ("communication", "clarity", "explain", "writing"),
    "Leadership": ("leadership", "lead", "mentor", "manage", "influence"),
    "Ownership": ("ownership", "accountab", "initiative", "proactiv"),
    "Collaboration": ("collaborat", "team", "cross-functional", "stakeholder"),
    "Learning": ("learn", "growth", "adapt", "curious"),
    "Problem Solving": ("problem", "analytic", "reasoning"),
    "Decision Making": ("decision", "judgment", "prioritiz"),
    "Culture & Values": ("culture", "values", "integrity"),
}


def _related(dimension: str, phrase: str) -> bool:
    """Return True if ``phrase`` plausibly relates to ``dimension``."""
    hints = _DIMENSION_HINTS.get(dimension, ())
    lowered = (phrase or "").lower()
    return any(h in lowered for h in hints)
