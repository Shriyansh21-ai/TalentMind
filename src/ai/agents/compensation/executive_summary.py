"""Executive compensation report assembly (Module 10).

The Module 10 report is the same :class:`CompensationReport` the engine produces,
presented in a fixed executive section order. This module owns the section
registry + the one-paragraph executive digest used by the copilot tool and the
export view — pure presentation over the assembled report, no recomputation.
"""

from __future__ import annotations

from typing import List, Tuple

from src.ai.agents.compensation.schemas import CompensationReport

# The ordered sections of the executive compensation report (Module 10).
REPORT_SECTIONS: List[Tuple[str, str]] = [
    ("executive_summary", "Executive Summary"),
    ("compensation_recommendation", "Compensation Recommendation"),
    ("offer_justification", "Offer Justification"),
    ("business_value", "Business Value"),
    ("budget_assessment", "Budget Assessment"),
    ("negotiation_strategy", "Negotiation Strategy"),
    ("governance_notes", "Governance Notes"),
    ("internal_equity", "Internal Equity"),
    ("future_growth", "Future Growth"),
    ("risk_assessment", "Risk Assessment"),
    ("audit_trail", "Transparency Audit Trail"),
]


def section_titles() -> List[str]:
    """Return the ordered executive-report section titles."""
    return [title for _key, title in REPORT_SECTIONS]


def build_executive_digest(report: CompensationReport) -> str:
    """Return a one-paragraph executive digest of the compensation decision."""
    band = report.recommended_range
    return (
        f"Recommended {band.formatted()} for {report.candidate_overview.get('title', 'the candidate')}. "
        f"Market position: {report.market_position.position} (internal heuristic model). "
        f"Hire type: {report.budget.hire_type}. "
        f"Offer-acceptance likelihood: {report.negotiation.acceptance_likelihood}. "
        f"Confidence: {band.confidence_label}. "
        f"Approvals required: {', '.join(report.audit_trail.approvals_required)}. "
        f"Decision {report.audit_trail.decision_id} is {report.audit_trail.human_review_status.lower()}."
    )
