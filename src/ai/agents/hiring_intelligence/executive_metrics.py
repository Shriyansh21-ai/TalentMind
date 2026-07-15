"""Executive KPI intelligence (Module 5).

Builds the evidence-backed executive KPIs. Cohort-derivable KPIs (hiring health,
interview readiness, strategic readiness) are computed from the analyzed cohort's
intelligence and marked **Observed**; governance / transparency / compliance /
audit readiness need org-wide governance data and are marked **Unavailable** (with
a null value) unless an analytics provider is connected. Never fabricates numbers
(Module 15).
"""

from __future__ import annotations

from typing import Any, Dict, List

from src.ai.agents.hiring_intelligence.analytics_engine import (
    hiring_health_label,
    is_positive,
    share,
)
from src.ai.agents.hiring_intelligence.schemas import KPI
from src.ai.agents.hiring_intelligence.templates import KPI_DEFS


def _band(value: float) -> str:
    if value >= 65:
        return "High"
    if value >= 40:
        return "Medium"
    return "Low"


def build_kpis(cohort: List[Dict[str, Any]], provider: Any, data_available: bool) -> List[KPI]:
    """Build the executive KPIs (Module 5)."""
    total = len(cohort)
    hire_share = share(cohort, lambda s: is_positive(s["recommendation"]))
    high_risk_share = share(cohort, lambda s: s["risk_level"] == "High")
    interview_share = share(cohort, lambda s: s.get("interview_ready"))
    strategic_share = share(cohort, lambda s: s["overall"] >= 70 or "strong" in s["recommendation"].lower())
    confidence = min(100.0, 45.0 + total * 3.0)

    provider_kpis: Dict[str, Any] = {}
    if data_available and provider is not None:
        # A connected analytics source may supply the governance-family KPIs.
        provider_kpis = (provider.get_trends() or {}).get("kpis", {}) if hasattr(provider, "get_trends") else {}

    kpis: List[KPI] = []
    for definition in KPI_DEFS:
        if definition.key == "hiring_health":
            value = max(0.0, min(100.0, hire_share * 100.0 - high_risk_share * 50.0))
            kpis.append(KPI(name=definition.name, value=value, label=hiring_health_label(hire_share, high_risk_share),
                            register="Observed", confidence=confidence,
                            basis=f"{hire_share*100:.0f}% positive recommendations, {high_risk_share*100:.0f}% high-risk across {total} candidates."))
        elif definition.key == "interview_readiness":
            value = interview_share * 100.0
            kpis.append(KPI(name=definition.name, value=value, label=_band(value), register="Observed",
                            confidence=confidence, basis=f"{interview_share*100:.0f}% of the cohort has a structured interview signal."))
        elif definition.key == "strategic_readiness":
            value = strategic_share * 100.0
            kpis.append(KPI(name=definition.name, value=value, label=_band(value), register="Observed",
                            confidence=confidence, basis=f"{strategic_share*100:.0f}% strong-hire / high-capability candidates."))
        elif definition.key in provider_kpis:
            v = float(provider_kpis[definition.key])
            kpis.append(KPI(name=definition.name, value=v, label=_band(v), register="Observed",
                            confidence=70.0, basis="From the connected analytics source."))
        else:
            kpis.append(KPI(name=definition.name, value=None, label="Unavailable", register="Unavailable",
                            confidence=0.0, basis="Requires connected governance/analytics data (Module 13)."))
    return kpis
