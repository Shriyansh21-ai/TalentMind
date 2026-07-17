"""Deterministic composer for the CompensationNarrative (offline reasoning).

Maps the aggregated evidence dict to a :class:`CompensationNarrative`-shaped dict
by **restating and organizing** the existing intelligence and the engine's own
heuristic range — never inventing a salary survey, payroll figure or market
benchmark (Module 16). This is what lets the governance agent run fully offline
with a structural no-fabrication guarantee: the narrative is a pure function of
the deterministic inputs.

The same evidence is embedded in the prompt for real providers, so online and
offline modes agree on the facts.
"""

from __future__ import annotations

from typing import Any


def _overview_line(evidence: dict[str, Any]) -> str:
    ov = evidence.get("candidate_overview") or {}
    title = ov.get("title") or "the candidate"
    years = ov.get("years_of_experience")
    line = title
    if isinstance(years, (int, float)) and years:
        line += f" with {years:.0f} years of experience"
    return line


def _range_str(evidence: dict[str, Any]) -> str:
    rr = evidence.get("recommended_range") or {}
    if not rr:
        return "a defensible range (pending computation)"
    return (
        f"{rr.get('currency', 'INR')} {rr.get('minimum', 0):.1f}-{rr.get('maximum', 0):.1f} "
        f"{rr.get('unit', 'LPA')} (target {rr.get('target', 0):.1f})"
    )


def compose_compensation_narrative(evidence: dict[str, Any]) -> dict[str, Any]:
    """Deterministically compose a :class:`CompensationNarrative` from evidence."""
    rr = evidence.get("recommended_range") or {}
    conf_label = rr.get("confidence_label", "Moderate")
    market = evidence.get("market_position") or "Market Competitive"
    hire_type = evidence.get("hire_type") or "Growth Hire"
    overview = _overview_line(evidence)
    range_str = _range_str(evidence)

    summary = (
        f"For {overview}, the internal heuristic model recommends {range_str}. "
        f"This is a defensible range — not a salary prediction — synthesized from "
        f"the candidate's stated expectation and TalentMind's existing intelligence. "
        f"Market position: {market}; classified as a {hire_type}."
    )

    justifications: list[str] = list(rr.get("basis", []))
    intelligence = evidence.get("intelligence") or {}
    for s in (intelligence.get("strengths") or [])[:2]:
        justifications.append(f"Assessed strength: {s} (Candidate Intelligence).")
    justifications = list(dict.fromkeys(justifications))[:6]

    assumptions: list[str] = list(rr.get("assumptions", []))
    if not evidence.get("committee"):
        assumptions.append(
            "No committee decision was available; stance inferred from the recommendation engine."
        )
    assumptions = list(dict.fromkeys(assumptions))[:5]

    comp = evidence.get("candidate_comp") or {}
    has_expectation = float(comp.get("expected_max", 0) or 0) > 0

    recommendation_rationale = (
        "The range anchors on "
        + (
            "the candidate's stated expectation"
            if has_expectation
            else "a seniority baseline (assumption)"
        )
        + " and applies documented internal premiums/discounts for skill, leadership, "
        "strategic value and risk. Every step is recorded in the offer-justification trail."
    )

    negotiation_note = (
        "Open at the target and hold the band maximum as headroom; separate the "
        "observed evidence (stated expectation, acceptance rate) from the recommended strategy."
    )
    budget_note = (
        f"Classified as a {hire_type}; the investment is defensible against the assessed "
        "value. Budget figures are qualitative estimates, not connected financial metrics."
    )
    equity_note = (
        "Internal equity validation unavailable — no payroll/HRIS source is connected. "
        "The design is ready for future HRIS integration."
    )
    future_note = (
        "Promotion readiness and compensation progression track the career-growth and "
        "learning signals; confidence is attached to each estimate."
    )
    transparency_note = (
        "A full transparency audit trail (decision id, evidence sources, agents consulted, "
        "reasoning chain, required approvals, human-review status) accompanies this "
        "recommendation and is exportable."
    )

    if conf_label == "High":
        confidence_note = "Confidence is high: the range rests on an observed expectation and broad evidence coverage."
    elif conf_label == "Low":
        confidence_note = "Confidence is low: evidence is thin — treat the range as provisional and validate before approval."
    else:
        confidence_note = (
            "Confidence is moderate: the range is defensible but partially assumption-based."
        )

    return {
        "executive_summary": summary,
        "recommendation_rationale": recommendation_rationale,
        "market_position_note": f"{market}. Recommendation based on internal heuristic model (no external salary survey).",
        "governance_note": (
            "Aligns with the transparency policy: a documented range, explicit premiums and "
            "a full audit trail. Every governance conclusion explains why."
        ),
        "negotiation_note": negotiation_note,
        "budget_note": budget_note,
        "internal_equity_note": equity_note,
        "future_outlook_note": future_note,
        "transparency_note": transparency_note,
        "key_justifications": justifications,
        "key_assumptions": assumptions,
        "confidence_note": confidence_note,
    }
