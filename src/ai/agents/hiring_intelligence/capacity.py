"""Hiring capacity intelligence (Module 6).

Estimates recruiter / interview / approval / committee / executive workload.
Actual workloads need requisition + headcount + calendar data the platform does
not hold, so each area is reported **Unavailable** (with a planning recommendation)
unless an analytics provider is connected. Never fabricates workload figures
(Module 15).
"""

from __future__ import annotations

from typing import Any

from src.ai.agents.hiring_intelligence.schemas import CapacityEstimate

_AREAS = [
    ("Recruiter workload", "requisition load per recruiter"),
    ("Interview workload", "interview hours per interviewer"),
    ("Approval workload", "approvals per approver"),
    ("Committee workload", "committee sessions per period"),
    ("Executive workload", "executive reviews per period"),
]


def build_capacity(
    cohort: list[dict[str, Any]], provider: Any, data_available: bool
) -> list[CapacityEstimate]:
    """Estimate hiring capacity (Module 6)."""
    provider_capacity: dict[str, Any] = {}
    if data_available and provider is not None and hasattr(provider, "get_capacity"):
        provider_capacity = provider.get_capacity() or {}

    estimates: list[CapacityEstimate] = []
    for area, desc in _AREAS:
        if area in provider_capacity:
            info = provider_capacity[area]
            estimates.append(
                CapacityEstimate(
                    area=area,
                    workload_level=info.get("level", "Moderate"),
                    risk=info.get("risk", ""),
                    recommendation=info.get("recommendation", ""),
                    register="Observed",
                )
            )
        else:
            estimates.append(
                CapacityEstimate(
                    area=area,
                    workload_level="Unavailable",
                    risk="Cannot assess capacity risk without workload data.",
                    recommendation=f"Connect a workforce-analytics source to measure {desc}.",
                    register="Unavailable",
                )
            )
    return estimates
