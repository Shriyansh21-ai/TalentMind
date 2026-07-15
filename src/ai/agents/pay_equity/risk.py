"""Overall internal-equity risk scoring (feeds Module 1 + the Module 10 gauge).

Combines the compression, inversion and policy-alignment signals into a single
qualitative :class:`EquityRisk` (Low / Medium / High / Unknown). When no internal
compensation data is available the risk is honestly reported as **Unknown** rather
than assumed benign (Module 14).
"""

from __future__ import annotations

from typing import List

from src.ai.agents.pay_equity.schemas import (
    CompressionAssessment,
    EquityRisk,
    InversionAssessment,
    PolicyAlignment,
)

_SEVERITY = {"low": 1, "medium": 2, "high": 3}


def build_equity_risk(
    compression: CompressionAssessment,
    inversion: InversionAssessment,
    policy_alignment: PolicyAlignment,
) -> EquityRisk:
    """Combine the equity signals into one overall risk (Module 1 / gauge)."""
    data_available = compression.data_available or inversion.data_available
    if not data_available:
        return EquityRisk(
            level="Unknown",
            drivers=["Internal compensation data unavailable — equity risk cannot be scored."],
            confidence=0.0,
            data_available=False,
        )

    severities: List[int] = []
    drivers: List[str] = []
    if compression.data_available and compression.risk_level.lower() in _SEVERITY:
        severities.append(_SEVERITY[compression.risk_level.lower()])
        drivers.append(f"Compression risk: {compression.risk_level}.")
    if inversion.data_available and inversion.risk_level.lower() in _SEVERITY:
        severities.append(_SEVERITY[inversion.risk_level.lower()])
        drivers.append(f"Inversion risk: {inversion.risk_level}.")
    if policy_alignment.alignment == "Violation":
        severities.append(3)
        drivers.append("Policy violation flagged.")
    elif policy_alignment.alignment == "Partial":
        severities.append(2)
        drivers.append("Partial policy alignment.")

    peak = max(severities) if severities else 1
    level = {1: "Low", 2: "Medium", 3: "High"}[peak]
    confidence = 70.0 if len(severities) >= 2 else 55.0

    return EquityRisk(
        level=level,
        drivers=drivers or ["No material equity risk drivers detected."],
        confidence=round(confidence, 1),
        data_available=True,
    )
