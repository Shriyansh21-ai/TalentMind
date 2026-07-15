"""Deterministic composer for the PayEquityNarrative (offline reasoning).

Maps the aggregated evidence dict to a :class:`PayEquityNarrative`-shaped dict by
**restating and organizing** the computed equity signals — never inventing
payroll, protected characteristics or legal findings, and never accusing
discrimination (Module 14). This lets the guardian run fully offline with a
structural no-fabrication guarantee.

The same evidence is embedded in the prompt for real providers, so online and
offline modes agree on the facts.
"""

from __future__ import annotations

from typing import Any, Dict, List


def compose_pay_equity_narrative(evidence: Dict[str, Any]) -> Dict[str, Any]:
    """Deterministically compose a :class:`PayEquityNarrative` from evidence."""
    data_available = bool(evidence.get("data_available"))
    offer = evidence.get("offer_summary") or {}
    ov = evidence.get("candidate_overview") or {}
    title = ov.get("title") or "the candidate"

    compression = evidence.get("compression") or {}
    inversion = evidence.get("inversion") or {}
    promotion = evidence.get("promotion") or {}
    policy = evidence.get("policy_alignment") or {}
    fairness = evidence.get("fairness") or {}
    review = evidence.get("executive_review") or {}
    equity_risk = evidence.get("equity_risk") or {}

    offer_str = offer.get("recommended_range") or (
        f"{offer.get('currency', 'INR')} target {offer.get('target', 0)} {offer.get('unit', 'LPA')}"
    )

    if data_available:
        summary = (
            f"Internal pay-equity review for the offer to {title} ({offer_str}). "
            f"Overall equity risk is {equity_risk.get('level', 'Unknown')}; "
            f"compression {compression.get('risk_level', 'n/a')}, inversion "
            f"{inversion.get('risk_level', 'n/a')}. This is a governance assessment for "
            "human review, not a legal finding."
        )
        data_note = "Internal compensation data was connected; internal comparisons were evaluated."
    else:
        summary = (
            f"Internal pay-equity review for the offer to {title} ({offer_str}). "
            "No company compensation data is connected, so internal comparisons "
            "(compression, inversion, band consistency) could not be evaluated. The "
            "assessment is provisional and routes the standard governance approvals."
        )
        data_note = (
            "Company compensation data unavailable. Compression and inversion are "
            "'Unable to evaluate without internal compensation data.'"
        )

    key_findings: List[str] = []
    if data_available:
        if compression.get("risk_level") in ("Medium", "High"):
            key_findings.append(f"Compression risk: {compression.get('risk_level')} — {compression.get('rationale', '')}")
        if inversion.get("risk_level") in ("Medium", "High"):
            key_findings.append(f"Inversion risk: {inversion.get('risk_level')} — {inversion.get('rationale', '')}")
    if policy.get("alignment") in ("Partial", "Violation"):
        key_findings.append(f"Policy '{policy.get('policy_name')}' alignment: {policy.get('alignment')}.")
    if not key_findings:
        key_findings.append("No material equity concerns surfaced from the available information.")

    review_recs = list(fairness.get("human_review_recommendations", []))[:5]
    assumptions = list(fairness.get("assumptions", []))[:5]

    risk_level = equity_risk.get("level", "Unknown")
    if risk_level == "High":
        confidence_note = "Elevated equity risk on connected data — treat the human-review recommendations as required."
    elif not data_available:
        confidence_note = "Confidence is limited: internal data is unavailable, so internal fairness is unverified."
    else:
        confidence_note = "Confidence is moderate: findings rest on the connected peer data and existing intelligence."

    return {
        "executive_summary": summary,
        "equity_assessment": fairness.get("assessment", "Internal-equity findings summarized above."),
        "compression_note": compression.get("rationale", "Company compensation data unavailable."),
        "inversion_note": inversion.get("rationale", "Unable to evaluate without internal compensation data."),
        "promotion_note": promotion.get("progression_note", "") + " " + promotion.get("level_alignment", ""),
        "policy_note": policy.get("rationale", "Policy alignment not evaluated."),
        "fairness_note": (
            "Concerns for review: " + "; ".join(fairness.get("concerns", []))
            if fairness.get("concerns") else "No material fairness concerns surfaced."
        ) + " (Governance review only — no legal conclusion, no discrimination finding.)",
        "review_note": review.get("rationale", "Standard governance approvals apply."),
        "data_availability_note": data_note,
        "key_findings": key_findings,
        "assumptions": assumptions,
        "human_review_recommendations": review_recs or ["No human review beyond standard approvals."],
        "confidence_note": confidence_note,
    }
