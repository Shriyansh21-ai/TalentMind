"""Promotion equity (Module 4).

Evaluates promotion consistency, level alignment and career progression. Career
progression is read from the existing Career Timeline / Candidate Intelligence
signals (always available); internal level/promotion consistency requires the
injected HRIS provider and is otherwise reported "Not Evaluable" (Module 14).
"""

from __future__ import annotations

from typing import Any, Dict, List

from src.ai.agents.pay_equity.schemas import PromotionEquityAssessment


def _num(source: Dict[str, Any], key: str, default: float = 0.0) -> float:
    try:
        return float(source.get(key, default))
    except (TypeError, ValueError):
        return default


def assess_promotion_equity(context: Dict[str, Any], provider: Any) -> PromotionEquityAssessment:
    """Assess promotion equity for the offer (Module 4)."""
    timeline = context.get("timeline", {}) or {}
    intelligence = context.get("intelligence", {}) or {}
    data_available = bool(provider is not None and getattr(provider, "is_available", lambda: False)())

    growth = _num(intelligence, "career_growth_score")
    progression = timeline.get("leadership_progression") or timeline.get("career_story", "")
    progression_note = (
        f"Career progression signal: {progression}" if progression
        else "Career progression signal is limited in the available intelligence."
    )

    recommendations: List[str] = []
    confidence = 45.0

    if data_available:
        band = provider.get_pay_band(context.get("role", ""), context.get("level", "")) or {}
        target = float(context.get("offer", {}).get("target", 0.0))
        lo = float(band.get("min", 0.0))
        hi = float(band.get("max", 0.0))
        if hi:
            within = lo <= target <= hi
            level_alignment = (
                f"Offer target sits {'within' if within else 'outside'} the {context.get('level', 'role')} band."
            )
            consistency = "Consistent" if within else "Review"
            if not within:
                recommendations.append("Reconcile the level assignment with the published band before promotion parity is set.")
            confidence = 70.0
        else:
            level_alignment = "Company level band unavailable from the provider."
            consistency = "Not Evaluable"
    else:
        level_alignment = "Internal level bands unavailable; level alignment not evaluable without HRIS data."
        consistency = "Not Evaluable"
        recommendations.append("Connect an HRIS source to evaluate internal promotion/level consistency.")

    if growth >= 70:
        recommendations.append("Strong growth trajectory — plan an accelerated review cadence to keep pay aligned.")

    return PromotionEquityAssessment(
        consistency=consistency,
        data_available=data_available,
        level_alignment=level_alignment,
        progression_note=progression_note,
        recommendations=recommendations or ["No promotion-equity actions indicated."],
        confidence=round(confidence, 1),
    )
