"""Deterministic composer for the AuditNarrative (offline reasoning).

Maps the reconstructed audit evidence to an :class:`AuditNarrative`-shaped dict by
**restating and organizing** what the reconstruction found — never fabricating
evidence, approvals or history, and never issuing a legal opinion (Module 14).
This lets the audit agent run fully offline with a structural no-fabrication
guarantee.
"""

from __future__ import annotations

from typing import Any


def compose_audit_narrative(evidence: dict[str, Any]) -> dict[str, Any]:
    """Deterministically compose an :class:`AuditNarrative` from evidence."""
    ov = evidence.get("candidate_overview") or {}
    title = ov.get("title") or "the candidate"
    agents = evidence.get("agents_participated") or []
    readiness = evidence.get("audit_readiness") or {}
    reasoning = evidence.get("reasoning") or {}
    responsibility = evidence.get("responsibility") or []
    governance = evidence.get("governance_explanations") or []
    history = evidence.get("history") or {}
    data_available = bool(evidence.get("data_available"))

    level = readiness.get("readiness_level", "Medium")
    status = readiness.get("status", "Requires Review")

    summary = (
        f"Hiring-decision audit for {title}. {len(agents)} AI agent(s) participated; "
        f"audit readiness is {status} ({level}). The decision journey is reconstructed "
        "from artefacts on record — this reconstructs the record and gives no legal opinion."
    )

    human = [d for d in responsibility if d.get("responsible_party") != "AI"]
    ai = [d for d in responsibility if d.get("responsible_party") == "AI"]
    observed_human = [d for d in human if d.get("status") == "Observed"]

    responsibility_note = (
        f"{len(ai)} AI decision point(s) and {len(human)} human decision point(s) identified; "
        f"{len(observed_human)} human approval(s) verified on record. "
        "AI recommendations and human decisions are kept strictly separate."
    )

    key_findings: list[str] = []
    for d in reasoning.get("ai_decisions", [])[:3]:
        key_findings.append(d)
    if not key_findings:
        key_findings.append("No AI decisions were evidenced.")

    outstanding: list[str] = []
    outstanding += [f"Missing evidence: {m}" for m in readiness.get("missing_evidence", [])[:3]]
    outstanding += [f"Missing approval: {m}" for m in readiness.get("missing_approvals", [])[:3]]
    outstanding += [f"Unverified: {m}" for m in readiness.get("unverified_decisions", [])[:2]]
    if not outstanding:
        outstanding.append("No outstanding audit gaps on record.")

    audit_recommendations: list[str] = []
    if readiness.get("missing_approvals"):
        audit_recommendations.append(
            "Confirm the outstanding approvals in the approval system of record."
        )
    if readiness.get("missing_documents"):
        audit_recommendations.append("File the missing documentation before sign-off.")
    if not data_available:
        audit_recommendations.append(
            "Connect an audit archive to enable full historical reconstruction."
        )
    if not audit_recommendations:
        audit_recommendations.append(
            "Retain the current evidence set; the journey is well-reconstructed."
        )

    assumptions = [
        "This reconstruction reflects only artefacts on record; it does not add or rewrite history."
    ]
    if not data_available:
        assumptions.append(
            "No audit archive connected; human approvals and history are unverified."
        )

    if level == "High":
        confidence_note = (
            "Confidence is high: the journey is fully reconstructable from the evidence on record."
        )
    elif not data_available:
        confidence_note = "Confidence is limited: approval/history systems are not connected, so several steps are unverified."
    else:
        confidence_note = "Confidence is moderate: the AI decision chain is on record; some human/approval steps are unverified."

    return {
        "executive_summary": summary,
        "decision_journey_note": (
            "Reconstructed journey: " + " -> ".join(a for a in agents) + "."
            if agents
            else "No agent participation was evidenced."
        ),
        "evidence_note": (
            f"{len(agents)} evidence source(s) on record with documented provenance; "
            f"missing: {', '.join(readiness.get('missing_evidence', [])) or 'none'}."
        ),
        "responsibility_note": responsibility_note,
        "governance_note": (
            "; ".join(f"{g.get('topic')}: {g.get('explanation', '')[:120]}" for g in governance[:3])
            if governance
            else "No governance events evidenced."
        ),
        "readiness_note": (
            f"Audit readiness {status} ({level}). {readiness.get('governance_completeness', '')}"
        ),
        "data_availability_note": (
            history.get("status_message", "No historical audit archive connected.")
        ),
        "key_findings": key_findings,
        "assumptions": assumptions,
        "audit_recommendations": audit_recommendations,
        "outstanding_risks": outstanding,
        "confidence_note": confidence_note,
    }
