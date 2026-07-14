"""Shared test fixtures for the Phase 2 / Milestone 2 test-suite.

Provides a synthetic :class:`Candidate` factory so the new Enterprise Workspace
modules can be exercised without loading the 487 MB production dataset or any
ML dependency (torch / faiss / sentence-transformers). The factory produces a
fully-valid candidate record that satisfies every required pydantic field.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Optional

import pytest

# Ensure the project root is importable when pytest is run from anywhere.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.models.candidates import (  # noqa: E402
    Candidate,
    CareerHistory,
    Education,
    Profile,
    RedrobSignals,
    SalaryRange,
    Skill,
)


def make_candidate(
    candidate_id: str = "CAND_TEST_1",
    years: float = 9.0,
    title: str = "Senior Machine Learning Engineer",
    company: str = "Acme AI",
    location: str = "Bangalore",
    skills: Optional[List[str]] = None,
    endorsements: int = 25,
    summary: str = "Experienced ML engineer building RAG and LLM systems.",
) -> Candidate:
    """Build a fully-populated synthetic candidate.

    Args:
        candidate_id: Stable id.
        years: Years of experience (drives seniority-based heuristics).
        title: Current title (drives domain segmentation).
        company: Current company.
        location: Location.
        skills: Skill names; defaults to an ML-heavy stack.
        endorsements: Endorsements per skill.
        summary: Profile summary text.

    Returns:
        A valid :class:`Candidate`.
    """
    if skills is None:
        skills = ["Python", "Machine Learning", "PyTorch", "LLM", "AWS", "Docker"]

    profile = Profile(
        anonymized_name="Test Candidate",
        headline=title,
        summary=summary,
        location=location,
        country="India",
        years_of_experience=years,
        current_title=title,
        current_company=company,
        current_company_size="1001-5000",
        current_industry="Software",
    )

    career_history = [
        CareerHistory(
            company=company,
            title=title,
            start_date="2021-01-01",
            end_date=None,
            duration_months=48,
            is_current=True,
            industry="Software",
            company_size="1001-5000",
            description="Led ML platform and RAG systems; mentored engineers.",
        ),
        CareerHistory(
            company="Previous Corp",
            title="Machine Learning Engineer",
            start_date="2017-01-01",
            end_date="2020-12-01",
            duration_months=47,
            is_current=False,
            industry="Software",
            company_size="501-1000",
            description="Built recommendation and ranking models.",
        ),
    ]

    education = [
        Education(
            institution="Test Institute of Technology",
            degree="B.Tech",
            field_of_study="Computer Science",
            start_year=2013,
            end_year=2017,
            grade="8.5",
            tier="Tier 1",
        )
    ]

    skill_models = [
        Skill(
            name=name,
            proficiency="Advanced",
            endorsements=endorsements,
            duration_months=36,
        )
        for name in skills
    ]

    redrob = RedrobSignals(
        profile_completeness_score=95.0,
        signup_date="2020-01-01",
        last_active_date="2026-07-01",
        open_to_work_flag=True,
        profile_views_received_30d=120,
        applications_submitted_30d=5,
        recruiter_response_rate=0.8,
        avg_response_time_hours=6.0,
        skill_assessment_scores={"Python": 92.0, "Machine Learning": 88.0},
        connection_count=800,
        endorsements_received=200,
        notice_period_days=30,
        expected_salary_range_inr_lpa=SalaryRange(min=40.0, max=60.0),
        preferred_work_mode="Hybrid",
        willing_to_relocate=True,
        github_activity_score=78.0,
        search_appearance_30d=60,
        saved_by_recruiters_30d=10,
        interview_completion_rate=0.9,
        offer_acceptance_rate=0.7,
        verified_email=True,
        verified_phone=True,
        linkedin_connected=True,
    )

    return Candidate(
        candidate_id=candidate_id,
        profile=profile,
        career_history=career_history,
        education=education,
        skills=skill_models,
        certifications=[],
        languages=[],
        redrob_signals=redrob,
    )


@pytest.fixture
def candidate() -> Candidate:
    """A single default synthetic candidate."""
    return make_candidate()


@pytest.fixture
def candidate_factory():
    """Expose :func:`make_candidate` as a fixture for parametrized cases."""
    return make_candidate
