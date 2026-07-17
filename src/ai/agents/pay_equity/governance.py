"""Governance notes + transparency-report scaffolding (Modules 6, 9).

Owns the governance-note synthesis shared by the fairness assessment and the
transparency report, plus the ordered section registry for the Module 9
executive transparency report. Pure presentation/synthesis — no engine
recomputation, no legal conclusions (Module 14).
"""

from __future__ import annotations

from typing import Any

from src.ai.agents.pay_equity.schemas import (
    CompressionAssessment,
    ExecutiveReview,
    InversionAssessment,
    PolicyAlignment,
)

# Ordered sections of the executive transparency report (Module 9).
REPORT_SECTIONS: list[tuple[str, str]] = [
    ("executive_summary", "Executive Summary"),
    ("equity_assessment", "Equity Assessment"),
    ("compression_analysis", "Compression Analysis"),
    ("promotion_analysis", "Promotion Analysis"),
    ("governance_findings", "Governance Findings"),
    ("approvals_required", "Approvals Required"),
    ("recommendations", "Recommendations"),
    ("evidence_sources", "Evidence Sources"),
]


def section_titles() -> list[str]:
    """Return the ordered transparency-report section titles."""
    return [title for _key, title in REPORT_SECTIONS]


def build_governance_notes(
    context: dict[str, Any],
    compression: CompressionAssessment,
    inversion: InversionAssessment,
    policy_alignment: PolicyAlignment,
    executive_review: ExecutiveReview,
) -> list[str]:
    """Synthesize governance notes shared by fairness + the transparency report."""
    notes: list[str] = []

    if not (compression.data_available or inversion.data_available):
        notes.append(
            "Internal compensation data is unavailable; compression and inversion "
            "checks could not run. Equity findings are provisional."
        )
    else:
        if compression.risk_level in ("Medium", "High"):
            notes.append(f"Compression risk is {compression.risk_level}: {compression.rationale}")
        if inversion.risk_level in ("Medium", "High"):
            notes.append(f"Inversion risk is {inversion.risk_level}: {inversion.rationale}")

    if policy_alignment.alignment in ("Partial", "Violation"):
        notes.append(
            f"Policy '{policy_alignment.policy_name}' alignment is {policy_alignment.alignment}: "
            + "; ".join(policy_alignment.violations)
        )

    if executive_review.review_level != "Standard":
        notes.append(
            f"Elevated review path: {executive_review.review_level}. "
            f"Required approvers: {', '.join(executive_review.required_approvers())}."
        )

    notes.append(
        "This is a governance assessment only — it surfaces areas for human review and "
        "makes no legal determination and no discrimination finding."
    )
    return notes
