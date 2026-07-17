"""Team hiring analytics (Module 3).

Aggregates hiring health by the dimensions derivable from the cohort's own
profiles — **Role Family** and **Location** (Observed). Department / Business Unit
/ Hiring Manager / Recruiter require an org-structure source and are reported
**Unavailable** unless an analytics provider is connected. Only produces a group
when data exists (Module 3 / 15).
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from src.ai.agents.hiring_intelligence.analytics_engine import hiring_health_label, is_positive
from src.ai.agents.hiring_intelligence.schemas import TeamMetric

# Dimensions that need an org-structure source (Unavailable without a provider).
_PROVIDER_DIMENSIONS = ["Department", "Business Unit", "Hiring Manager", "Recruiter"]


def _group_health(dimension: str, cohort: list[dict[str, Any]], key: str) -> list[TeamMetric]:
    """Aggregate hiring health per group value for a cohort-derivable dimension."""
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for s in cohort:
        groups[str(s.get(key, "Unknown"))].append(s)

    metrics: list[TeamMetric] = []
    for group, members in sorted(groups.items()):
        hire_share = sum(1 for m in members if is_positive(m["recommendation"])) / len(members)
        high_risk = sum(1 for m in members if m["risk_level"] == "High") / len(members)
        metrics.append(
            TeamMetric(
                dimension=dimension,
                group=group,
                count=len(members),
                hiring_health=hiring_health_label(hire_share, high_risk),
                register="Observed",
                detail=f"{hire_share * 100:.0f}% positive, {high_risk * 100:.0f}% high-risk ({len(members)} candidate(s)).",
            )
        )
    return metrics


def build_team_metrics(
    cohort: list[dict[str, Any]], provider: Any, data_available: bool
) -> list[TeamMetric]:
    """Aggregate team hiring analytics (Module 3)."""
    metrics: list[TeamMetric] = []
    metrics.extend(_group_health("Role Family", cohort, "role_family"))
    metrics.extend(_group_health("Location", cohort, "location"))

    if data_available and provider is not None and hasattr(provider, "get_team_metrics"):
        for row in provider.get_team_metrics() or []:
            metrics.append(
                TeamMetric(
                    dimension=row.get("dimension", "Team"),
                    group=row.get("group", "?"),
                    count=int(row.get("count", 0)),
                    hiring_health=row.get("hiring_health", "n/a"),
                    register="Observed",
                    detail=row.get("detail", "From the connected analytics source."),
                )
            )
    else:
        for dim in _PROVIDER_DIMENSIONS:
            metrics.append(
                TeamMetric(
                    dimension=dim,
                    group="(all)",
                    count=0,
                    hiring_health="Unavailable",
                    register="Unavailable",
                    detail="Requires a connected org-structure / analytics source.",
                )
            )
    return metrics
