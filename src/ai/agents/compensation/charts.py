"""Visualization data for the Compensation Governance dashboard (Module 11).

Pure data builders (no plotting, no Streamlit import) that turn the assembled
report into chart-ready structures: the recommended salary range, a scenario
comparison, the market position, a budget-allocation view, offer confidence,
negotiation readiness, a compensation timeline (future outlook) and a
business-value overview. Keeping this pure makes it trivially testable and lets
the UI render it with any charting library. Every figure is a heuristic estimate,
never a fabricated market number.
"""

from __future__ import annotations

from typing import Any

from src.ai.agents.compensation.schemas import (
    BudgetAssessment,
    CompensationRange,
    FutureCompensationOutlook,
    MarketPosition,
    NegotiationIntelligence,
    OfferScenario,
)

# Ordered market-position ladder for the position gauge.
_POSITION_LADDER = [
    "Budget-Constrained",
    "Below Market",
    "Market Competitive",
    "Premium",
    "Strategic Premium",
]
_LIKELIHOOD = {"high": 1.0, "moderate": 0.6, "low": 0.3, "": 0.0}


def build_chart_data(
    *,
    band: CompensationRange,
    scenarios: list[OfferScenario],
    market: MarketPosition,
    budget: BudgetAssessment,
    negotiation: NegotiationIntelligence,
    future: FutureCompensationOutlook,
) -> dict[str, Any]:
    """Build every chart structure for the compensation dashboard (Module 11)."""
    return {
        "recommended_range": {
            "currency": band.currency,
            "unit": band.unit,
            "minimum": band.minimum,
            "target": band.target,
            "maximum": band.maximum,
        },
        "scenario_comparison": {
            s.name: {
                "minimum": s.comp_range.minimum,
                "target": s.comp_range.target,
                "maximum": s.comp_range.maximum,
            }
            for s in scenarios
        },
        "market_position": {
            "position": market.position,
            "index": _POSITION_LADDER.index(market.position)
            if market.position in _POSITION_LADDER
            else 2,
            "scale": list(_POSITION_LADDER),
            "data_available": market.data_available,
        },
        "budget_allocation": {
            "hire_type": budget.hire_type,
            "priority": budget.hiring_priority,
            "utilization": budget.budget_utilization,
            "confidence": budget.confidence,
        },
        "offer_confidence": round(band.confidence, 1),
        "negotiation_readiness": {
            "acceptance_likelihood": negotiation.acceptance_likelihood,
            "acceptance_score": _LIKELIHOOD.get(negotiation.acceptance_likelihood.lower(), 0.0),
            "negotiation_probability": negotiation.negotiation_probability,
            "confidence": negotiation.confidence,
        },
        "compensation_timeline": {name: est.confidence for name, est in future.items()},
        "business_value": {name: est.level for name, est in future.items()},
    }
