"""Shared, pure career-analysis utilities.

These helpers are consumed by both the Career Timeline engine
(``src.intelligence.timeline``) and the Resume Risk engine
(``src.intelligence.risk``). They contain **no** scoring/ranking logic tied to
the existing engines — only reusable primitives (date parsing, tenure math,
title seniority, company sizing, keyword detection) so that the two new modules
share one implementation instead of duplicating heuristics.

All functions are deterministic and free of side effects. No LLM, no I/O.
"""

from __future__ import annotations

import re
from datetime import date
from typing import List, Optional, Tuple

from src.models.candidates import Candidate, CareerHistory

# ---------------------------------------------------------------------------
# Keyword vocabularies (single source of truth for both new engines)
# ---------------------------------------------------------------------------

# Ordered by seniority so the *highest* matching rank wins.
_SENIORITY_KEYWORDS: List[Tuple[int, Tuple[str, ...]]] = [
    (6, ("chief", "cto", "ceo", "cio", "vp", "vice president")),
    (5, ("director", "head of", "head,", " head", "manager", "engineering manager")),
    (4, ("principal", "staff", "architect", "lead")),
    (3, ("senior", "sr.", "sr ")),
    (1, ("junior", "jr.", "jr ", "associate", "trainee", "intern")),
]

_MANAGEMENT_KEYWORDS: Tuple[str, ...] = (
    "manager",
    "head",
    "director",
    "vp",
    "vice president",
    "chief",
    "cto",
    "ceo",
)

_LEADERSHIP_KEYWORDS: Tuple[str, ...] = _MANAGEMENT_KEYWORDS + (
    "lead",
    "principal",
    "staff",
    "architect",
)

_CONSULTING_KEYWORDS: Tuple[str, ...] = (
    "consult",
    "advisory",
    "it services",
)

_LEADERSHIP_VERBS: Tuple[str, ...] = (
    "led",
    "managed",
    "mentored",
    "owned",
    "spearheaded",
    "directed",
    "coordinated",
    "built the team",
    "hired",
)

# Technologies commonly treated as legacy / declining in modern hiring.
# Public: consumed by the risk engine's skill-stagnation heuristic.
OUTDATED_TECHNOLOGIES: Tuple[str, ...] = (
    "jquery",
    "angularjs",
    "flash",
    "silverlight",
    "perl",
    "svn",
    "cvs",
    "vb6",
    "visual basic",
    "cobol",
    "coffeescript",
    "backbone",
    "webforms",
)


# ---------------------------------------------------------------------------
# Dates & tenure
# ---------------------------------------------------------------------------


def parse_date(value: Optional[str]) -> Optional[date]:
    """Parse an ISO ``YYYY-MM-DD`` date string, returning ``None`` on failure.

    Gracefully tolerates ``None`` (open-ended / current roles) and malformed
    values rather than raising.
    """
    if not value:
        return None
    try:
        return date.fromisoformat(value.strip()[:10])
    except (ValueError, AttributeError):
        return None


def sort_career_chronologically(
    career: List[CareerHistory],
) -> List[CareerHistory]:
    """Return career history ordered oldest-first by start date.

    Entries with unparseable start dates are pushed to the end while keeping a
    stable relative order.
    """
    return sorted(
        career,
        key=lambda job: (parse_date(job.start_date) or date.max),
    )


def months_between(earlier: Optional[date], later: Optional[date]) -> Optional[int]:
    """Whole-month distance between two dates (``later - earlier``).

    Returns ``None`` if either date is missing.
    """
    if earlier is None or later is None:
        return None
    return (later.year - earlier.year) * 12 + (later.month - earlier.month)


def average_job_duration_months(career: List[CareerHistory]) -> float:
    """Mean tenure (in months) across all roles; ``0.0`` when empty."""
    if not career:
        return 0.0
    total = sum(max(0, job.duration_months) for job in career)
    return round(total / len(career), 1)


def total_experience_years(candidate: Candidate) -> float:
    """Authoritative years of experience.

    Prefers the profile value; falls back to summed role durations so velocity
    ratios never divide by zero.
    """
    profile_years = getattr(candidate.profile, "years_of_experience", 0) or 0
    if profile_years > 0:
        return float(profile_years)
    total_months = sum(max(0, job.duration_months) for job in candidate.career_history)
    return round(total_months / 12, 1)


