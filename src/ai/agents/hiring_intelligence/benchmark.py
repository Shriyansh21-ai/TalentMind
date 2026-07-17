"""Benchmark intelligence (Module 8).

Compares groups **using available internal cohort data only** — role families and
locations — on observed hiring health. It **never compares against external market
data** (Module 8). When a dimension has fewer than two groups, it says so rather
than inventing a comparison (Module 15).
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from src.ai.agents.hiring_intelligence.analytics_engine import hiring_health_label, is_positive
from src.ai.agents.hiring_intelligence.schemas import Benchmark


def _compare(dimension: str, cohort: list[dict[str, Any]], key: str) -> Benchmark:
    """Compare groups on observed hiring health for a cohort dimension."""
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for s in cohort:
        groups[str(s.get(key, "Unknown"))].append(s)

    comparisons: list[dict[str, Any]] = []
    for group, members in sorted(groups.items()):
        hire_share = sum(1 for m in members if is_positive(m["recommendation"])) / len(members)
        high_risk = sum(1 for m in members if m["risk_level"] == "High") / len(members)
        avg_overall = sum(m["overall"] for m in members) / len(members)
        comparisons.append(
            {
                "group": group,
                "count": len(members),
                "hiring_health": hiring_health_label(hire_share, high_risk),
                "avg_capability": round(avg_overall, 1),
                "positive_share": round(hire_share * 100, 1),
            }
        )

    note = (
        "" if len(comparisons) >= 2 else "Insufficient groups for a meaningful internal comparison."
    )
    return Benchmark(dimension=dimension, comparisons=comparisons, register="Observed", note=note)


def build_benchmarks(cohort: list[dict[str, Any]], data_available: bool) -> list[Benchmark]:
    """Build internal benchmark comparisons (Module 8)."""
    return [
        _compare("Role Family", cohort, "role_family"),
        _compare("Location", cohort, "location"),
    ]
