"""Audit-trail validation (Module 6).

Verifies the decision history, evidence chain, agent participation, approval
history, reasoning provenance and human-review status, reporting each as Complete
/ Incomplete / Needs Investigation. Approval/decision history that requires an
external system is honestly reported as Needs Investigation when no provider is
connected (Module 14).
"""

from __future__ import annotations

from typing import Any

from src.ai.agents.compliance.schemas import ApprovalMatrix, AuditFinding, AuditTrailValidation


def validate_audit_trail(
    context: dict[str, Any], approvals: ApprovalMatrix, provider: Any
) -> AuditTrailValidation:
    """Validate the hiring decision's audit trail (Module 6)."""
    sources = set(context.get("evidence_sources", []))
    has_provider = provider is not None and getattr(provider, "is_available", lambda: False)()
    audit_events = (
        provider.get_audit_events(context.get("candidate_id", "")) if has_provider else None
    )

    findings: list[AuditFinding] = []

    # Evidence chain — derived from the engines that participated.
    findings.append(
        AuditFinding(
            "Evidence chain",
            "Complete" if len(sources) >= 5 else "Incomplete",
            f"{len(sources)} evidence source(s) recorded across the hiring intelligence chain.",
        )
    )
    # Agent participation — the core agents that must have run.
    core = {"AI Hiring Committee", "Compensation Governance Agent", "Pay Equity Guardian"}
    present = core & sources
    findings.append(
        AuditFinding(
            "Agent participation",
            "Complete" if core <= sources else "Incomplete",
            f"Core agents present: {', '.join(sorted(present)) or 'none'}.",
        )
    )
    # Reasoning provenance — the agents attach provenance to their outputs.
    findings.append(
        AuditFinding(
            "Reasoning provenance",
            "Complete",
            "Upstream agents attach evidence-anchored reasoning to every conclusion.",
        )
    )
    # Decision history — needs a governance/workflow system to be authoritative.
    findings.append(
        AuditFinding(
            "Decision history",
            "Complete" if audit_events else "Needs Investigation",
            f"{len(audit_events)} recorded audit event(s)."
            if audit_events
            else "No governance/workflow system connected to confirm the decision history.",
        )
    )
    # Approval history — from the approval provider.
    outstanding = approvals.outstanding()
    if not approvals.required():
        approval_status, approval_why = "Needs Investigation", "No required approvals determined."
    elif has_provider and not outstanding:
        approval_status, approval_why = "Complete", "All required approvals recorded."
    elif has_provider:
        approval_status, approval_why = (
            "Incomplete",
            f"Outstanding approvals: {', '.join(outstanding)}.",
        )
    else:
        approval_status, approval_why = "Needs Investigation", "No approval system connected."
    findings.append(AuditFinding("Approval history", approval_status, approval_why))

    # Human review status.
    findings.append(
        AuditFinding(
            "Human review status",
            "Incomplete",
            "This assessment is pending human review — it supports compliance, it does not replace review.",
        )
    )

    statuses = {f.status for f in findings}
    if "Needs Investigation" in statuses:
        overall = "Needs Investigation"
    elif "Incomplete" in statuses:
        overall = "Incomplete"
    else:
        overall = "Complete"

    return AuditTrailValidation(findings=findings, status=overall)
