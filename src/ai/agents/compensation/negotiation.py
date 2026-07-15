"""Negotiation intelligence (Module 6).

Estimates offer-acceptance likelihood, negotiation probability, likely
objections, a negotiation strategy, a fallback and executive/recruiter talking
points. It cleanly separates **observed evidence** (the candidate's stated
expectation, historical acceptance rate, notice period, mobility) from the
**recommended** strategy (Module 6 / 16). All observed evidence traces to the
candidate record; no behavioural data is fabricated.
"""

from __future__ import annotations

from typing import Any, Dict, List

from src.ai.agents.compensation.schemas import CompensationRange, NegotiationIntelligence


def _num(source: Dict[str, Any], key: str, default: float = 0.0) -> float:
    try:
        return float(source.get(key, default))
    except (TypeError, ValueError):
        return default


def build_negotiation(evidence: Dict[str, Any], band: CompensationRange) -> NegotiationIntelligence:
    """Build the negotiation intelligence for the recommendation (Module 6)."""
    comp = evidence.get("candidate_comp") or {}
    exp_min = _num(comp, "expected_min")
    exp_max = _num(comp, "expected_max")
    acceptance_rate = _num(comp, "offer_acceptance_rate")  # 0..1
    notice = _num(comp, "notice_period_days")
    open_to_work = bool(comp.get("open_to_work"))
    relocate = bool(comp.get("willing_to_relocate"))

    observed: List[str] = []
    if exp_max > 0:
        observed.append(f"Stated expectation {band.currency} {exp_min:.1f}-{exp_max:.1f} {band.unit}.")
    if acceptance_rate:
        observed.append(f"Historical offer-acceptance rate {acceptance_rate * 100:.0f}% (platform signal).")
    if notice:
        observed.append(f"Notice period {notice:.0f} days.")
    observed.append(f"Open to work: {'yes' if open_to_work else 'unknown'}; willing to relocate: {'yes' if relocate else 'no'}.")

    # Acceptance likelihood: target vs. expectation + historical acceptance.
    expected_mid = (exp_min + exp_max) / 2.0 if exp_max > 0 else 0.0
    meets_expectation = expected_mid == 0.0 or band.target >= expected_mid
    if meets_expectation and acceptance_rate >= 0.7:
        acceptance = "High"
    elif meets_expectation or acceptance_rate >= 0.5:
        acceptance = "Moderate"
    else:
        acceptance = "Low"

    # Negotiation probability: below expectation or high notice -> more likely.
    if expected_mid and band.target < expected_mid:
        negotiation_prob = "High"
    elif open_to_work and meets_expectation:
        negotiation_prob = "Low"
    else:
        negotiation_prob = "Moderate"

    objections: List[str] = []
    if expected_mid and band.target < expected_mid:
        objections.append("Target is below the candidate's stated expectation.")
    if notice >= 60:
        objections.append("Long notice period may delay start / prompt a sign-on ask.")
    objections.append("Competing offers or counter from the current employer.")

    strategy = [
        f"Open at the target ({band.target:.1f} {band.unit}); keep the band maximum ({band.maximum:.1f}) as headroom.",
        "Lead with the evidence-based justification, not just the number.",
        "Address the top objection proactively.",
    ]
    fallback = [
        f"If pushed, move toward {band.maximum:.1f} {band.unit} only with the documented justification.",
        "Trade non-cash levers (sign-on, start date, remote flexibility) before exceeding the band.",
        "If the ask exceeds the band, escalate for executive approval rather than improvising.",
    ]
    exec_notes = [
        f"Recommended band: {band.formatted()} ({band.confidence_label} confidence).",
        "Any offer above the band requires documented executive sponsorship (see audit trail).",
    ]
    talking_points = [
        "This range synthesizes the candidate's assessed value across our intelligence engines.",
        "It is a defensible range, not a fixed number — we have room to reach a fair close.",
        "Comp is one lever; role scope, growth and team are part of the package.",
    ]

    confidence = 50.0 + (15.0 if exp_max > 0 else 0.0) + (15.0 if acceptance_rate else 0.0)
    confidence = min(100.0, confidence)

    return NegotiationIntelligence(
        acceptance_likelihood=acceptance,
        negotiation_probability=negotiation_prob,
        confidence=round(confidence, 1),
        observed_evidence=observed,
        likely_objections=objections,
        strategy=strategy,
        fallback_strategy=fallback,
        executive_approval_notes=exec_notes,
        recruiter_talking_points=talking_points,
    )
