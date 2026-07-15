"""Future compensation outlook (Module 9).

Estimates promotion readiness, future compensation progression, retention
incentives, learning investment, career-growth compensation and long-term talent
value — each a heuristic :class:`Estimate` with an explicit confidence, derived
from the Candidate Intelligence and Career Timeline signals (Module 9 / 16).
Nothing is fabricated; every estimate cites its basis.
"""

from __future__ import annotations

from typing import Any, Dict, List

from src.ai.agents.compensation.schemas import Estimate, FutureCompensationOutlook


def _num(source: Dict[str, Any], key: str, default: float = 0.0) -> float:
    try:
        return float(source.get(key, default))
    except (TypeError, ValueError):
        return default


def _level(value: float) -> str:
    """Map a 0-100 signal to a qualitative level."""
    if value >= 70:
        return "High"
    if value >= 45:
        return "Moderate"
    return "Low"


def build_future_outlook(evidence: Dict[str, Any]) -> FutureCompensationOutlook:
    """Build the future compensation outlook (Module 9)."""
    intelligence = evidence.get("intelligence") or {}
    timeline = evidence.get("timeline") or {}

    base_conf = _num(intelligence, "confidence") or 55.0
    ci: List[str] = ["Candidate Intelligence engine"]
    ct: List[str] = ["Career Timeline Intelligence"]

    growth = _num(intelligence, "career_growth_score")
    learning = _num(intelligence, "learning_velocity")
    leadership = _num(intelligence, "leadership_score")
    stability = _num(timeline, "career_stability")
    overall = _num(intelligence, "overall_score")

    def est(value: float, rationale: str, basis: List[str], kind: str = "Heuristic Estimate") -> Estimate:
        return Estimate(
            level=_level(value),
            rationale=rationale,
            confidence=round(base_conf, 1),
            kind=kind,
            basis=basis,
        )

    return FutureCompensationOutlook(
        promotion_readiness=est(
            (growth + leadership) / 2.0,
            "Promotion readiness from career-growth trajectory and leadership signal.",
            ci + ct,
        ),
        progression=est(
            growth,
            "Expected compensation progression tracks the career-growth trajectory.",
            ct,
        ),
        retention_incentives=est(
            100.0 - (100.0 - stability if stability else 40.0),
            "Retention incentives calibrated to career stability; lower stability warrants stronger retention design.",
            ct,
        ),
        learning_investment=est(
            learning,
            "Learning-investment value from the learning-velocity signal.",
            ci,
        ),
        growth_compensation=est(
            (growth + overall) / 2.0,
            "Career-growth compensation reflects trajectory and overall capability.",
            ci + ct,
        ),
        long_term_value=est(
            overall,
            "Long-term talent value from the overall intelligence signal.",
            ci,
        ),
    )
