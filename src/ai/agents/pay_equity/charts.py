"""Visualization data for the Pay Equity dashboard (Module 10).

Pure data builders (no plotting, no Streamlit import): an equity-risk gauge, a
compression matrix, an approval-flow view, offer alignment, governance status, a
scenario comparison and the executive-review pipeline. Every value is a
qualitative level or a coverage count — never a fabricated payroll figure.
"""

from __future__ import annotations

from typing import Any

from src.ai.agents.pay_equity.schemas import (
    CompressionAssessment,
    EquityRisk,
    EquityScenario,
    ExecutiveReview,
    InversionAssessment,
    PolicyAlignment,
)

_RISK_INDEX = {"low": 1, "medium": 2, "high": 3, "unknown": 0, "unavailable": 0}


def build_chart_data(
    *,
    equity_risk: EquityRisk,
    compression: CompressionAssessment,
    inversion: InversionAssessment,
    policy_alignment: PolicyAlignment,
    executive_review: ExecutiveReview,
    scenarios: list[EquityScenario],
    offer: dict[str, Any],
) -> dict[str, Any]:
    """Build every chart structure for the pay-equity dashboard (Module 10)."""
    return {
        "equity_risk_gauge": {
            "level": equity_risk.level,
            "index": _RISK_INDEX.get(equity_risk.level.lower(), 0),
            "scale": ["Unknown", "Low", "Medium", "High"],
            "data_available": equity_risk.data_available,
        },
        "compression_matrix": {
            "compression": compression.risk_level,
            "inversion": inversion.risk_level,
            "compression_index": _RISK_INDEX.get(compression.risk_level.lower(), 0),
            "inversion_index": _RISK_INDEX.get(inversion.risk_level.lower(), 0),
        },
        "approval_flow": [
            {"approver": a.approver, "required": a.required} for a in executive_review.approvals
        ],
        "offer_alignment": {
            "policy": policy_alignment.policy_name,
            "alignment": policy_alignment.alignment,
            "target": offer.get("target", 0.0),
            "currency": offer.get("currency", "INR"),
            "unit": offer.get("unit", "LPA"),
        },
        "governance_status": {
            "review_level": executive_review.review_level,
            "required_approvers": executive_review.required_approvers(),
        },
        "scenario_comparison": {
            s.name: {"target": s.offer_target, "equity_impact": s.equity_impact} for s in scenarios
        },
        "executive_review_pipeline": [a.approver for a in executive_review.approvals if a.required],
    }
