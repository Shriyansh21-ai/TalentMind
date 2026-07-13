"""Career Timeline Intelligence engine.

Transforms raw career history into recruiter insight using pure, deterministic
heuristics (no LLM, no I/O). The engine infers progression, stability,
promotion velocity, domain focus and employer-quality trend, then renders a
recruiter-friendly narrative plus strength/concern signals.

Public entry point: :func:`build_career_timeline`.
"""

from __future__ import annotations

from typing import List

from src.models.candidates import Candidate, CareerHistory
from src.intelligence.common import career_utils as cu
from src.intelligence.timeline.models import CareerTimelineAnalysis

# Tuning thresholds (months) — grouped here so heuristics stay readable.
_RAPID_PROMOTION_MONTHS = 18
_LONG_TENURE_MONTHS = 48
_SHORT_TENURE_MONTHS = 18


def build_career_timeline(candidate: Candidate) -> CareerTimelineAnalysis:
    """Build a full :class:`CareerTimelineAnalysis` for a candidate.

    Safe on empty or single-role histories, returning a well-formed neutral
    analysis rather than raising.
    """
    career = candidate.career_history or []

    if not career:
        return _empty_analysis()

    ordered = cu.sort_career_chronologically(career)

    average_duration = cu.average_job_duration_months(ordered)
    job_switches = max(0, len(ordered) - 1)
    promotion_count = cu.count_promotions(ordered)
    experience_years = max(cu.total_experience_years(candidate), 0.1)
    promotion_velocity = round(promotion_count / experience_years, 2)

    stability = _career_stability(average_duration)
    growth = _career_growth_score(promotion_count, ordered)
    consistency = round(cu.domain_consistency(ordered) * 100, 1)
    leadership_progression = _leadership_progression(ordered)
    company_trend = _company_quality_trend(ordered)

    timeline_score = _timeline_score(
        growth=growth,
        stability=stability,
        consistency=consistency,
    )

    strengths, concerns = _signals(
        candidate=candidate,
        ordered=ordered,
        average_duration=average_duration,
        promotion_count=promotion_count,
        promotion_velocity=promotion_velocity,
        consistency=consistency,
    )

    story = _career_story(
        candidate=candidate,
        ordered=ordered,
        promotion_count=promotion_count,
        leadership_progression=leadership_progression,
        consistency=consistency,
    )

    summary = _timeline_summary(
        timeline_score=timeline_score,
        job_count=len(ordered),
        experience_years=cu.total_experience_years(candidate),
    )

    return CareerTimelineAnalysis(
        timeline_score=timeline_score,
        career_growth_score=growth,
        promotion_velocity=promotion_velocity,
        career_stability=stability,
        average_job_duration=average_duration,
        job_switches=job_switches,
        promotion_count=promotion_count,
        leadership_progression=leadership_progression,
        company_quality_trend=company_trend,
        domain_consistency=consistency,
        career_story=story,
        timeline_summary=summary,
        strengths=strengths,
        concerns=concerns,
    )


# ---------------------------------------------------------------------------
# Scoring heuristics
# ---------------------------------------------------------------------------


def _career_stability(average_duration: float) -> float:
    """Map average tenure to a 0-100 stability score."""
    if average_duration >= _LONG_TENURE_MONTHS:
        return 95.0
    if average_duration >= 36:
        return 85.0
    if average_duration >= 24:
        return 70.0
    if average_duration >= _SHORT_TENURE_MONTHS:
        return 55.0
    if average_duration >= 12:
        return 40.0
    return 25.0


def _career_growth_score(promotion_count: int, career: List[CareerHistory]) -> float:
    """Blend promotion count with the seniority level ultimately reached."""
    latest_rank = cu.seniority_rank(career[-1].title)
    seniority_component = min(latest_rank / 6.0, 1.0) * 60.0
    promotion_component = min(promotion_count * 20.0, 40.0)
    return round(min(seniority_component + promotion_component, 100.0), 1)


def _timeline_score(growth: float, stability: float, consistency: float) -> float:
    """Composite trajectory quality (independent of existing engines)."""
    score = growth * 0.45 + stability * 0.35 + consistency * 0.20
    return round(min(max(score, 0.0), 100.0), 1)


def _leadership_progression(career: List[CareerHistory]) -> str:
    """Describe the candidate's leadership trajectory as a label."""
    started_managing = cu.is_management_title(career[0].title)
    ends_managing = cu.is_management_title(career[-1].title)
    ends_leading = cu.is_leadership_title(career[-1].title)

    if ends_managing and not started_managing:
        return "Grew into management"
    if ends_managing and started_managing:
        return "Sustained management track"
    if ends_leading:
        return "Senior technical leadership"
    return "Individual contributor track"


def _company_quality_trend(career: List[CareerHistory]) -> str:
    """Report the trend in employer size/tier across the timeline."""
    tiers = [cu.company_size_tier(job.company_size) for job in career]
    tiers = [tier for tier in tiers if tier > 0]

    if len(tiers) < 2:
        return "Insufficient data"
    if tiers[-1] > tiers[0]:
        return "Improving (moving to larger firms)"
    if tiers[-1] < tiers[0]:
        return "Declining (moving to smaller firms)"
    return "Stable"


# ---------------------------------------------------------------------------
# Narrative & signal generation
# ---------------------------------------------------------------------------


