"""Legal / Compliance review determination.

Decides whether the hiring decision should be routed to Legal and/or Compliance
for human review, based on the governance risk, exceptions and policy findings.
Requesting Legal review means "a person should look at this exposure" — it is
never itself a legal opinion (Module 14).
"""

from __future__ import annotations

from typing import List

from src.ai.agents.compliance.schemas import (
    ComplianceException,
    ComplianceReview,
    GovernanceRisk,
    PolicyCheck,
)


def determine_review(
    governance_risk: GovernanceRisk,
    exceptions: List[ComplianceException],
    policy_checks: List[PolicyCheck],
) -> ComplianceReview:
    """Determine whether Legal / Compliance should review (governance-only)."""
    real_exceptions = [e for e in exceptions if e.kind != "No exceptions detected"]
    high = [e for e in real_exceptions if e.severity == "High"]
    policy_violations = [c for c in policy_checks if c.status == "Violation"]
    pay_equity_flag = any("Pay-equity" in e.kind or "Compensation governance" in e.kind for e in real_exceptions)

    legal = bool(high or policy_violations or pay_equity_flag or governance_risk.level == "High")
    compliance = bool(real_exceptions or governance_risk.level in ("Medium", "High"))

    reviewers: List[str] = []
    if compliance:
        reviewers.append("Compliance")
    if legal:
        reviewers.append("Legal")

    if legal:
        rationale = (
            "Recommend Legal + Compliance review of the governance exposure "
            f"({governance_risk.level} risk). This is a governance routing, not a legal opinion."
        )
    elif compliance:
        rationale = f"Recommend Compliance review ({governance_risk.level} governance risk)."
    else:
        rationale = "No elevated Legal/Compliance review indicated; standard approvals suffice."

    return ComplianceReview(
        legal_review_recommended=legal,
        compliance_review_recommended=compliance,
        reviewers=reviewers,
        rationale=rationale,
    )
