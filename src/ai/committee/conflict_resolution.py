"""Conflict detection + resolution (Module 5).

When two members reach materially different stances, the committee explains *why*
the disagreement exists — grounded in each side's evidence — and proposes a
concrete resolution strategy. Conflicts are never invented: a conflict only
exists when two real opinions diverge by a real stance gap.
"""

from __future__ import annotations

from itertools import combinations

from src.ai.committee.schemas import Conflict, MemberOpinion
from src.ai.committee.voting import stance_of

# Minimum stance gap (on the -2..3 scale) to count as a material conflict.
_CONFLICT_GAP = 2.0


def detect_conflicts(opinions: list[MemberOpinion]) -> list[Conflict]:
    """Return material, evidence-grounded conflicts between members."""
    active = [o for o in opinions if not o.abstained]
    conflicts: list[Conflict] = []

    for a, b in combinations(active, 2):
        gap = abs(stance_of(a.recommendation) - stance_of(b.recommendation))
        if gap < _CONFLICT_GAP:
            continue
        # Order so `a` is the more positive stance for readable narration.
        if stance_of(b.recommendation) > stance_of(a.recommendation):
            a, b = b, a
        conflicts.append(_resolve(a, b, gap))

    conflicts.sort(key=lambda c: c.stance_gap, reverse=True)
    return conflicts


def _resolve(a: MemberOpinion, b: MemberOpinion, gap: float) -> Conflict:
    """Build a :class:`Conflict` explaining an a-vs-b disagreement."""
    root_cause = (
        f"{a.role_title} weights {', '.join(a.evidence_sources) or 'its evidence'} "
        f"(→ {a.recommendation.value}), while {b.role_title} weights "
        f"{', '.join(b.evidence_sources) or 'its evidence'} (→ {b.recommendation.value})."
    )
    # Missing evidence = the concern the negative side raised that the positive
    # side did not address.
    missing = b.concerns[0] if b.concerns else "cross-validation between the two evidence sources"
    missing_evidence = f"Unaddressed by {a.role_title}: {missing}"
    assumption_difference = (
        f"{a.role_title} assumes the positive signals generalise; "
        f"{b.role_title} assumes the concerns are material until validated."
    )
    confidence_difference = (
        f"{a.role_title} confidence {a.confidence:.0f}% vs {b.role_title} {b.confidence:.0f}%"
    )
    # Resolution: validate the negative side's leading concern.
    resolution_strategy = (
        f"Resolve by validating '{missing}' directly (e.g. in interview or reference "
        f"check). Until then, weight the higher-confidence, better-evidenced side "
        f"({a.role_title if a.confidence >= b.confidence else b.role_title})."
    )
    return Conflict(
        member_a=a.role_title,
        member_b=b.role_title,
        stance_gap=gap,
        root_cause=root_cause,
        missing_evidence=missing_evidence,
        assumption_difference=assumption_difference,
        confidence_difference=confidence_difference,
        resolution_strategy=resolution_strategy,
    )