def _signals(
    candidate: Candidate,
    ordered: List[CareerHistory],
    average_duration: float,
    promotion_count: int,
    promotion_velocity: float,
    consistency: float,
) -> tuple[List[str], List[str]]:
    """Derive recruiter-friendly strengths and concerns from the timeline."""
    strengths: List[str] = []
    concerns: List[str] = []

    # Promotion / acceleration signals.
    fastest_promotion = _fastest_promotion_months(ordered)
    if fastest_promotion is not None and fastest_promotion <= _RAPID_PROMOTION_MONTHS:
        strengths.append(
            f"Rapid promotion — advanced within {fastest_promotion} months in a role."
        )
    if promotion_velocity >= 0.4:
        strengths.append("Career acceleration — promotions ahead of typical pace.")
    if promotion_count == 0 and len(ordered) >= 3:
        concerns.append("No clear upward title progression across multiple roles.")

    # Tenure / stability signals.
    if any(job.duration_months >= _LONG_TENURE_MONTHS for job in ordered):
        strengths.append("Long tenure — demonstrated commitment at an employer.")
    if average_duration < _SHORT_TENURE_MONTHS and len(ordered) >= 3:
        concerns.append(
            f"Frequent switching — average tenure only {average_duration:.0f} months."
        )

    # Movement pattern.
    if _mostly_lateral(ordered):
        concerns.append("Largely lateral movement with limited seniority change.")

    # Leadership growth.
    if cu.is_management_title(ordered[-1].title) and not cu.is_management_title(
        ordered[0].title
    ):
        strengths.append("Management growth — progressed from IC into leadership.")

    # Domain focus.
    if consistency >= 80:
        strengths.append("Domain specialization — consistent industry focus.")
    elif consistency <= 40 and len(ordered) >= 3:
        concerns.append("Domain hopping — frequent industry changes.")

    # Company profile exposure.
    if cu.has_startup_experience(ordered):
        strengths.append("Startup experience — comfortable in high-ownership settings.")
    if cu.has_enterprise_experience(ordered):
        strengths.append("Enterprise experience — worked at large-scale organizations.")
    if cu.has_consulting_background(ordered):
        strengths.append("Consulting/services background — broad client exposure.")

    return strengths, concerns


def _career_story(
    candidate: Candidate,
    ordered: List[CareerHistory],
    promotion_count: int,
    leadership_progression: str,
    consistency: float,
) -> str:
    """Compose a short recruiter narrative of the career trajectory."""
    years = cu.total_experience_years(candidate)
    first = ordered[0]
    latest = ordered[-1]
    industries = {(job.industry or "").strip() for job in ordered if job.industry}

    parts: List[str] = [
        f"{years:.1f} years across {len(ordered)} "
        f"{'role' if len(ordered) == 1 else 'roles'}.",
    ]

    if len(ordered) >= 2:
        parts.append(
            f"Progressed from {first.title} at {first.company} to "
            f"{latest.title} at {latest.company}."
        )
    else:
        parts.append(f"Currently {latest.title} at {latest.company}.")

    if promotion_count:
        parts.append(
            f"{promotion_count} upward "
            f"{'move' if promotion_count == 1 else 'moves'} in seniority."
        )

    parts.append(f"{leadership_progression}.")

    if consistency >= 80 and industries:
        parts.append(f"Deep focus in {sorted(industries)[0]}.")
    elif len(industries) > 1:
        parts.append(f"Cross-domain exposure across {len(industries)} industries.")

    return " ".join(parts)


def _timeline_summary(
    timeline_score: float,
    job_count: int,
    experience_years: float,
) -> str:
    """One-line headline for the timeline tab."""
    if timeline_score >= 80:
        label = "Strong, upward career trajectory"
    elif timeline_score >= 60:
        label = "Solid, steady career trajectory"
    elif timeline_score >= 40:
        label = "Mixed career trajectory — validate progression"
    else:
        label = "Early or non-linear career trajectory"
    return (
        f"{label} · {experience_years:.1f} yrs · {job_count} "
        f"{'role' if job_count == 1 else 'roles'}"
    )


# ---------------------------------------------------------------------------
# Small internal helpers
# ---------------------------------------------------------------------------


def _fastest_promotion_months(career: List[CareerHistory]) -> int | None:
    """Shortest tenure that immediately preceded an upward move, if any."""
    fastest: int | None = None
    for previous, following in zip(career, career[1:]):
        if cu.seniority_rank(following.title) > cu.seniority_rank(previous.title):
            tenure = max(0, previous.duration_months)
            fastest = tenure if fastest is None else min(fastest, tenure)
    return fastest


def _mostly_lateral(career: List[CareerHistory]) -> bool:
    """True when most transitions kept the same seniority rank."""
    if len(career) < 3:
        return False
    lateral = 0
    transitions = 0
    for previous, following in zip(career, career[1:]):
        transitions += 1
        if cu.seniority_rank(following.title) == cu.seniority_rank(previous.title):
            lateral += 1
    return transitions > 0 and lateral / transitions >= 0.6


def _empty_analysis() -> CareerTimelineAnalysis:
    """Neutral analysis for candidates with no career history."""
    return CareerTimelineAnalysis(
        timeline_score=0.0,
        career_growth_score=0.0,
        promotion_velocity=0.0,
        career_stability=0.0,
        average_job_duration=0.0,
        job_switches=0,
        promotion_count=0,
        leadership_progression="No career history available",
        company_quality_trend="Insufficient data",
        domain_consistency=0.0,
        career_story="No career history is available for this candidate.",
        timeline_summary="No career history available",
        strengths=[],
        concerns=["No career history to analyze."],
    )
