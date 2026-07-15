"""Pay-band derivation — the internal heuristic compensation model (Module 1).

Builds a defensible compensation *range* from the candidate's own stated
expectation plus the existing intelligence signals (seniority, technical and
leadership strength, committee stance, risk). It applies only **internal
heuristic multipliers** (``templates.PREMIUM_FACTORS``) — it never consults a
fabricated salary survey or market benchmark (Module 16). Every applied factor is
recorded in ``basis`` and every unfounded step in ``assumptions`` so the range is
fully traceable.

Currency/unit follow the candidate record (INR LPA); currency conversion is a
prepared Module 14 extension, not implemented here.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from src.ai.agents.compensation.schemas import CompensationRange
from src.ai.agents.compensation.templates import PREMIUM_FACTORS, PREMIUM_THRESHOLDS

# Fallback baseline when the candidate stated no expectation (Assumption only).
_BASELINE_LPA_PER_YEAR = 4.0
_MIN_BASELINE_LPA = 8.0


def _num(source: Dict[str, Any], key: str, default: float = 0.0) -> float:
    """Return a float for ``source[key]`` (0.0 on missing/invalid)."""
    try:
        return float(source.get(key, default))
    except (TypeError, ValueError):
        return default


def _label(confidence: float) -> str:
    """Map a 0-100 confidence to a qualitative label."""
    if confidence >= 75:
        return "High"
    if confidence >= 55:
        return "Moderate"
    return "Low"


def _anchor(evidence: Dict[str, Any]) -> Tuple[float, float, bool, str, str]:
    """Return ``(anchor_min, anchor_max, observed, currency, unit)``.

    Uses the candidate's stated expectation when present (Observed Evidence);
    otherwise derives a seniority-based baseline (Assumption).
    """
    comp = evidence.get("candidate_comp") or {}
    currency = comp.get("currency", "INR")
    unit = comp.get("unit", "LPA")
    exp_min = _num(comp, "expected_min")
    exp_max = _num(comp, "expected_max")
    if exp_min > 0 and exp_max >= exp_min:
        return exp_min, exp_max, True, currency, unit

    # Fallback: seniority baseline (explicitly an assumption, not market data).
    years = _num(evidence.get("candidate_overview") or {}, "years_of_experience")
    baseline = max(_MIN_BASELINE_LPA, years * _BASELINE_LPA_PER_YEAR)
    return baseline * 0.9, baseline * 1.2, False, currency, unit


def derive_pay_band(evidence: Dict[str, Any]) -> CompensationRange:
    """Derive the recommended :class:`CompensationRange` (Module 1).

    Args:
        evidence: The aggregated compensation evidence dict.

    Returns:
        A defensible range with basis + assumptions attached.
    """
    anchor_min, anchor_max, observed, currency, unit = _anchor(evidence)
    base_target = (anchor_min + anchor_max) / 2.0

    intelligence = evidence.get("intelligence") or {}
    risk = evidence.get("risk") or {}
    committee = evidence.get("committee") or {}
    recommendation = evidence.get("recommendation") or {}

    basis: List[str] = []
    assumptions: List[str] = []

    if observed:
        basis.append(
            f"Candidate stated expectation {currency} {anchor_min:.1f}-{anchor_max:.1f} {unit} "
            "(Observed Evidence)."
        )
    else:
        assumptions.append(
            "Candidate stated no salary expectation; band anchored on a seniority "
            "baseline (Assumption — internal heuristic, not market data)."
        )

    premium = 0.0
    tech = _num(intelligence, "technical_score")
    if tech >= PREMIUM_THRESHOLDS["technical_strong"]:
        premium += PREMIUM_FACTORS["skill_premium"]
        basis.append(f"Skill premium applied (technical signal {tech:.0f}/100, Candidate Intelligence).")

    lead = _num(intelligence, "leadership_score")
    if lead >= PREMIUM_THRESHOLDS["leadership_strong"]:
        premium += PREMIUM_FACTORS["leadership_premium"]
        basis.append(f"Leadership premium applied (leadership signal {lead:.0f}/100, Candidate Intelligence).")

    stance = str((committee.get("consensus") or {}).get("recommendation", "")) or str(recommendation.get("recommendation", ""))
    if "strong" in stance.lower():
        premium += PREMIUM_FACTORS["strategic_premium"]
        basis.append(f"Strategic premium applied ('{stance}' from the hiring decision).")

    discount = 0.0
    if str(risk.get("risk_level", "")).lower() == "high" or _num(risk, "risk_score") >= 70:
        discount = PREMIUM_FACTORS["risk_discount"]
        basis.append(f"Risk discount applied (risk level {risk.get('risk_level', 'elevated')}, Resume Risk Detection).")

    target = base_target * (1.0 + premium - discount)
    spread = PREMIUM_FACTORS["band_spread"]
    minimum = target * (1.0 - spread)
    maximum = target * (1.0 + spread)
    # Never let the band collapse or invert.
    minimum = min(minimum, target)
    maximum = max(maximum, target)

    assumptions.append("Recommendation based on internal heuristic model; no external salary survey was used.")

    # Confidence: coverage of evidence + whether the anchor was observed.
    confidence = 45.0
    if observed:
        confidence += 20.0
    intel_conf = _num(intelligence, "confidence")
    if intel_conf:
        confidence += min(20.0, intel_conf * 0.2)
    if committee:
        confidence += 10.0
    confidence = max(0.0, min(100.0, confidence))

    return CompensationRange(
        currency=currency,
        unit=unit,
        minimum=round(minimum, 2),
        target=round(target, 2),
        maximum=round(maximum, 2),
        confidence=round(confidence, 1),
        confidence_label=_label(confidence),
        basis=basis,
        assumptions=assumptions,
    )
