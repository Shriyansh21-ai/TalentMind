"""Trend intelligence (Module 4).

Identifies hiring / approval / compensation / pay-equity / compliance / interview /
committee trends. Trends are inherently **time-series**, which the platform does
not persist, so every trend is reported **Unavailable** (with an honest evidence
note) unless an analytics provider supplies history. Never fabricates a trend
direction (Module 15).
"""

from __future__ import annotations

from typing import Any, Dict, List

from src.ai.agents.hiring_intelligence.schemas import Trend

_TREND_NAMES = [
    "Hiring volume",
    "Approval trend",
    "Compensation trend",
    "Pay-equity trend",
    "Compliance trend",
    "Interview trend",
    "Committee trend",
]


def build_trends(cohort: List[Dict[str, Any]], provider: Any, data_available: bool) -> List[Trend]:
    """Identify hiring trends (Module 4)."""
    provider_trends: Dict[str, Any] = {}
    if data_available and provider is not None and hasattr(provider, "get_trends"):
        provider_trends = (provider.get_trends() or {}).get("series", {})

    trends: List[Trend] = []
    for name in _TREND_NAMES:
        if name in provider_trends:
            info = provider_trends[name]
            trends.append(
                Trend(
                    name=name,
                    direction=info.get("direction", "Flat"),
                    evidence=info.get("evidence", "From the connected analytics source."),
                    confidence=float(info.get("confidence", 60.0)),
                    interpretation=info.get("interpretation", ""),
                    register="Observed",
                )
            )
        else:
            trends.append(
                Trend(
                    name=name,
                    direction="Unavailable",
                    evidence="No historical event data is connected; a trend needs a time series.",
                    confidence=0.0,
                    interpretation="Connect an analytics source (Module 13) to compute this trend.",
                    register="Unavailable",
                )
            )
    return trends
