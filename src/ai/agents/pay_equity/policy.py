"""Compensation policy alignment (Module 5).

Evaluates the offer against a **configurable** company pay philosophy (never
hardcoded — policies are data in ``templates.PAY_POLICIES`` and a custom
:class:`PayPolicy` may be injected). It reports alignment, policy violations and
review requirements. "Violation" here means an *internal policy* exception routed
for review — never a legal conclusion (Module 14).
"""

from __future__ import annotations

from typing import Any

from src.ai.agents.pay_equity.schemas import (
    CompressionAssessment,
    InversionAssessment,
    PolicyAlignment,
)
from src.ai.agents.pay_equity.templates import PayPolicy

# Human-readable descriptions for each review trigger key.
_TRIGGER_TEXT = {
    "outside_band": "Offer sits outside the internal pay band.",
    "compression_high": "High salary-compression risk detected.",
    "compression_medium": "Moderate salary-compression risk detected.",
    "inversion_detected": "Potential pay inversion detected.",
}


def _fires(
    trigger: str,
    *,
    outside_band: bool,
    compression: CompressionAssessment,
    inversion: InversionAssessment,
) -> bool:
    """Return whether a policy ``review_trigger`` condition is met."""
    if trigger == "outside_band":
        return outside_band
    if trigger == "compression_high":
        return compression.risk_level == "High"
    if trigger == "compression_medium":
        return compression.risk_level in ("Medium", "High")
    if trigger == "inversion_detected":
        return inversion.risk_level in ("Medium", "High")
    return False


def evaluate_policy(
    policy: PayPolicy,
    context: dict[str, Any],
    compression: CompressionAssessment,
    inversion: InversionAssessment,
) -> PolicyAlignment:
    """Evaluate the offer against ``policy`` (Module 5)."""
    data_available = compression.data_available or inversion.data_available
    outside_band = bool(context.get("outside_band"))

    if not data_available and context.get("outside_band") is None:
        return PolicyAlignment(
            policy_key=policy.key,
            policy_name=policy.name,
            alignment="Not Evaluable",
            rationale=(
                f"'{policy.name}' prioritizes {', '.join(policy.priority_factors[:2])}; "
                "internal compensation data is unavailable, so band-based alignment cannot be evaluated."
            ),
            violations=[],
            review_requirements=["Connect an HRIS / payroll source to evaluate policy alignment."],
        )

    fired = [
        t
        for t in policy.review_triggers
        if _fires(t, outside_band=outside_band, compression=compression, inversion=inversion)
    ]
    violations = [_TRIGGER_TEXT.get(t, t) for t in fired]

    if not fired:
        alignment = "Aligned"
        rationale = (
            f"No '{policy.name}' review triggers fired; the offer is consistent with the policy."
        )
    elif "outside_band" in fired and "pay_band_consistency" in policy.priority_factors[:1]:
        alignment = "Violation"
        rationale = f"Under '{policy.name}' (pay-band leading), an out-of-band offer is a policy exception requiring review."
    else:
        alignment = "Partial"
        rationale = f"'{policy.name}' review triggers fired: {', '.join(violations)}. Route for review before approval."

    review_requirements = [f"Review: {v}" for v in violations] or ["No policy review required."]
    return PolicyAlignment(
        policy_key=policy.key,
        policy_name=policy.name,
        alignment=alignment,
        rationale=rationale,
        violations=violations,
        review_requirements=review_requirements,
    )
