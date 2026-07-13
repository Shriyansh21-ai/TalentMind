"""Resume Risk Detection engine.

Assesses a candidate the way a seasoned hiring manager would: not by keyword
matching, but by looking for gaps, instability, stagnation, shallow impact and
missing leadership/communication signals — and by proposing concrete
validation questions to close each gap in an interview.

Pure, deterministic heuristics. No LLM, no I/O.

Public entry point: :func:`build_risk_report`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

from src.models.candidates import Candidate, CareerHistory
from src.intelligence.common import career_utils as cu
from src.intelligence.risk.models import RiskReport

# Sub-risk weights (must sum to 1.0) for the aggregate score.
_WEIGHTS = {
    "gap": 0.20,
    "hopping": 0.20,
    "stagnation": 0.15,
    "depth": 0.20,
    "leadership": 0.10,
    "communication": 0.15,
}

# Levels mapped to a 0-100 contribution for aggregation.
_LEVEL_VALUE = {"Low": 20.0, "Medium": 55.0, "High": 85.0}

# Thresholds.
_SIGNIFICANT_GAP_MONTHS = 6
_SHORT_TENURE_MONTHS = 18
_WEAK_DESCRIPTION_CHARS = 120
_WEAK_SUMMARY_CHARS = 200


@dataclass
class _SubRisk:
    """Internal result of one sub-risk heuristic."""

    level: str
    factors: List[str]
    red_flags: List[str]
    questions: List[str]


def build_risk_report(candidate: Candidate) -> RiskReport:
    """Build a complete :class:`RiskReport` for a candidate.

    Safe on sparse profiles; never raises on missing/empty fields.
    """
    career = candidate.career_history or []

    gap = _employment_gap_risk(career)
    hopping = _job_hopping_risk(career)
    stagnation = _skill_stagnation_risk(candidate)
    depth = _technical_depth_risk(career)
    leadership = _leadership_risk(career)
    communication = _communication_risk(candidate)

    sub_risks = {
        "gap": gap,
        "hopping": hopping,
        "stagnation": stagnation,
        "depth": depth,
        "leadership": leadership,
        "communication": communication,
    }

    risk_score = round(
        sum(_LEVEL_VALUE[sub.level] * _WEIGHTS[key] for key, sub in sub_risks.items()),
        1,
    )
    risk_level = _risk_level(risk_score)

    factors: List[str] = []
    red_flags: List[str] = []
    questions: List[str] = []
    for sub in sub_risks.values():
        factors.extend(sub.factors)
        red_flags.extend(sub.red_flags)
        questions.extend(sub.questions)

    positive_signals = _positive_signals(candidate, career)
    career_consistency = _career_consistency(career)

    return RiskReport(
        overall_risk=_overall_statement(risk_level, len(red_flags)),
        risk_score=risk_score,
        risk_level=risk_level,
        career_consistency=career_consistency,
        employment_gap_risk=gap.level,
        job_hopping_risk=hopping.level,
        skill_stagnation_risk=stagnation.level,
        technical_depth_risk=depth.level,
        leadership_risk=leadership.level,
        communication_risk=communication.level,
        risk_factors=factors,
        red_flags=red_flags,
        validation_questions=questions,
        positive_signals=positive_signals,
    )


# ---------------------------------------------------------------------------
# Individual sub-risk heuristics
# ---------------------------------------------------------------------------


def _employment_gap_risk(career: List[CareerHistory]) -> _SubRisk:
    """Flag employment gaps and generate gap-specific validation questions."""
    gaps = cu.employment_gaps(career, min_gap_months=_SIGNIFICANT_GAP_MONTHS)
    if not gaps:
        return _SubRisk("Low", [], [], [])

    largest = max(gap for _, _, gap in gaps)
    factors = [f"{len(gaps)} employment gap(s) of {_SIGNIFICANT_GAP_MONTHS}+ months."]
    red_flags = [
        f"{gap}-month gap between {prev} and {nxt}." for prev, nxt, gap in gaps
    ]
    questions = [
        f"Ask candidate why there is a {gap}-month employment gap "
        f"between {prev} and {nxt}."
        for prev, nxt, gap in gaps
    ]
    level = "High" if largest >= 12 else "Medium"
    return _SubRisk(level, factors, red_flags, questions)


def _job_hopping_risk(career: List[CareerHistory]) -> _SubRisk:
    """Flag short average tenure and many companies in a short window."""
    if len(career) < 2:
        return _SubRisk("Low", [], [], [])

    average_duration = cu.average_job_duration_months(career)
    short_stints = sum(
        1 for job in career if 0 < job.duration_months < _SHORT_TENURE_MONTHS
    )

    factors: List[str] = []
    red_flags: List[str] = []
    questions: List[str] = []
    level = "Low"

    if average_duration < 12 and len(career) >= 3:
        level = "High"
        red_flags.append(
            f"Frequent job changes — average tenure {average_duration:.0f} months."
        )
        questions.append(
            "Ask candidate about the drivers behind frequent job changes and "
            "what would make them stay long term."
        )
    elif average_duration < _SHORT_TENURE_MONTHS and len(career) >= 3:
        level = "Medium"
        factors.append(f"Below-average tenure ({average_duration:.0f} months).")
        questions.append(
            "Validate tenure expectations and reasons for recent moves."
        )

    if short_stints >= 2:
        factors.append(f"{short_stints} roles shorter than {_SHORT_TENURE_MONTHS} months.")

    return _SubRisk(level, factors, red_flags, questions)


def _skill_stagnation_risk(candidate: Candidate) -> _SubRisk:
    """Flag outdated technologies and overly narrow skill sets."""
    skills = candidate.skills or []
    skill_names = {s.name.lower() for s in skills}

    outdated = sorted(
        {tech for tech in cu.OUTDATED_TECHNOLOGIES if tech in skill_names}
    )
    advanced = sum(1 for s in skills if s.proficiency.lower() == "advanced")

    factors: List[str] = []
    red_flags: List[str] = []
    questions: List[str] = []
    level = "Low"

    if len(skill_names) < 4:
        level = "High"
        red_flags.append(f"Very narrow skill set ({len(skill_names)} skills listed).")
        questions.append(
            "Validate the breadth of the candidate's current technical stack."
        )
    elif len(skill_names) < 7:
        level = "Medium"
        factors.append("Moderately narrow skill set.")

    if outdated:
        level = "High" if level != "High" else level
        red_flags.append(
            "Skill set leans on legacy technologies: " + ", ".join(outdated) + "."
        )
        questions.append(
            "Ask how the candidate has kept current with modern tooling beyond "
            + ", ".join(outdated) + "."
        )

    if advanced == 0 and skills:
        factors.append("No skills self-rated at an advanced proficiency level.")
        if level == "Low":
            level = "Medium"

    return _SubRisk(level, factors, red_flags, questions)


def _technical_depth_risk(career: List[CareerHistory]) -> _SubRisk:
    """Flag shallow role descriptions and absent measurable achievements."""
    if not career:
        return _SubRisk("Medium", ["No role descriptions to assess depth."], [], [])

    weak_descriptions = sum(
        1
        for job in career
        if len(job.description or "") < _WEAK_DESCRIPTION_CHARS
    )
    with_achievements = sum(
        1 for job in career if cu.has_measurable_achievements(job.description or "")
    )

    factors: List[str] = []
    red_flags: List[str] = []
    questions: List[str] = []
    level = "Low"

    if with_achievements == 0:
        level = "High"
        red_flags.append("No quantified achievements found in role descriptions.")
        questions.append(
            "Ask the candidate to quantify the impact of their most significant "
            "project (metrics, scale, outcomes)."
        )
        questions.append("Validate production ownership and end-to-end delivery.")
    elif with_achievements < len(career):
        level = "Medium"
        factors.append("Some roles lack quantified impact.")

    if weak_descriptions >= max(1, len(career) // 2):
        if level == "Low":
            level = "Medium"
        factors.append("Thin role descriptions limit depth assessment.")
        questions.append("Validate system design depth for recent roles.")

    return _SubRisk(level, factors, red_flags, questions)


def _leadership_risk(career: List[CareerHistory]) -> _SubRisk:
    """Flag absence of any leadership evidence."""
    if cu.has_leadership_evidence(career):
        return _SubRisk("Low", [], [], [])

    return _SubRisk(
        "Medium",
        ["No explicit leadership or ownership evidence in titles/descriptions."],
        [],
        [
            "Explore examples of technical leadership, mentoring, or project "
            "ownership."
        ],
    )


def _communication_risk(candidate: Candidate) -> _SubRisk:
    """Flag weak written communication (very short summary/descriptions)."""
    summary = candidate.profile.summary or ""

    factors: List[str] = []
    questions: List[str] = []
    level = "Low"

    if len(summary) < _WEAK_SUMMARY_CHARS:
        level = "Medium"
        factors.append("Professional summary is brief / low-detail.")
        questions.append(
            "Assess written and verbal communication depth during screening."
        )

    return _SubRisk(level, factors, [], questions)


# ---------------------------------------------------------------------------
# Aggregation & positive signals
# ---------------------------------------------------------------------------


def _positive_signals(
    candidate: Candidate,
    career: List[CareerHistory],
) -> List[str]:
    """Collect reassuring, risk-mitigating signals."""
    signals: List[str] = []

    if any(job.duration_months >= 48 for job in career):
        signals.append("Demonstrated long-tenure commitment at an employer.")
    if cu.has_leadership_evidence(career):
        signals.append("Clear leadership / ownership evidence.")
    if any(cu.has_measurable_achievements(job.description or "") for job in career):
        signals.append("Role descriptions include quantified achievements.")
    if cu.domain_consistency(career) >= 0.8 and len(career) >= 2:
        signals.append("Consistent domain focus across roles.")

    signals_from_profile = _verified_profile_signals(candidate)
    signals.extend(signals_from_profile)

    return signals


def _verified_profile_signals(candidate: Candidate) -> List[str]:
    """Trust signals sourced from RedRob verification flags (read-only)."""
    signals: List[str] = []
    redrob = getattr(candidate, "redrob_signals", None)
    if redrob is None:
        return signals

    if getattr(redrob, "verified_email", False) and getattr(
        redrob, "verified_phone", False
    ):
        signals.append("Identity verified (email and phone).")
    if getattr(redrob, "github_activity_score", 0) >= 70:
        signals.append("Strong public GitHub activity.")
    return signals


def _career_consistency(career: List[CareerHistory]) -> float:
    """0-100 consistency of the career narrative (domain + tenure)."""
    if not career:
        return 0.0
    domain = cu.domain_consistency(career) * 100
    average_duration = cu.average_job_duration_months(career)
    tenure_component = min(average_duration / 36.0, 1.0) * 100
    return round(domain * 0.6 + tenure_component * 0.4, 1)


def _risk_level(risk_score: float) -> str:
    """Bucket the aggregate score into Low / Medium / High."""
    if risk_score >= 60:
        return "High"
    if risk_score >= 35:
        return "Medium"
    return "Low"


def _overall_statement(risk_level: str, red_flag_count: int) -> str:
    """Human-readable one-line overall risk statement."""
    base = {
        "Low": "Low risk — profile is consistent and well-evidenced",
        "Medium": "Moderate risk — some areas require validation",
        "High": "Elevated risk — several items need scrutiny",
    }[risk_level]
    if red_flag_count:
        return f"{base} ({red_flag_count} red flag{'s' if red_flag_count != 1 else ''})."
    return f"{base}."
