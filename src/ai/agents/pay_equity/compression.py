"""Salary compression detection (Module 2).

Compression = a new hire landing at or above the compensation of *existing*
employees who have more tenure (or a higher level) in an equivalent role. This is
only evaluable when internal compensation data is supplied through the injected
provider. **Without it, no payroll is fabricated** — the assessment reports
"Company compensation data unavailable." (Module 14).
"""

from __future__ import annotations

from typing import Any

from src.ai.agents.pay_equity.schemas import CompressionAssessment


def _peers(context: dict[str, Any], provider: Any) -> list[dict[str, Any]]:
    """Return the peer records from the provider (empty when unavailable)."""
    if provider is None or not getattr(provider, "is_available", lambda: False)():
        return []
    peers = provider.get_peers(
        context.get("role", ""), context.get("level", ""), context.get("department", "")
    )
    return list(peers or [])


def assess_compression(context: dict[str, Any], provider: Any) -> CompressionAssessment:
    """Assess salary-compression risk for the offer (Module 2)."""
    peers = _peers(context, provider)
    if not peers:
        return CompressionAssessment(
            risk_level="Unavailable",
            data_available=False,
            rationale="Company compensation data unavailable.",
            business_impact="",
            mitigation="Connect an HRIS / payroll source to enable compression detection.",
            evidence=[],
        )

    target = float(context.get("offer", {}).get("target", 0.0))
    unit = context.get("offer", {}).get("unit", "LPA")

    # A peer is "compressed" if they have more tenure but comp <= the new offer.
    compressed: list[dict[str, Any]] = []
    for peer in peers:
        comp = float(peer.get("compensation", 0.0) or 0.0)
        tenure = float(peer.get("tenure_years", 0.0) or 0.0)
        if comp and comp <= target and tenure >= 1.0:
            compressed.append(peer)

    ratio = len(compressed) / len(peers) if peers else 0.0
    if ratio >= 0.5:
        level = "High"
    elif ratio >= 0.2:
        level = "Medium"
    else:
        level = "Low"

    evidence = [
        f"{len(compressed)} of {len(peers)} peers earn at or below the offer target "
        f"({target:.1f} {unit}) despite >= 1 year tenure."
    ]
    for peer in compressed[:3]:
        evidence.append(
            f"Peer {peer.get('employee_id', peer.get('peer_ref', '?'))}: "
            f"{float(peer.get('compensation', 0)):.1f} {unit}, tenure {float(peer.get('tenure_years', 0)):.1f}y."
        )

    business_impact = (
        "Compression can demotivate tenured staff and raise attrition/back-fill cost "
        "if it surfaces in pay reviews."
        if level != "Low"
        else "Limited compression signal; monitor at the next pay review."
    )
    mitigation = (
        "Consider anchoring nearer the band minimum, or plan proactive adjustments for "
        "the affected peers; route to HR compensation for review."
        if level != "Low"
        else "No adjustment indicated now; document the comparison in the offer file."
    )

    return CompressionAssessment(
        risk_level=level,
        data_available=True,
        rationale=f"{len(compressed)}/{len(peers)} peers fall at or below the offer target with more tenure.",
        business_impact=business_impact,
        mitigation=mitigation,
        evidence=evidence,
    )
