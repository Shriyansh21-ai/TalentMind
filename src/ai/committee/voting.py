"""Stance model + evidence weighting (Module 4).

The committee never decides by majority vote. Each member's opinion maps to a
numeric *stance*; each opinion carries an evidence-derived *weight* (confidence ×
evidence coverage, adjusted by the operating mode). Consensus is the
weight-weighted stance — so a single well-evidenced, high-confidence expert can
outweigh several thinly-supported opinions.
"""

from __future__ import annotations

from typing import List

from src.ai.committee.schemas import (
    CommitteeMode,
    MemberOpinion,
    Recommendation,
)

# Numeric stance for each recommendation label.
STANCE = {
    Recommendation.NO_HIRE: -2.0,
    Recommendation.LEAN_NO_HIRE: -1.0,
    Recommendation.HOLD: 0.0,
    Recommendation.LEAN_HIRE: 1.0,
    Recommendation.HIRE: 2.0,
    Recommendation.STRONG_HIRE: 3.0,
}

# How many independent evidence items a member is expected to cite (for coverage).
_EXPECTED_EVIDENCE = 3


def stance_of(recommendation: Recommendation) -> float:
    """Return the numeric stance for a recommendation label."""
    return STANCE.get(recommendation, 0.0)


def recommendation_from_stance(stance: float) -> Recommendation:
    """Map a weighted stance back to a recommendation label (Module 4/6)."""
    if stance >= 2.0:
        return Recommendation.STRONG_HIRE
    if stance >= 1.1:
        return Recommendation.HIRE
    if stance >= 0.4:
        return Recommendation.LEAN_HIRE
    if stance > -0.4:
        return Recommendation.HOLD
    if stance > -1.1:
        return Recommendation.LEAN_NO_HIRE
    return Recommendation.NO_HIRE


def evidence_coverage(opinion: MemberOpinion) -> float:
    """Return 0-1 evidence coverage for a member's opinion."""
    if opinion.abstained:
        return 0.2
    return max(0.0, min(1.0, len(opinion.evidence) / _EXPECTED_EVIDENCE))


def weight_of(opinion: MemberOpinion, mode: CommitteeMode) -> float:
    """Return the evidence weight of an opinion under a committee mode.

    weight = (confidence/100) × evidence_coverage × role_mode_multiplier.
    Modes re-weight *deterministically* (no randomness): the conservative mode
    amplifies the Risk Officer; the optimistic mode amplifies growth/technical
    upside. This shifts emphasis, never invents opinions.
    """
    base = (max(0.0, min(100.0, opinion.confidence)) / 100.0) * evidence_coverage(opinion)
    multiplier = 1.0
    if mode == CommitteeMode.CONSERVATIVE:
        if opinion.role == "risk_officer":
            multiplier = 1.6
        elif opinion.role in ("career_growth", "resume_expert"):
            multiplier = 0.85
    elif mode == CommitteeMode.OPTIMISTIC:
        if opinion.role in ("career_growth", "technical_hiring_manager", "hiring_analyst"):
            multiplier = 1.3
        elif opinion.role == "risk_officer":
            multiplier = 0.85
    return base * multiplier


def mode_stance_bias(mode: CommitteeMode) -> float:
    """Return a small deterministic stance bias applied to the weighted average.

    Optimistic nudges the reading up; conservative nudges it down. Bounded and
    fixed, so runs are reproducible.
    """
    if mode == CommitteeMode.OPTIMISTIC:
        return 0.25
    if mode == CommitteeMode.CONSERVATIVE:
        return -0.25
    return 0.0


def stance_distribution(opinions: List[MemberOpinion]) -> dict:
    """Return a count of members per recommendation label (transparency only)."""
    dist: dict = {}
    for opinion in opinions:
        key = opinion.recommendation.value
        dist[key] = dist.get(key, 0) + 1
    return dist
