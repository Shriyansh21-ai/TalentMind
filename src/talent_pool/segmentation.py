"""Deterministic Talent Pool segmentation (Module 3).

Groups candidates into recruiter-friendly :class:`TalentPool` segments using
transparent, threshold-based heuristics over the shared
:class:`CandidateInsights` bundle plus the candidate's declared skills/titles.

Everything here is deterministic and Streamlit-free — no LLM, no I/O, no
randomness — so segmentation is reproducible and unit-testable.
"""

from __future__ import annotations

import re
from typing import Dict, List, Sequence

from src.insights.models import CandidateInsights
from src.talent_pool.models import PoolAssignment, TalentPool

# ---------------------------------------------------------------------------
# Thresholds (single source of truth; tuned to the 0-100 engine scales)
# ---------------------------------------------------------------------------

IMMEDIATE_HIRE_SCORE = 82.0
IMMEDIATE_HIRE_MAX_RISK = 40.0
HIGH_POTENTIAL_LEARNING = 70.0
HIGH_POTENTIAL_GROWTH = 65.0
LEADERSHIP_SCORE = 70.0
NEEDS_UPSKILLING_TECH = 55.0
NEEDS_UPSKILLING_MATCH = 55.0
SENIOR_YEARS = 8.0
SPECIALIST_DOMAIN_CONSISTENCY = 75.0
GENERALIST_DOMAIN_CONSISTENCY = 45.0
FUTURE_PIPELINE_MAX_YEARS = 3.0

# ---------------------------------------------------------------------------
# Domain keyword vocabularies (lower-cased, substring-matched against skills,
# title and headline). Intentionally small and explicit for auditability.
# ---------------------------------------------------------------------------

_DOMAIN_KEYWORDS: Dict[TalentPool, Sequence[str]] = {
    TalentPool.ML_SPECIALISTS: (
        "machine learning", "deep learning", "ml", "nlp", "llm", "pytorch",
        "tensorflow", "transformers", "rag", "computer vision", "data scientist",
        "ml engineer",
    ),
    TalentPool.FRONTEND: (
        "frontend", "front-end", "react", "angular", "vue", "javascript",
        "typescript", "css", "html", "ui engineer", "next.js",
    ),
    TalentPool.BACKEND: (
        "backend", "back-end", "java", "golang", "node", "django", "spring",
        "microservice", "api", "python", "c++", "rust",
    ),
    TalentPool.CLOUD: (
        "aws", "azure", "gcp", "kubernetes", "docker", "terraform", "devops",
        "cloud", "sre", "infrastructure",
    ),
    TalentPool.DATA: (
        "data engineer", "spark", "airflow", "etl", "sql", "warehouse", "hadoop",
        "kafka", "snowflake", "bigquery", "data pipeline",
    ),
}


def _candidate_corpus(insights: CandidateInsights) -> str:
    """Build a single lower-cased haystack of skills + title + headline."""
    candidate = insights.candidate
    parts: List[str] = [candidate.profile.current_title, candidate.profile.headline]
    parts.extend(skill.name for skill in candidate.skills)
    return " ".join(part.lower() for part in parts if part)


def _keyword_present(keyword: str, corpus: str) -> bool:
    """Return ``True`` iff ``keyword`` appears in ``corpus`` as a whole token.

    Uses alphanumeric boundary lookarounds (rather than naive ``in``) so short
    tokens like ``"ml"`` match ``"AI/ML"`` but never ``"html"``, and symbols in
    keywords like ``"c++"`` / ``"next.js"`` are matched literally.
    """
    pattern = r"(?<![a-z0-9])" + re.escape(keyword) + r"(?![a-z0-9])"
    return re.search(pattern, corpus) is not None


def _matched_domains(corpus: str) -> List[TalentPool]:
    """Return the domain pools whose vocabulary appears in ``corpus``."""
    matched: List[TalentPool] = []
    for pool, keywords in _DOMAIN_KEYWORDS.items():
        if any(_keyword_present(keyword, corpus) for keyword in keywords):
            matched.append(pool)
    return matched


