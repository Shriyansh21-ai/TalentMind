"""Deterministic composer for the ComplianceNarrative (offline reasoning).

Maps the aggregated evidence dict to a :class:`ComplianceNarrative`-shaped dict by
**restating and organizing** the computed compliance signals — never inventing a
document, an approval or a legal conclusion (Module 14). This lets the compliance
agent run fully offline with a structural no-fabrication / no-legal-advice
guarantee.
"""

from __future__ import annotations

from typing import Any


def compose_compliance_narrative(evidence: dict[str, Any]) -> dict[str, Any]:
    """Deterministically compose a :class:`ComplianceNarrative` from evidence."""
    ov = evidence.get("candidate_overview") or {}
    title = ov.get("title") or "the candidate"
    workflow = evidence.get("workflow") or {}
    approvals = evidence.get("approvals") or {}
    documentation = evidence.get("documentation") or {}
    audit = evidence.get("audit") or {}
    risk = evidence.get("governance_risk") or {}
    review = evidence.get("review") or {}
    policy_checks = evidence.get("policy_checks") or []
    exceptions = evidence.get("exceptions") or []
    data_available = bool(evidence.get("data_available"))

    wf_status = workflow.get("status", "Requires Review")
    risk_level = risk.get("level", "Medium")
    outstanding = approvals.get("outstanding", [])
    missing_docs = documentation.get("missing", [])

    summary = (
        f"Hiring-compliance review for {title}. Workflow status: {wf_status} "
        f"({workflow.get('completed', 0)}/{workflow.get('total', 0)} steps). "
        f"Governance risk: {risk_level}. "
        + (
            f"Recommend {', '.join(review.get('reviewers', []))} review. "
            if review.get("reviewers")
            else "No elevated Legal/Compliance review indicated. "
        )
        + "This is a governance assessment, not legal advice."
    )

    key_findings: list[str] = []
    real_exceptions = [e for e in exceptions if e.get("kind") != "No exceptions detected"]
    for e in real_exceptions[:5]:
        key_findings.append(f"[{e.get('severity')}] {e.get('kind')}: {e.get('detail')}")
    if not key_findings:
        key_findings.append("No governance exceptions surfaced from the available evidence.")

    required_actions: list[str] = []
    for e in real_exceptions:
        if e.get("recommendation"):
            required_actions.append(e["recommendation"])
    for c in policy_checks:
        required_actions.extend(c.get("required_actions", []))
    required_actions = list(dict.fromkeys(a for a in required_actions if a))[:6]

    assumptions: list[str] = []
    if not data_available:
        assumptions.append(
            "No governance/workflow/document system connected; approval and document "
            "completion could not be confirmed and are treated as pending review."
        )
    assumptions.append(
        "Compliance findings support human review; they are not a legal determination."
    )

    if wf_status == "Compliant" and risk_level == "Low":
        confidence_note = (
            "Confidence is solid: the evidenced workflow is complete and no exceptions surfaced."
        )
    elif not data_available:
        confidence_note = "Confidence is limited: external approval/document systems are not connected, so several controls are pending review."
    else:
        confidence_note = "Confidence is moderate: findings rest on the connected data and the existing intelligence chain."

    return {
        "executive_summary": summary,
        "workflow_note": (
            f"{workflow.get('completed', 0)} of {workflow.get('total', 0)} required steps completed; "
            f"overall {wf_status}."
        ),
        "approval_note": (
            f"Required approvals: {', '.join(approvals.get('required', [])) or 'none determined'}. "
            + (
                f"Outstanding: {', '.join(outstanding)}."
                if outstanding
                else "No outstanding approvals."
            )
        ),
        "policy_note": (
            "; ".join(f"{c.get('policy_name')}: {c.get('status')}" for c in policy_checks)
            if policy_checks
            else "No policies evaluated."
        ),
        "documentation_note": (
            f"Missing documents: {', '.join(missing_docs)}."
            if missing_docs
            else "All required documentation is present or pending confirmation."
        ),
        "audit_note": f"Audit-trail readiness: {audit.get('status', 'Needs Investigation')}.",
        "risk_note": (
            f"Governance risk is {risk_level}. Drivers: "
            + "; ".join(risk.get("drivers", [])[:3])
            + "."
        ),
        "required_actions": required_actions or ["Proceed through standard approvals."],
        "key_findings": key_findings,
        "assumptions": assumptions,
        "human_review_recommendations": risk.get("human_review_recommendations", [])[:5]
        or ["Standard approvals only."],
        "confidence_note": confidence_note,
    }
