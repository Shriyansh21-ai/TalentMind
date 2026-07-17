"""Safety + coverage validators for the Hiring Compliance Agent (Module 14).

Pure functions that (a) report which evidence sources were available and (b)
assert the safety guarantees: the narrative must contain no legal-advice /
employment-law / regulatory-ruling language, and controls that need an external
system must not be reported as satisfied without one. No I/O.
"""

from __future__ import annotations

from typing import Any

from src.ai.agents.compliance.schemas import ApprovalMatrix, ComplianceNarrative

_SOURCE_LABELS = {
    "pay_equity": "Pay Equity Guardian",
    "compensation": "Compensation Governance Agent",
    "committee": "AI Hiring Committee",
    "interview": "Interview Intelligence",
    "resume": "Resume Analyst Agent",
    "jd": "JD Analyst Agent",
    "governance_data": "Connected governance/workflow data",
}

# Assertion-specific language that would indicate the system GIVING legal advice
# or issuing a ruling. Phrased affirmatively so negating disclaimers (e.g. "this
# is not legal advice") do not trip the guard.
_FORBIDDEN_PHRASES = (
    "here is legal advice",
    "this constitutes legal advice",
    "our legal opinion is",
    "legal opinion:",
    "you should sue",
    "is illegal",
    "violates the law",
    "breaks the law",
    "unlawful",
    "court will rule",
    "regulatory ruling",
)


def available_sources(evidence: dict[str, Any]) -> list[str]:
    """Return the evidence sources actually consulted for this compliance review."""
    return list(dict.fromkeys(evidence.get("evidence_sources", [])))


def evidence_coverage_warnings(evidence: dict[str, Any]) -> list[str]:
    """Return warnings when key evidence sources are missing (Module 14)."""
    warnings: list[str] = []
    if not evidence.get("data_available"):
        warnings.append(
            "No governance / workflow / document system connected — approval and "
            "documentation completion could not be confirmed. Findings are provisional."
        )
    sources = set(evidence.get("evidence_sources", []))
    if "Pay Equity Guardian" not in sources:
        warnings.append("Pay-equity review not available — governance coverage is limited.")
    return warnings


def validate_safety(
    narrative: ComplianceNarrative, approvals: ApprovalMatrix, data_available: bool
) -> list[str]:
    """Assert the no-legal-advice / no-fabrication guarantees (Module 14)."""
    warnings: list[str] = []

    blob = " ".join(str(v) for v in narrative.to_dict().values() if isinstance(v, str)).lower()
    for phrase in _FORBIDDEN_PHRASES:
        if phrase in blob:
            warnings.append(
                f"Narrative contains unsupported legal-advice language ({phrase!r}); flagged."
            )

    # Without a connected system, no required approval may be reported Complete.
    if not data_available:
        for a in approvals.approvals:
            if a.required and a.state == "Complete":
                warnings.append(
                    f"{a.approver} approval reported Complete without a connected approval system; flagged."
                )

    return warnings
