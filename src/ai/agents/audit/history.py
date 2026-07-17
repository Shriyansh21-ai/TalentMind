"""Historical decision explorer (Module 8).

Reconstructs past hiring decisions **using stored artifacts only**, via an
optional injected archive provider. TalentMind ships no archive connector, so the
default is honest: "No historical audit archive connected." — it never fabricates
unavailable history (Module 14).
"""

from __future__ import annotations

from typing import Any

from src.ai.agents.audit.schemas import HistoricalReconstruction


def reconstruct_history(candidate_id: str, provider: Any) -> HistoricalReconstruction:
    """Reconstruct historical decisions from stored artifacts (Module 8)."""
    if provider is None or not getattr(provider, "is_available", lambda: False)():
        return HistoricalReconstruction(
            available=False,
            status_message="No historical audit archive connected; showing the current decision only.",
            records=[],
        )

    records: list[dict] | None = provider.get_history(candidate_id)
    records = list(records or [])
    return HistoricalReconstruction(
        available=True,
        status_message=(
            f"{len(records)} historical record(s) reconstructed from the connected archive."
            if records
            else "Archive connected, but no historical records found for this candidate."
        ),
        records=records,
    )
