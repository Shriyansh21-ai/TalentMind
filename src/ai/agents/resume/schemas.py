"""Structured output schemas for the ResumeAnalystAgent (Module 12).

`ResumeAnalysis` is the single validated artefact the agent produces. It is
**resume-quality only** and score-free at the top level: the platform safety
guard rejects any top-level field whose name looks like a hiring score
(``score``/``rating``/``percent``), so every numeric quality dimension lives in
the nested :class:`ResumeQuality` model. These numbers describe *resume quality*
and must never feed hiring ranking.

The schema is intentionally rich and composable so future agents (Resume Rewrite,
Optimizer, Generator, Comparison, Versioning — Module 15) can consume or extend
it without a redesign.
"""

from __future__ import annotations

from pydantic import Field, field_validator

from src.ai.schemas.base import BaseAIResponse

# ---------------------------------------------------------------------------
# Nested report models (numeric dimensions live here, never at top level)
# ---------------------------------------------------------------------------


class ResumeQuality(BaseAIResponse):
    """Resume-quality dimensions (0-100). **Not** a hiring score (Module 11)."""

    overall: float = 0.0
    structure: float = 0.0
    writing: float = 0.0
    technical_depth: float = 0.0
    project_quality: float = 0.0
    achievements: float = 0.0
    ats_friendliness: float = 0.0
    professionalism: float = 0.0
    career_narrative: float = 0.0


class StructureReport(BaseAIResponse):
    """Resume structure analysis (Module 1)."""

    sections_present: list[str] = Field(default_factory=list)
    sections_missing: list[str] = Field(default_factory=list)
    weak_sections: list[str] = Field(default_factory=list)
    empty_sections: list[str] = Field(default_factory=list)
    observations: list[str] = Field(default_factory=list)


class CareerStory(BaseAIResponse):
    """Career narrative analysis (Module 3)."""

    narrative: str = ""
    direction: str = ""
    growth: str = ""
    consistency: str = ""
    focus: str = ""
    progression_strength: str = ""
    observations: list[str] = Field(default_factory=list)


class TechnicalReport(BaseAIResponse):
    """Technical resume analysis (Module 4)."""

    technologies: list[str] = Field(default_factory=list)
    modern_technologies: list[str] = Field(default_factory=list)
    dated_technologies: list[str] = Field(default_factory=list)
    diversity: str = ""
    depth: str = ""
    breadth: str = ""
    cloud_exposure: bool = False
    ai_exposure: bool = False
    production_exposure: bool = False
    open_source: bool = False
    observations: list[str] = Field(default_factory=list)


class ProjectInsight(BaseAIResponse):
    """Per-project intelligence (Module 5)."""

    name: str = ""
    complexity: str = ""
    business_value: str = ""
    innovation: str = ""
    impact: str = ""
    production_readiness: str = ""
    uniqueness: str = ""
    scalability: str = ""
    technologies: list[str] = Field(default_factory=list)
    evidence: str = ""


class AchievementReport(BaseAIResponse):
    """Achievement intelligence (Module 6)."""

    quantified: list[str] = Field(default_factory=list)
    leadership: list[str] = Field(default_factory=list)
    recognition: list[str] = Field(default_factory=list)
    strength: str = ""
    missing: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)


class ATSReport(BaseAIResponse):
    """ATS optimization report (Module 7). Resume quality only — never ranking."""

    friendliness: str = ""
    matched_keywords: list[str] = Field(default_factory=list)
    missing_keywords: list[str] = Field(default_factory=list)
    overused_keywords: list[str] = Field(default_factory=list)
    parsing_notes: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)


class ResumeRiskFinding(BaseAIResponse):
    """A single, evidence-backed resume-risk finding (Module 8)."""

    type: str = ""
    issue: str = ""
    evidence: str = ""
    severity: str = "low"


class ResumeRiskReport(BaseAIResponse):
    """Resume risk report — evidence only, never hallucinated (Module 8)."""

    level: str = "Low"
    findings: list[ResumeRiskFinding] = Field(default_factory=list)
    positive_signals: list[str] = Field(default_factory=list)


class RewriteSuggestion(BaseAIResponse):
    """A concrete before/after rewrite (Module 9)."""

    before: str = ""
    after: str = ""
    reason: str = ""


class WritingReport(BaseAIResponse):
    """Writing intelligence (Module 9)."""

    tone: str = ""
    clarity: str = ""
    conciseness: str = ""
    action_verb_usage: str = ""
    bullet_quality: str = ""
    observations: list[str] = Field(default_factory=list)
    sample_rewrites: list[RewriteSuggestion] = Field(default_factory=list)


class Improvement(BaseAIResponse):
    """A single prioritized improvement recommendation (Module 10)."""

    title: str = ""
    area: str = ""
    priority: str = "medium"
    impact: str = ""
    rationale: str = ""
    example: str = ""


# ---------------------------------------------------------------------------
# Top-level analysis (score-free field names)
# ---------------------------------------------------------------------------


class ResumeAnalysis(BaseAIResponse):
    """Complete, recruiter-grade resume intelligence (Module 12).

    Every field is derived from resume evidence; numeric quality lives in
    :attr:`resume_quality`. The agent clearly separates **evidence** (facts in
    the resume), **inference** (analysis observations) and **suggestions**
    (the improvement plan / rewrites) — Module 17.
    """

    executive_summary: str
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    career_story: CareerStory = Field(default_factory=CareerStory)
    resume_quality: ResumeQuality = Field(default_factory=ResumeQuality)
    structure: StructureReport = Field(default_factory=StructureReport)
    writing: WritingReport = Field(default_factory=WritingReport)
    technical: TechnicalReport = Field(default_factory=TechnicalReport)
    projects: list[ProjectInsight] = Field(default_factory=list)
    achievements: AchievementReport = Field(default_factory=AchievementReport)
    ats_report: ATSReport = Field(default_factory=ATSReport)
    risk_report: ResumeRiskReport = Field(default_factory=ResumeRiskReport)
    improvement_plan: list[Improvement] = Field(default_factory=list)
    confidence_note: str = ""
    evidence: list[str] = Field(default_factory=list)

    @field_validator("executive_summary")
    @classmethod
    def _summary_non_empty(cls, value: str) -> str:
        """Ensure the executive summary is a non-empty string."""
        text = (value or "").strip()
        if not text:
            raise ValueError("executive_summary must not be empty")
        return text
