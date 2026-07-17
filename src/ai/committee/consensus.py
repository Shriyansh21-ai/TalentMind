"""Consensus engine (Module 4) — evidence-weighted, never majority vote.

Aggregates the members' independent opinions into a single committee stance by
weighting each opinion by its evidence (confidence × coverage, mode-adjusted).
Consensus *level* reflects both how aligned the members are (agreement ratio) and
how tightly their stances cluster (dispersion) — so three thinly-supported
agreements do not manufacture a "strong consensus".
"""

from __future__ import annotations

import math

from src.ai.committee.schemas import (
    CommitteeMode,
    Consensus,
    ConsensusLevel,
    MemberOpinion,
    Recommendation,
)
from src.ai.committee.voting import (
    mode_stance_bias,
    recommendation_from_stance,
    stance_distribution,
    stance_of,
    weight_of,
)


def _direction(stance: float) -> int:
    """Return +1 (positive), -1 (negative) or 0 (hold) for a stance value."""
    if stance > 0.4:
        return 1
    if stance < -0.4:
        return -1
    return 0


def build_consensus(opinions: list[MemberOpinion], mode: CommitteeMode) -> Consensus:
    """Return the evidence-weighted :class:`Consensus` for the opinions."""
    weights = {o.role: weight_of(o, mode) for o in opinions}
    total_w = sum(weights.values())

    if total_w <= 0:
        return Consensus(
            level=ConsensusLevel.NONE,
            recommendation=Recommendation.HOLD,
            weighted_stance=0.0,
            agreement_ratio=0.0,
            reasoning="No member produced weighted evidence; unable to form a view.",
            stance_distribution=stance_distribution(opinions),
            member_weights=weights,
        )

    raw_stance = sum(stance_of(o.recommendation) * weights[o.role] for o in opinions) / total_w
    weighted_stance = max(-2.0, min(3.0, raw_stance + mode_stance_bias(mode)))
    recommendation = recommendation_from_stance(weighted_stance)

    # Dispersion (weighted std of member stances around the raw mean).
    variance = (
        sum(weights[o.role] * (stance_of(o.recommendation) - raw_stance) ** 2 for o in opinions)
        / total_w
    )
    dispersion = math.sqrt(variance)

    # Agreement: share of weight aligned with the committee direction.
    target = _direction(weighted_stance)
    agree_w = sum(
        weights[o.role] for o in opinions if _direction(stance_of(o.recommendation)) == target
    )
    agreement_ratio = agree_w / total_w

    level = _classify(agreement_ratio, dispersion)
    reasoning = _reasoning(
        recommendation, level, agreement_ratio, dispersion, mode, opinions, weights
    )

    return Consensus(
        level=level,
        recommendation=recommendation,
        weighted_stance=weighted_stance,
        agreement_ratio=agreement_ratio,
        reasoning=reasoning,
        stance_distribution=stance_distribution(opinions),
        member_weights=weights,
    )


def _classify(agreement: float, dispersion: float) -> ConsensusLevel:
    """Classify consensus from agreement ratio + stance dispersion."""
    if dispersion <= 0.9 and agreement >= 0.8:
        return ConsensusLevel.STRONG
    if agreement >= 0.62:
        return ConsensusLevel.MODERATE
    if agreement >= 0.45:
        return ConsensusLevel.SPLIT
    return ConsensusLevel.NONE


def _reasoning(
    recommendation: Recommendation,
    level: ConsensusLevel,
    agreement: float,
    dispersion: float,
    mode: CommitteeMode,
    opinions: list[MemberOpinion],
    weights: dict,
) -> str:
    """Produce confidence-weighted reasoning explaining the consensus."""
    top = sorted(opinions, key=lambda o: weights[o.role], reverse=True)[:3]
    drivers = ", ".join(
        f"{o.role_title} ({o.recommendation.value}, w={weights[o.role]:.2f})" for o in top
    )
    return (
        f"{level.value}: committee leans '{recommendation.value}'. "
        f"{agreement * 100:.0f}% of evidence weight aligns with this direction "
        f"(stance dispersion {dispersion:.2f}). "
        f"Highest-weight voices: {drivers}. "
        f"Aggregation is evidence-weighted (confidence × coverage), not a headcount vote"
        + (f"; '{mode.value}' mode applied." if mode != CommitteeMode.BALANCED else ".")
    )
