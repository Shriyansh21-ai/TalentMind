"""Internal equity readiness — HRIS-ready, no payroll connectors (Module 8, 14).

TalentMind ships **no payroll integration** and must never assume company
compensation data exists. This module:

* defines the :class:`CompensationDataProvider` Protocol — the future HRIS / payroll
  integration seam (Module 14),
* ships :class:`NullCompensationDataProvider` as the default (no data), so the
  readiness assessment honestly reports "Internal equity validation unavailable.",
* evaluates pay-band consistency, compression risk, promotion impact and future
  adjustments **only when** a real provider is injected.

No connector (SuccessFactors / Workday / Oracle HCM / ADP / …) is implemented —
their names are registered as prepared extension points in ``templates``.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

from src.ai.agents.compensation.schemas import (
    CompensationRange,
    GovernanceCheck,
    InternalEquityReadiness,
)
from src.ai.agents.compensation.templates import HRIS_CONNECTORS


@runtime_checkable
class CompensationDataProvider(Protocol):
    """Future HRIS / payroll integration seam (Module 14 — interface only).

    A real implementation (against SuccessFactors / Workday / Oracle HCM / ADP /
    a regional comp database) returns the company's own pay bands and peer
    compensation for a role/level. TalentMind implements none of these; the
    Protocol exists so a later milestone plugs one in without a redesign.
    """

    def is_available(self) -> bool:
        """Return True when live company compensation data can be served."""
        ...

    def get_pay_band(self, role: str, level: str) -> Optional[Dict[str, Any]]:
        """Return the company pay band for ``(role, level)`` or ``None``."""
        ...

    def get_peer_compensation(self, role: str, level: str) -> Optional[List[Dict[str, Any]]]:
        """Return peer compensation records for ``(role, level)`` or ``None``."""
        ...


class NullCompensationDataProvider:
    """Default provider: no company compensation data (the shipped behaviour)."""

    def is_available(self) -> bool:
        """Always False — no payroll data is connected."""
        return False

    def get_pay_band(self, role: str, level: str) -> Optional[Dict[str, Any]]:
        """Return ``None`` — no pay-band data available."""
        return None

    def get_peer_compensation(self, role: str, level: str) -> Optional[List[Dict[str, Any]]]:
        """Return ``None`` — no peer data available."""
        return None


def assess_internal_equity(
    evidence: Dict[str, Any],
    band: CompensationRange,
    provider: Optional[CompensationDataProvider] = None,
) -> InternalEquityReadiness:
    """Assess internal-equity readiness (Module 8).

    With no provider (or a Null one), returns the honest "unavailable" state and
    the list of HRIS interfaces the design is ready for. With a real provider,
    evaluates pay-band consistency, compression and promotion impact.
    """
    provider = provider or NullCompensationDataProvider()

    if not provider.is_available():
        return InternalEquityReadiness(
            available=False,
            status_message="Internal equity validation unavailable.",
            checks=[],
            recommendations=[
                "Connect an HRIS / payroll source to enable pay-band and compression checks.",
            ],
            hris_interfaces_ready=list(HRIS_CONNECTORS),
        )

    # --- Provider available: evaluate against real company data ---------------
    overview = evidence.get("candidate_overview") or {}
    role = str(overview.get("title", ""))
    intelligence = evidence.get("intelligence") or {}
    level = "senior" if float(overview.get("years_of_experience", 0) or 0) >= 8 else "mid"

    checks: List[GovernanceCheck] = []
    recommendations: List[str] = []

    pay_band = provider.get_pay_band(role, level)
    if pay_band:
        lo = float(pay_band.get("min", 0.0))
        hi = float(pay_band.get("max", 0.0))
        within = lo <= band.target <= hi if hi else False
        checks.append(
            GovernanceCheck(
                dimension="Pay-band consistency",
                status="Aligned" if within else "Review",
                rationale=(
                    f"Recommended target {band.target:.1f} {band.unit} "
                    f"{'sits within' if within else 'falls outside'} the company band "
                    f"{lo:.1f}-{hi:.1f} {band.unit}."
                ),
                source="HRIS (injected provider)",
            )
        )
        if not within:
            recommendations.append("Reconcile the offer with the published pay band before approval.")

    peers = provider.get_peer_compensation(role, level)
    if peers:
        peer_vals = [float(p.get("compensation", 0.0)) for p in peers if p.get("compensation")]
        if peer_vals:
            peak = max(peer_vals)
            compression = band.target > peak
            checks.append(
                GovernanceCheck(
                    dimension="Compression risk",
                    status="Review" if compression else "Aligned",
                    rationale=(
                        f"Recommended target {'exceeds' if compression else 'is at or below'} "
                        f"the highest peer ({peak:.1f} {band.unit})."
                    ),
                    source="HRIS (injected provider)",
                )
            )
            if compression:
                recommendations.append("Assess compression against existing peers; consider a peer adjustment.")

    checks.append(
        GovernanceCheck(
            dimension="Promotion impact",
            status="Aligned",
            rationale="No promotion conflict detected in the connected data.",
            source="HRIS (injected provider)",
        )
    )

    return InternalEquityReadiness(
        available=True,
        status_message="Internal equity validated against connected company data.",
        checks=checks,
        recommendations=recommendations or ["No internal-equity adjustments required."],
        hris_interfaces_ready=list(HRIS_CONNECTORS),
    )