def segment_candidate(insights: CandidateInsights) -> PoolAssignment:
    """Segment one candidate into every :class:`TalentPool` they qualify for.

    Args:
        insights: The shared insight bundle for the candidate.

    Returns:
        A :class:`PoolAssignment` listing all matched pools and the rationale for
        each — empty pools list if the candidate matches no segment.
    """
    intel = insights.intelligence
    timeline = insights.timeline
    risk = insights.risk

    pools: List[TalentPool] = []
    rationale: List[str] = []

    def add(pool: TalentPool, reason: str) -> None:
        if pool not in pools:
            pools.append(pool)
            rationale.append(f"{pool.value}: {reason}")

    # -- Readiness axis -----------------------------------------------------
    if (
        intel.overall_score >= IMMEDIATE_HIRE_SCORE
        and risk.risk_score <= IMMEDIATE_HIRE_MAX_RISK
    ):
        add(
            TalentPool.IMMEDIATE_HIRE,
            f"overall {intel.overall_score:.0f} with low risk "
            f"({risk.risk_score:.0f})",
        )

    if (
        intel.learning_velocity >= HIGH_POTENTIAL_LEARNING
        and intel.career_growth_score >= HIGH_POTENTIAL_GROWTH
    ):
        add(
            TalentPool.HIGH_POTENTIAL,
            f"fast learner ({intel.learning_velocity:.0f}) with strong growth "
            f"({intel.career_growth_score:.0f})",
        )

    if insights.years_of_experience <= FUTURE_PIPELINE_MAX_YEARS:
        add(
            TalentPool.FUTURE_PIPELINE,
            f"early-career ({insights.years_of_experience:.1f} yrs)",
        )

    if (
        intel.technical_score < NEEDS_UPSKILLING_TECH
        or insights.skill_match_percent < NEEDS_UPSKILLING_MATCH
    ):
        add(
            TalentPool.NEEDS_UPSKILLING,
            f"technical {intel.technical_score:.0f} / JD match "
            f"{insights.skill_match_percent:.0f}%",
        )

    # -- Shape axis ---------------------------------------------------------
    if intel.leadership_score >= LEADERSHIP_SCORE:
        add(
            TalentPool.LEADERSHIP_TALENT,
            f"leadership {intel.leadership_score:.0f}",
        )

    if insights.years_of_experience >= SENIOR_YEARS:
        add(
            TalentPool.SENIOR_ENGINEERING,
            f"{insights.years_of_experience:.1f} yrs experience",
        )

    if timeline.domain_consistency >= SPECIALIST_DOMAIN_CONSISTENCY:
        add(
            TalentPool.SPECIALIST,
            f"domain focus {timeline.domain_consistency:.0f}%",
        )
    elif timeline.domain_consistency <= GENERALIST_DOMAIN_CONSISTENCY:
        add(
            TalentPool.GENERALIST,
            f"broad domain spread ({timeline.domain_consistency:.0f}%)",
        )

    # -- Domain axis --------------------------------------------------------
    corpus = _candidate_corpus(insights)
    for pool in _matched_domains(corpus):
        add(pool, "skill/title keyword match")

    return PoolAssignment(
        candidate_id=insights.candidate_id,
        pools=pools,
        rationale=rationale,
    )


def segment_pool(
    insights_list: Sequence[CandidateInsights],
) -> Dict[str, PoolAssignment]:
    """Segment a cohort, returning ``{candidate_id: PoolAssignment}``."""
    return {
        insights.candidate_id: segment_candidate(insights)
        for insights in insights_list
    }


def filter_by_pool(
    assignments: Dict[str, PoolAssignment],
    pool: TalentPool,
) -> List[str]:
    """Return the ids of candidates assigned to ``pool``.

    Args:
        assignments: Map produced by :func:`segment_pool`.
        pool: The pool to filter on.

    Returns:
        Candidate ids belonging to ``pool`` (order follows ``assignments``).
    """
    return [
        candidate_id
        for candidate_id, assignment in assignments.items()
        if assignment.in_pool(pool)
    ]


def pool_counts(
    assignments: Dict[str, PoolAssignment],
) -> Dict[str, int]:
    """Return ``{pool_value: candidate_count}`` across all pools (0s included)."""
    counts: Dict[str, int] = {pool.value: 0 for pool in TalentPool}
    for assignment in assignments.values():
        for pool in assignment.pools:
            counts[pool.value] += 1
    return counts
