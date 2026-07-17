"""Reasoning explainability (Module 3).

Organizes the decision's reasoning into the mandated registers — Observed Facts,
Derived Insights, Business Reasoning, Assumptions, Human Decisions and AI
Decisions — each referencing the evidence it rests on. Every entry is derived from
the reused compliance/governance signals; nothing is invented (Module 14).
"""

from __future__ import annotations

from typing import Any

from src.ai.agents.audit.schemas import ReasoningExplanation
from src.ai.agents.audit.templates import CATALOG_BY_SOURCE


def build_reasoning(context: dict[str, Any]) -> ReasoningExplanation:
    """Build the register-by-register reasoning explanation (Module 3)."""
    sources = list(context.get("evidence_sources", []))
    governance_risk = context.get("governance_risk", {}) or {}
    workflow = context.get("workflow", {}) or {}
    approvals = context.get("approvals", {}) or {}
    review = context.get("review", {}) or {}
    data_available = bool(context.get("data_available"))

    observed_facts = [
        f"{CATALOG_BY_SOURCE[s].origin_agent} produced {CATALOG_BY_SOURCE[s].evidence_type.lower()}."
        for s in sources
        if s in CATALOG_BY_SOURCE
    ]

    derived_insights = [
        f"Workflow status is {workflow.get('status', 'Requires Review')} "
        f"({workflow.get('completed', 0)}/{workflow.get('total', 0)} steps).",
        f"Governance risk is {governance_risk.get('level', 'Medium')}.",
    ]
    if context.get("equity_risk_level") and context["equity_risk_level"] != "Unknown":
        derived_insights.append(f"Internal pay-equity risk is {context['equity_risk_level']}.")

    business_reasoning = list(governance_risk.get("drivers", []))[:4] or [
        "No governance risk drivers surfaced from the available evidence."
    ]

    assumptions = [
        "This reconstruction reflects only the evidence on record; it neither adds nor rewrites history."
    ]
    if not data_available:
        assumptions.append(
            "No governance/approval system connected — human approvals and audit history are "
            "unverified and treated as pending."
        )

    # Human vs AI is kept strictly separate (Module 5 principle applied here too).
    human_decisions: list[str] = []
    for a in approvals.get("approvals", []):
        if a.get("required") and a.get("state") == "Complete":
            human_decisions.append(f"{a['approver']} approved (human decision).")
    if not human_decisions:
        human_decisions.append("No human approvals are verified on record (pending review).")

    ai_decisions: list[str] = []
    if "AI Hiring Committee" in sources:
        ai_decisions.append(
            "The AI Hiring Committee produced a consensus recommendation (AI decision)."
        )
    if "Compensation Governance Agent" in sources:
        ai_decisions.append(
            "Compensation Governance recommended a defensible range (AI recommendation)."
        )
    if "Pay Equity Guardian" in sources:
        ai_decisions.append("The Pay Equity Guardian assessed internal fairness (AI assessment).")
    if "Hiring Compliance" in sources:
        ai_decisions.append("Hiring Compliance evaluated governance adherence (AI assessment).")
    if review.get("rationale"):
        ai_decisions.append(f"Compliance review routing: {review['rationale']}")
    if not ai_decisions:
        ai_decisions.append("No AI decisions were evidenced.")

    return ReasoningExplanation(
        observed_facts=observed_facts or ["No upstream agent evidence was recorded."],
        derived_insights=derived_insights,
        business_reasoning=business_reasoning,
        assumptions=assumptions,
        human_decisions=human_decisions,
        ai_decisions=ai_decisions,
    )