def employment_gaps(
    career: List[CareerHistory],
    min_gap_months: int = 3,
) -> List[Tuple[str, str, int]]:
    """Detect employment gaps between consecutive roles.

    Args:
        career: Career history (any order; sorted internally).
        min_gap_months: Minimum gap size (months) worth reporting.

    Returns:
        A list of ``(previous_company, next_company, gap_months)`` tuples for
        every gap at or above ``min_gap_months``.
    """
    ordered = sort_career_chronologically(career)
    gaps: List[Tuple[str, str, int]] = []

    for previous, following in zip(ordered, ordered[1:]):
        prev_end = parse_date(previous.end_date)
        next_start = parse_date(following.start_date)
        gap = months_between(prev_end, next_start)
        if gap is not None and gap >= min_gap_months:
            gaps.append((previous.company, following.company, gap))

    return gaps


# ---------------------------------------------------------------------------
# Titles & seniority
# ---------------------------------------------------------------------------


def seniority_rank(title: str) -> int:
    """Map a job title to a coarse seniority rank (higher == more senior).

    Ranks: 6 exec, 5 management, 4 lead/principal/staff/architect, 3 senior,
    2 individual contributor (default), 1 junior/entry.
    """
    text = (title or "").lower()
    for rank, keywords in _SENIORITY_KEYWORDS:
        if any(keyword in text for keyword in keywords):
            return rank
    return 2  # default individual-contributor level


def is_management_title(title: str) -> bool:
    """True when the title denotes people/management responsibility."""
    text = (title or "").lower()
    return any(keyword in text for keyword in _MANAGEMENT_KEYWORDS)


def is_leadership_title(title: str) -> bool:
    """True for management *or* senior technical-leadership titles."""
    text = (title or "").lower()
    return any(keyword in text for keyword in _LEADERSHIP_KEYWORDS)


def has_leadership_evidence(career: List[CareerHistory]) -> bool:
    """True when any title or role description shows leadership evidence."""
    for job in career:
        if is_leadership_title(job.title):
            return True
        description = (job.description or "").lower()
        if any(verb in description for verb in _LEADERSHIP_VERBS):
            return True
    return False


# ---------------------------------------------------------------------------
# Companies & domains
# ---------------------------------------------------------------------------


def company_size_tier(company_size: Optional[str]) -> int:
    """Classify a company-size band into a tier.

    Tiers: 1 startup (<=50), 2 growth (51-500), 3 large (501-5000),
    4 enterprise (>5000). Returns ``0`` when the size is unknown.
    """
    if not company_size:
        return 0

    if "+" in company_size:
        # e.g. "10001+" -> treat by its lower bound.
        numbers = re.findall(r"\d+", company_size)
        lower = int(numbers[0]) if numbers else 0
        return _tier_from_headcount(lower)

    numbers = [int(n) for n in re.findall(r"\d+", company_size)]
    if not numbers:
        return 0
    return _tier_from_headcount(max(numbers))


def _tier_from_headcount(headcount: int) -> int:
    """Bucket a headcount into a company tier (helper for ``company_size_tier``)."""
    if headcount <= 50:
        return 1
    if headcount <= 500:
        return 2
    if headcount <= 5000:
        return 3
    return 4


def has_startup_experience(career: List[CareerHistory]) -> bool:
    """True when the candidate worked at a startup-sized company (<=50)."""
    return any(company_size_tier(job.company_size) == 1 for job in career)


def has_enterprise_experience(career: List[CareerHistory]) -> bool:
    """True when the candidate worked at an enterprise-sized company (>5000)."""
    return any(company_size_tier(job.company_size) == 4 for job in career)


def has_consulting_background(career: List[CareerHistory]) -> bool:
    """True when any company or industry indicates consulting/services work."""
    for job in career:
        haystack = f"{job.company} {job.industry}".lower()
        if any(keyword in haystack for keyword in _CONSULTING_KEYWORDS):
            return True
    return False


def domain_consistency(career: List[CareerHistory]) -> float:
    """Fraction (0-1) of roles in the most common industry.

    A proxy for domain specialization vs. domain hopping. Returns ``1.0`` for
    a single role and ``0.0`` for empty history.
    """
    if not career:
        return 0.0
    if len(career) == 1:
        return 1.0

    counts: dict[str, int] = {}
    for job in career:
        key = (job.industry or "unknown").strip().lower()
        counts[key] = counts.get(key, 0) + 1

    dominant = max(counts.values())
    return round(dominant / len(career), 2)


def count_promotions(career: List[CareerHistory]) -> int:
    """Count upward seniority transitions across the chronological timeline."""
    ordered = sort_career_chronologically(career)
    promotions = 0
    for previous, following in zip(ordered, ordered[1:]):
        if seniority_rank(following.title) > seniority_rank(previous.title):
            promotions += 1
    return promotions


def has_measurable_achievements(text: str) -> bool:
    """Heuristic: does the text contain quantified impact (numbers / %)?"""
    if not text:
        return False
    return bool(re.search(r"\d+\s?%|\$\s?\d+|\b\d{2,}\b|\bx\d+\b", text.lower()))
