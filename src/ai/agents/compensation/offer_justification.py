"""Offer justification + transparency audit trail (Modules 2, 12).

* :func:`build_justification` — the Module 2 audit trail of *why* the
  recommendation exists: every entry is tagged Evidence / Reasoning / Business
  Impact / Assumption and cites its source (Module 16).
* :func:`build_audit_trail` — the Module 12 **flagship** transparency record:
  decision id, timestamp, evidence sources, agents consulted, ordered reasoning
  chain, confidence, required approvals, business justification and human-review
  status. Exportable via :meth:`AuditTrail.to_export_text`.
"""

from __future__ import annotations

from typing import Any, Dict, List

from src.ai.agents.compensation.schemas import (
    AuditTrail,
    BudgetAssessment,
    CompensationRange,
    JustificationEntry,
    MarketPosition,
    NegotiationIntelligence,
)
from src.ai.agents.compensation.templates import APPROVAL_POLICY


def build_justification(
    evidence: Dict[str, Any],
    band: CompensationRange,
    market: MarketPosition,
    budget: BudgetAssessment,
    negotiation: NegotiationIntelligence,
) -> List[JustificationEntry]:
    """Build the transparent offer-justification trail (Module 2)."""
    entries: List[JustificationEntry] = []

    # Evidence — the candidate's own stated expectation + engine signals.
    comp = evidence.get("candidate_comp") or {}
    if float(comp.get("expected_max", 0) or 0) > 0:
        entries.append(
            JustificationEntry(
                kind="Evidence",
                statement=(
                    f"Candidate stated expectation {band.currency} "
                    f"{comp.get('expected_min', 0):.1f}-{comp.get('expected_max', 0):.1f} {band.unit}."
                ),
                source="Candidate record",
                confidence=90.0,
            )
        )
    intelligence = evidence.get("intelligence") or {}
    if intelligence.get("strengths"):
        entries.append(
            JustificationEntry(
                kind="Evidence",
                statement="Assessed strengths: " + "; ".join(intelligence["strengths"][:3]) + ".",
                source="Candidate Intelligence engine",
                confidence=float(intelligence.get("confidence", 60.0) or 60.0),
            )
        )
    committee = evidence.get("committee") or {}
    stance = (committee.get("consensus") or {}).get("recommendation")
    if stance:
        entries.append(
            JustificationEntry(
                kind="Evidence",
                statement=f"Hiring decision stance: {stance}.",
                source="AI Hiring Committee",
                confidence=float((committee.get("confidence") or {}).get("overall", 60.0) or 60.0),
            )
        )

    # Reasoning — how the band was derived (the pay-band basis).
    for reason in band.basis:
        entries.append(
            JustificationEntry(kind="Reasoning", statement=reason, source="Internal heuristic model", confidence=band.confidence)
        )

    # Business Impact — market position + budget rationale.
    entries.append(
        JustificationEntry(
            kind="Business Impact",
            statement=f"Market position: {market.position}. {budget.investment_rationale}",
            source="Compensation Governance",
            confidence=budget.confidence,
        )
    )
    entries.append(
        JustificationEntry(
            kind="Business Impact",
            statement=(
                f"Offer-acceptance likelihood {negotiation.acceptance_likelihood}; "
                f"negotiation probability {negotiation.negotiation_probability}."
            ),
            source="Negotiation Intelligence",
            confidence=negotiation.confidence,
        )
    )

    # Assumptions — everything not grounded in the evidence.
    for assumption in band.assumptions:
        entries.append(
            JustificationEntry(kind="Assumption", statement=assumption, source="Internal heuristic model", confidence=0.0)
        )

    return entries


def _agents_consulted(evidence: Dict[str, Any]) -> List[str]:
    """Return the AI agents / engines actually consulted for this decision."""
    mapping = [
        ("resume", "Resume Analyst Agent"),
        ("jd", "JD Analyst Agent"),
        ("intelligence", "Candidate Intelligence engine"),
        ("timeline", "Career Timeline Intelligence"),
        ("risk", "Resume Risk Detection"),
        ("recommendation", "Hiring Recommendation engine"),
        ("interview", "Interview Intelligence"),
        ("committee", "AI Hiring Committee"),
    ]
    return [label for key, label in mapping if evidence.get(key)]


def _approvals_required(budget: BudgetAssessment, equity_available: bool) -> List[str]:
    """Return the approvers this decision requires (Module 12)."""
    approvals = list(APPROVAL_POLICY["base"])
    if budget.hire_type == "Critical Hire":
        approvals = list(APPROVAL_POLICY["critical_hire"])
    if equity_available:
        for a in APPROVAL_POLICY["equity_review"]:
            if a not in approvals:
                approvals.append(a)
    return approvals


def build_audit_trail(
    evidence: Dict[str, Any],
    band: CompensationRange,
    market: MarketPosition,
    budget: BudgetAssessment,
    *,
    decision_id: str,
    decision_timestamp: str,
    equity_available: bool,
) -> AuditTrail:
    """Build the flagship transparency audit trail (Module 12)."""
    reasoning_chain = [
        "Gathered existing structured intelligence (no engine re-run).",
        f"Anchored the band on {'the candidate stated expectation' if float((evidence.get('candidate_comp') or {}).get('expected_max', 0) or 0) > 0 else 'a seniority baseline (assumption)'}.",
        "Applied internal heuristic premiums/discounts (skill, leadership, strategic, risk).",
        f"Derived the recommended range: {band.formatted()}.",
        f"Assessed market position as {market.position} (internal heuristic model, no external survey).",
        f"Classified the hire as {budget.hire_type} and set required approvals.",
        "Generated the offer justification, negotiation strategy and this audit trail.",
    ]
    business_justification = budget.business_justification or budget.investment_rationale

    return AuditTrail(
        decision_id=decision_id,
        decision_timestamp=decision_timestamp,
        evidence_sources=_agents_consulted(evidence),
        agents_consulted=_agents_consulted(evidence) + ["Compensation Governance Agent"],
        reasoning_chain=reasoning_chain,
        confidence=band.confidence,
        confidence_label=band.confidence_label,
        approvals_required=_approvals_required(budget, equity_available),
        business_justification=business_justification,
        human_review_status="Pending Human Review",
    )
