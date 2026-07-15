"""Market position assessment (Module 4).

Estimates where the recommended range sits — Below Market, Market Competitive,
Premium, Strategic Premium or Budget-Constrained — **without fabricating market
data**. When no external salary survey is wired in (the default), the assessment
is explicitly labelled "Recommendation based on internal heuristic model" and
reasons purely from internal signals: how the recommended target compares to the
candidate's stated expectation, the applied premiums and the hiring stance
(Module 16).
"""

from __future__ import annotations

from typing import Any, Dict, List

from src.ai.agents.compensation.schemas import CompensationRange, MarketPosition


def _num(source: Dict[str, Any], key: str, default: float = 0.0) -> float:
    try:
        return float(source.get(key, default))
    except (TypeError, ValueError):
        return default


def assess_market_position(evidence: Dict[str, Any], band: CompensationRange) -> MarketPosition:
    """Estimate the market position of the recommended range (Module 4).

    Args:
        evidence: The aggregated compensation evidence dict.
        band: The recommended compensation range.

    Returns:
        A :class:`MarketPosition`, honest about the absence of market data.
    """
    comp = evidence.get("candidate_comp") or {}
    exp_min = _num(comp, "expected_min")
    exp_max = _num(comp, "expected_max")
    expected_mid = (exp_min + exp_max) / 2.0 if exp_max > 0 else 0.0

    intelligence = evidence.get("intelligence") or {}
    committee = evidence.get("committee") or {}
    stance = str((committee.get("consensus") or {}).get("recommendation", "")) or str(
        (evidence.get("recommendation") or {}).get("recommendation", "")
    )

    assumptions: List[str] = [
        "No external salary survey or market benchmark is connected; position is "
        "inferred from internal signals only.",
    ]
    basis: List[str] = []

    # Position relative to the candidate's own expectation (the only real anchor).
    if expected_mid:
        ratio = band.target / expected_mid if expected_mid else 1.0
        basis.append(
            f"Recommended target {band.target:.1f} vs. candidate expectation midpoint "
            f"{expected_mid:.1f} {band.unit} (ratio {ratio:.2f})."
        )
        if ratio < 0.95:
            position = "Budget-Constrained"
        elif ratio <= 1.08:
            position = "Market Competitive"
        elif ratio <= 1.2:
            position = "Premium"
        else:
            position = "Strategic Premium"
    else:
        assumptions.append("Candidate stated no expectation; position derived from seniority baseline.")
        position = "Market Competitive"

    # A "Strong Hire" stance with strong signals lifts a Premium to Strategic.
    strong_signals = _num(intelligence, "technical_score") >= 75 or _num(intelligence, "leadership_score") >= 70
    if "strong" in stance.lower() and strong_signals and position == "Premium":
        position = "Strategic Premium"
        basis.append(f"Elevated to Strategic Premium by the '{stance}' stance and strong capability signals.")

    return MarketPosition(
        position=position,
        rationale=(
            f"Assessed as {position} using the internal heuristic model. "
            + (basis[0] if basis else "Insufficient signals for a finer read.")
        ),
        data_available=False,
        data_note="Recommendation based on internal heuristic model.",
        assumptions=assumptions,
        basis=basis,
    )
