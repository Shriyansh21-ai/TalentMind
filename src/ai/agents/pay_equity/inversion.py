"""Pay inversion analysis (Module 3).

Inversion = a new hire whose offer exceeds the compensation of an *existing*
employee with **equivalent or greater responsibility**. Detectable only with
internal data; otherwise the assessment states "Unable to evaluate without
internal compensation data." — no payroll is fabricated (Module 14).
"""

from __future__ import annotations

from typing import Any

from src.ai.agents.pay_equity.schemas import InversionAssessment, InversionCase

# Responsibility ordering used to compare "equivalent or greater" responsibility.
_RESP_ORDER = {
    "junior": 1,
    "mid": 2,
    "senior": 3,
    "staff": 4,
    "principal": 5,
    "lead": 4,
    "manager": 4,
}


def _resp_rank(value: str) -> int:
    return _RESP_ORDER.get(str(value or "").strip().lower(), 2)


def _peers(context: dict[str, Any], provider: Any) -> list[dict[str, Any]]:
    if provider is None or not getattr(provider, "is_available", lambda: False)():
        return []
    peers = provider.get_peers(
        context.get("role", ""), context.get("level", ""), context.get("department", "")
    )
    return list(peers or [])


def assess_inversion(context: dict[str, Any], provider: Any) -> InversionAssessment:
    """Assess pay-inversion risk for the offer (Module 3)."""
    peers = _peers(context, provider)
    if not peers:
        return InversionAssessment(
            risk_level="Unavailable",
            data_available=False,
            rationale="Unable to evaluate without internal compensation data.",
        )

    target = float(context.get("offer", {}).get("target", 0.0))
    unit = context.get("offer", {}).get("unit", "LPA")
    offer_resp = _resp_rank(context.get("level", "mid"))

    cases: list[InversionCase] = []
    for peer in peers:
        comp = float(peer.get("compensation", 0.0) or 0.0)
        peer_resp = _resp_rank(peer.get("responsibility", peer.get("level", "")))
        # Inversion: peer has equal-or-greater responsibility but earns less than the offer.
        if comp and peer_resp >= offer_resp and comp < target:
            cases.append(
                InversionCase(
                    peer_ref=str(peer.get("employee_id", peer.get("peer_ref", "peer"))),
                    detail=(
                        f"Earns {comp:.1f} {unit} at equivalent-or-greater responsibility "
                        f"vs. the offer target {target:.1f} {unit}."
                    ),
                )
            )

    if not cases:
        level = "Low"
        rationale = (
            "No existing peer with equivalent-or-greater responsibility earns below the offer."
        )
    elif len(cases) >= 3:
        level = "High"
        rationale = (
            f"{len(cases)} peers with equivalent-or-greater responsibility earn below the offer."
        )
    else:
        level = "Medium"
        rationale = (
            f"{len(cases)} peer(s) with equivalent-or-greater responsibility earn below the offer."
        )

    return InversionAssessment(
        risk_level=level,
        data_available=True,
        rationale=rationale,
        cases=cases[:5],
        business_impact=(
            "Inversion is a common trigger for pay-equity grievances and can force reactive "
            "peer adjustments."
            if cases
            else "No inversion signal detected."
        ),
        recommended_review=(
            "Route to HR compensation to review the affected peers before extending the offer."
            if cases
            else "No review required on inversion grounds."
        ),
    )
