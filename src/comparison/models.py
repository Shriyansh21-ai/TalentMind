"""Domain models for the Candidate Comparison Workspace (Module 2)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ComparisonRow:
    """A single candidate's normalized metrics for side-by-side comparison.

    Every value is copied from the shared :class:`CandidateInsights` bundle — the
    comparison layer performs no scoring of its own, it only re-shapes existing
    engine output into a uniform, table-friendly record.

    Attributes:
        candidate_id: Stable candidate identifier.
        title: Current job title.
        company: Current company.
        overall_score: Candidate Intelligence overall score (0-100).
        hiring_recommendation: Intelligence-engine recommendation label.
        timeline_score: Career Timeline composite score (0-100).
        risk_score: Resume-risk score (0-100, higher == riskier).
        risk_level: ``Low`` / ``Medium`` / ``High`` risk band.
        technical_score: Technical capability score (0-100).
        leadership_score: Leadership score (0-100).
        experience_score: Experience score (0-100).
        career_growth: Career-growth score (0-100).
        skill_match: JD skill-match percentage (0-100).
        strengths: Top strengths.
        weaknesses: Areas to validate.
        recruiter_summary: AI recruiter summary lines.
        interview_focus: Suggested interview focus areas.
        missing_skills: JD skills the candidate lacks.
    """

    candidate_id: str
    title: str
    company: str
    overall_score: float
    hiring_recommendation: str
    timeline_score: float
    risk_score: float
    risk_level: str
    technical_score: float
    leadership_score: float
    experience_score: float
    career_growth: float
    skill_match: float
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    recruiter_summary: list[str] = field(default_factory=list)
    interview_focus: list[str] = field(default_factory=list)
    missing_skills: list[str] = field(default_factory=list)


# Numeric metric keys eligible for "best candidate" highlighting, mapped to
# whether a *higher* value is better. Risk is the sole lower-is-better metric.
NUMERIC_METRICS: dict[str, bool] = {
    "overall_score": True,
    "timeline_score": True,
    "risk_score": False,
    "technical_score": True,
    "leadership_score": True,
    "experience_score": True,
    "career_growth": True,
    "skill_match": True,
}


@dataclass
class ComparisonReport:
    """A full comparison across up to five candidates.

    Attributes:
        rows: One :class:`ComparisonRow` per compared candidate (ordered).
        best_by_metric: For each numeric metric, the ``candidate_id`` that wins
            it (used by the UI to highlight the leader per row).
    """

    rows: list[ComparisonRow] = field(default_factory=list)
    best_by_metric: dict[str, str] = field(default_factory=dict)

    @property
    def candidate_ids(self) -> list[str]:
        """Return the ids of the compared candidates, in display order."""
        return [row.candidate_id for row in self.rows]
