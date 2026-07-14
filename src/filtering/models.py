"""Filter criteria model for Smart Filtering (Module 6)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Set


@dataclass
class FilterCriteria:
    """Declarative recruiter filter. Every field is optional; ``None`` / empty
    means "no constraint on this dimension".

    The criteria intentionally mix cheap candidate-field constraints (experience,
    skills, company, location) with engine-backed constraints (risk,
    recommendation, the intelligence sub-scores) and workflow constraints
    (pipeline stage). The filtering engine knows how to evaluate each against the
    shared insight bundle + pipeline state.

    Attributes:
        min_experience / max_experience: Years-of-experience bounds.
        required_skills: Skills the candidate must possess (case-insensitive
            substring match against declared skill names); all must be present.
        company: Substring the current company must contain.
        location: Substring the location must contain.
        allowed_risk_levels: Permitted risk bands (e.g. ``{"Low", "Medium"}``).
        allowed_recommendations: Permitted intelligence recommendation labels.
        allowed_stages: Permitted pipeline stage display values.
        min_timeline_score: Minimum career-timeline score.
        min_technical_score: Minimum technical score.
        min_leadership_score: Minimum leadership score.
        min_career_growth: Minimum career-growth score.
        min_learning_velocity: Minimum learning-velocity score.
        min_skill_match: Minimum JD skill-match percentage.
    """

    min_experience: Optional[float] = None
    max_experience: Optional[float] = None
    required_skills: List[str] = field(default_factory=list)
    company: Optional[str] = None
    location: Optional[str] = None
    allowed_risk_levels: Set[str] = field(default_factory=set)
    allowed_recommendations: Set[str] = field(default_factory=set)
    allowed_stages: Set[str] = field(default_factory=set)
    min_timeline_score: Optional[float] = None
    min_technical_score: Optional[float] = None
    min_leadership_score: Optional[float] = None
    min_career_growth: Optional[float] = None
    min_learning_velocity: Optional[float] = None
    min_skill_match: Optional[float] = None

    def is_empty(self) -> bool:
        """Return ``True`` when no constraint is set (a pass-through filter)."""
        return all(
            not value
            for value in (
                self.min_experience,
                self.max_experience,
                self.required_skills,
                self.company,
                self.location,
                self.allowed_risk_levels,
                self.allowed_recommendations,
                self.allowed_stages,
                self.min_timeline_score,
                self.min_technical_score,
                self.min_leadership_score,
                self.min_career_growth,
                self.min_learning_velocity,
                self.min_skill_match,
            )
        )
