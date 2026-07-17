"""Filter criteria model for Smart Filtering (Module 6)."""

from __future__ import annotations

from dataclasses import dataclass, field


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

    min_experience: float | None = None
    max_experience: float | None = None
    required_skills: list[str] = field(default_factory=list)
    company: str | None = None
    location: str | None = None
    allowed_risk_levels: set[str] = field(default_factory=set)
    allowed_recommendations: set[str] = field(default_factory=set)
    allowed_stages: set[str] = field(default_factory=set)
    min_timeline_score: float | None = None
    min_technical_score: float | None = None
    min_leadership_score: float | None = None
    min_career_growth: float | None = None
    min_learning_velocity: float | None = None
    min_skill_match: float | None = None

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
