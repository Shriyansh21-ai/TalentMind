"""Compliance exceptions (Module 7).

Generates structured exception reports — missing interview, missing approval,
missing documentation, policy conflict, compensation-governance issue, pay-equity
concern and committee disagreement — from the assembled compliance signals. Each
exception carries a severity, a recommendation, an epistemic register and a
confidence. It flags governance issues only; it makes no legal determination
(Module 14).
"""

from __future__ import annotations

from typing import Any

from src.ai.agents.compliance.schemas import (
    ApprovalMatrix,
    ComplianceException,
    DocumentationReview,
    PolicyCheck,
    WorkflowCompliance,
)


def detect_exceptions(
    context: dict[str, Any],
    workflow: WorkflowCompliance,
    approvals: ApprovalMatrix,
    documentation: DocumentationReview,
    policy_checks: list[PolicyCheck],
) -> list[ComplianceException]:
    """Detect structured compliance exceptions (Module 7)."""
    exceptions: list[ComplianceException] = []

    # Missing critical workflow steps (e.g. interview / committee).
    for step in workflow.steps:
        if step.status == "Missing" and step.critical:
            exceptions.append(
                ComplianceException(
                    kind=f"Missing step: {step.name}",
                    severity="High",
                    detail=step.rationale,
                    recommendation=f"Complete '{step.name}' before finalizing the hire.",
                    register="Missing Information",
                    confidence=80.0,
                )
            )

    # Outstanding required approvals.
    for approver in approvals.outstanding():
        confirmable = any(
            a.approver == approver and a.state == "Requires Review" for a in approvals.approvals
        )
        exceptions.append(
            ComplianceException(
                kind=f"Missing approval: {approver}",
                severity="Medium" if confirmable else "High",
                detail=f"{approver} approval is required but not confirmed complete.",
                recommendation=f"Obtain/confirm {approver} approval.",
                register="Missing Information",
                confidence=70.0,
            )
        )

    # Missing documentation.
    for doc in documentation.missing():
        exceptions.append(
            ComplianceException(
                kind=f"Missing documentation: {doc}",
                severity="Medium",
                detail=f"Required document '{doc}' is not present.",
                recommendation=f"File the {doc}.",
                register="Missing Information",
                confidence=70.0,
            )
        )

    # Policy conflicts.
    for check in policy_checks:
        if check.status == "Violation":
            exceptions.append(
                ComplianceException(
                    kind=f"Policy conflict: {check.policy_name}",
                    severity="High",
                    detail=check.rationale,
                    recommendation="; ".join(check.required_actions)
                    or "Route for governance review.",
                    register="Company Policy",
                    confidence=75.0,
                )
            )

    # Compensation-governance + pay-equity concerns (reused signals).
    if context.get("equity_risk_level") == "High":
        exceptions.append(
            ComplianceException(
                kind="Pay-equity concern",
                severity="High",
                detail="The Pay Equity Guardian flagged High internal-equity risk on connected data.",
                recommendation="Route to HR compensation / Legal for pay-equity review.",
                register="Observed Evidence",
                confidence=75.0,
            )
        )
    if context.get("pay_policy_alignment") == "Violation":
        exceptions.append(
            ComplianceException(
                kind="Compensation governance issue",
                severity="Medium",
                detail="The pay policy alignment is a documented exception requiring review.",
                recommendation="Document the exception and obtain the required sign-off.",
                register="Company Policy",
                confidence=70.0,
            )
        )

    # Committee disagreement — gated (internal committee detail is not exposed).
    if context.get("committee_disagreement") is True:
        exceptions.append(
            ComplianceException(
                kind="Committee disagreement",
                severity="Medium",
                detail="The hiring committee recorded material disagreement.",
                recommendation="Confirm the chair's rationale resolves the disagreement.",
                register="Observed Evidence",
                confidence=60.0,
            )
        )

    if not exceptions:
        exceptions.append(
            ComplianceException(
                kind="No exceptions detected",
                severity="Low",
                detail="No governance exceptions surfaced from the available evidence.",
                recommendation="Proceed through standard approvals.",
                register="Observed Evidence",
                confidence=60.0,
            )
        )
    return exceptions
