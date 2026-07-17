"""Pipeline intelligence (Module 2).

Identifies pipeline bottlenecks. Stage/approval/interview/offer/compliance *timing*
is not persisted by the platform, so delay-based bottlenecks are reported
**Unavailable** unless an analytics provider is connected. Two bottlenecks are
**Estimated** from the cohort's own signals (a high-risk share implies a
risk-validation bottleneck; a low interview-ready share implies an
interview-planning bottleneck). Nothing is fabricated (Module 15).
"""

from __future__ import annotations

from typing import Any

from src.ai.agents.hiring_intelligence.analytics_engine import share
from src.ai.agents.hiring_intelligence.schemas import Bottleneck

# Delay-based stages that require timing data (Unavailable without a provider).
_TIMED_STAGES = [
    ("Screening delay", "Time from application to screen"),
    ("Approval delay", "Time awaiting required approvals"),
    ("Offer delay", "Time from decision to offer"),
    ("Compliance delay", "Time in compliance review"),
]


def build_bottlenecks(
    cohort: list[dict[str, Any]], provider: Any, data_available: bool
) -> list[Bottleneck]:
    """Identify pipeline bottlenecks (Module 2)."""
    bottlenecks: list[Bottleneck] = []
    high_risk_share = share(cohort, lambda s: s["risk_level"] == "High")
    not_ready_share = share(cohort, lambda s: not s.get("interview_ready"))

    # Estimated bottlenecks — derivable from the cohort intelligence.
    if high_risk_share >= 0.3:
        bottlenecks.append(
            Bottleneck(
                stage="Risk validation",
                severity="High" if high_risk_share >= 0.5 else "Medium",
                observed=False,
                potential_cause=f"{high_risk_share * 100:.0f}% of the cohort is high-risk, requiring extra validation.",
                business_impact="Longer interview loops and more bar-raiser / escalation cycles.",
                improvement="Front-load risk-validation questions and tighten sourcing filters.",
                register="Estimated",
            )
        )
    if not_ready_share >= 0.5:
        bottlenecks.append(
            Bottleneck(
                stage="Interview planning",
                severity="Medium",
                observed=False,
                potential_cause=f"{not_ready_share * 100:.0f}% of the cohort lacks a structured interview signal.",
                business_impact="Ad-hoc interviews reduce comparability and slow debriefs.",
                improvement="Standardize interview planning via the Interview Studio.",
                register="Estimated",
            )
        )

    # Timing-based stages — Unavailable without connected data.
    provider_stages = {}
    if data_available and provider is not None and hasattr(provider, "get_trends"):
        provider_stages = (provider.get_trends() or {}).get("bottlenecks", {})
    for stage, desc in _TIMED_STAGES:
        if stage in provider_stages:
            info = provider_stages[stage]
            bottlenecks.append(
                Bottleneck(
                    stage=stage,
                    severity=info.get("severity", "Medium"),
                    observed=True,
                    potential_cause=info.get("cause", desc),
                    business_impact=info.get("impact", ""),
                    improvement=info.get("improvement", ""),
                    register="Observed",
                )
            )
        else:
            bottlenecks.append(
                Bottleneck(
                    stage=stage,
                    severity="Unknown",
                    observed=False,
                    potential_cause=f"{desc} — no stage-timing data connected.",
                    business_impact="",
                    improvement="Connect an analytics source to measure this delay.",
                    register="Unavailable",
                )
            )
    return bottlenecks
