"""Data model for Career Timeline Intelligence."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class CareerTimelineAnalysis:
    """Recruiter-facing analysis of a candidate's complete career trajectory.

    All scores are on a 0-100 scale unless noted. This is an independent,
    heuristic assessment; it does not read from or modify the existing ranking,
    scoring, or intelligence engines.

    Attributes:
        timeline_score: Composite quality of the overall career trajectory.
        career_growth_score: Upward progression strength (promotions + seniority).
        promotion_velocity: Promotions per year of experience.
        career_stability: Tenure-based stability (higher == more stable).
        average_job_duration: Mean tenure across roles, in months.
        job_switches: Number of role transitions.
        promotion_count: Number of upward seniority moves.
        leadership_progression: Narrative track label (IC -> management, etc.).
        company_quality_trend: Trend in employer tier over time.
        domain_consistency: Fraction (0-100) of roles in the dominant industry.
        career_story: Multi-sentence recruiter narrative.
        timeline_summary: One-line headline summary.
        strengths: Positive, recruiter-friendly trajectory signals.
        concerns: Trajectory items worth validating.
    """

    timeline_score: float
    career_growth_score: float
    promotion_velocity: float
    career_stability: float
    average_job_duration: float
    job_switches: int
    promotion_count: int
    leadership_progression: str
    company_quality_trend: str
    domain_consistency: float
    career_story: str
    timeline_summary: str
    strengths: List[str] = field(default_factory=list)
    concerns: List[str] = field(default_factory=list)
