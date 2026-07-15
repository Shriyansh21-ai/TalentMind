"""Hiring workflow compliance (Module 1).

Evaluates each required workflow step — resume screen, JD, interview, committee,
compensation, pay-equity, required approvals and documentation — as Completed /
Missing / Requires Review, deriving presence from the evidence the upstream
engines produced plus the approval matrix and documentation review. Nothing is
fabricated (Module 14).
"""

from __future__ import annotations

from typing import Any, Dict

from src.ai.agents.compliance.schemas import (
    ApprovalMatrix,
    DocumentationReview,
    WorkflowCompliance,
    WorkflowStep,
)
from src.ai.agents.compliance.templates import WORKFLOW_STEPS


def assess_workflow(
    context: Dict[str, Any],
    approvals: ApprovalMatrix,
    documentation: DocumentationReview,
) -> WorkflowCompliance:
    """Assess overall hiring-workflow compliance (Module 1)."""
    sources = set(context.get("evidence_sources", []))
    steps = []

    for definition in WORKFLOW_STEPS:
        if definition.evidence_source == "__approvals__":
            outstanding = approvals.outstanding()
            if not approvals.required():
                status, register, why = "Requires Review", "Missing Information", "No required approvals determined."
            elif not outstanding:
                status, register, why = "Completed", "Observed Evidence", "All required approvals are complete."
            elif any(a.state == "Requires Review" for a in approvals.approvals if a.required):
                status, register, why = "Requires Review", "Missing Information", (
                    f"Approvals pending confirmation: {', '.join(outstanding)}."
                )
            else:
                status, register, why = "Missing", "Missing Information", f"Missing approvals: {', '.join(outstanding)}."
        elif definition.evidence_source == "__documentation__":
            missing = documentation.missing()
            pending = [d.name for d in documentation.documents if d.state == "Requires Review"]
            if missing:
                status, register, why = "Missing", "Missing Information", f"Missing documents: {', '.join(missing)}."
            elif pending:
                status, register, why = "Requires Review", "Missing Information", f"Documents to confirm filed: {', '.join(pending)}."
            else:
                status, register, why = "Completed", "Observed Evidence", "All required documentation is present."
        elif definition.evidence_source in sources:
            status, register, why = "Completed", "Observed Evidence", f"{definition.name} confirmed via {definition.evidence_source}."
        else:
            status, register, why = "Missing", "Missing Information", f"{definition.name} not evidenced by any upstream engine."

        steps.append(
            WorkflowStep(name=definition.name, status=status, rationale=why, register=register, critical=definition.critical)
        )

    completed = sum(1 for s in steps if s.status == "Completed")
    total = len(steps)
    critical_missing = any(s.status == "Missing" and s.critical for s in steps)
    if completed == total:
        overall = "Compliant"
    elif critical_missing:
        overall = "Incomplete"
    else:
        overall = "Requires Review"
    confidence = round(60.0 + 40.0 * (completed / total if total else 0.0), 1)

    return WorkflowCompliance(steps=steps, completed=completed, total=total, status=overall, confidence=confidence)
