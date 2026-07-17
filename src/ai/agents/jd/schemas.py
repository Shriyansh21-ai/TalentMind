"""Structured output schemas for the JDAnalystAgent (Module 12).

`JDAnalysis` is the single validated artefact the agent produces. It is
**JD-quality only** and score-free at the top level: the platform safety guard
rejects any top-level field whose name looks like a hiring score
(``score``/``rating``/``percent``), so every numeric quality dimension lives in
the nested :class:`JDQuality` model. These numbers describe *job-description
quality*; they must never influence candidate ranking (Module 11).

Every inference-bearing sub-report carries a ``confidence`` (Module 4 / 17). The
schema is rich and composable so future agents (Module 15) can consume it.
"""

from __future__ import annotations

from pydantic import Field, field_validator

from src.ai.schemas.base import BaseAIResponse

# ---------------------------------------------------------------------------
# Nested reports (numeric dimensions live here, never at top level)
# ---------------------------------------------------------------------------


class JDQuality(BaseAIResponse):
    """JD-quality dimensions (0-100). **Not** a candidate score (Module 11)."""

    overall: float = 0.0
    structure: float = 0.0
    technical_clarity: float = 0.0
    role_clarity: float = 0.0
    requirement_quality: float = 0.0
    business_context: float = 0.0
    hiring_readiness: float = 0.0
    market_alignment: float = 0.0
    organization_clarity: float = 0.0


class StructureReport(BaseAIResponse):
    """Job structure analysis (Module 1)."""

    sections_present: list[str] = Field(default_factory=list)
    sections_missing: list[str] = Field(default_factory=list)
    weak_sections: list[str] = Field(default_factory=list)
    observations: list[str] = Field(default_factory=list)


class RoleIntelligence(BaseAIResponse):
    """Inferred role shape (Module 2)."""

    seniority: str = ""
    technical_level: str = ""
    ownership: str = ""
    leadership_expectations: str = ""
    decision_making: str = ""
    architecture_responsibility: str = ""
    customer_interaction: str = ""
    management_expectations: str = ""
    cross_functional: str = ""
    confidence: float = 0.0
    observations: list[str] = Field(default_factory=list)


class TechnicalIntelligence(BaseAIResponse):
    """Technical requirement analysis (Module 3)."""

    languages: list[str] = Field(default_factory=list)
    frameworks: list[str] = Field(default_factory=list)
    cloud: list[str] = Field(default_factory=list)
    ai_ml: list[str] = Field(default_factory=list)
    devops: list[str] = Field(default_factory=list)
    data: list[str] = Field(default_factory=list)
    security: list[str] = Field(default_factory=list)
    infrastructure: list[str] = Field(default_factory=list)
    architecture: list[str] = Field(default_factory=list)
    technology_maturity: str = ""
    technology_diversity: str = ""
    observations: list[str] = Field(default_factory=list)


class HiringIntentSignal(BaseAIResponse):
    """A single hiring-intent inference with its confidence (Module 4)."""

    intent: str = ""
    rationale: str = ""
    confidence: float = 0.0


class HiringIntent(BaseAIResponse):
    """Why the role is open / what the company is solving (Module 4)."""

    primary_intent: str = ""
    summary: str = ""
    signals: list[HiringIntentSignal] = Field(default_factory=list)
    business_priorities: list[str] = Field(default_factory=list)
    confidence: float = 0.0


class OrganizationIntelligence(BaseAIResponse):
    """Company maturity + type estimate (Module 5)."""

    company_type: str = ""
    technology_maturity: str = ""
    engineering_maturity: str = ""
    signals: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    observations: list[str] = Field(default_factory=list)


class RequirementHierarchy(BaseAIResponse):
    """Separated requirement tiers (Module 6)."""

    mandatory: list[str] = Field(default_factory=list)
    preferred: list[str] = Field(default_factory=list)
    nice_to_have: list[str] = Field(default_factory=list)
    optional: list[str] = Field(default_factory=list)
    hidden_expectations: list[str] = Field(default_factory=list)
    implicit_requirements: list[str] = Field(default_factory=list)


class MarketEstimate(BaseAIResponse):
    """A single market estimate with confidence (Module 9)."""

    dimension: str = ""
    assessment: str = ""
    confidence: float = 0.0


class MarketIntelligence(BaseAIResponse):
    """Heuristic, offline market posture (Module 9)."""

    summary: str = ""
    estimates: list[MarketEstimate] = Field(default_factory=list)


class JDRiskFinding(BaseAIResponse):
    """A single, evidence-backed JD-risk finding (Module 8)."""

    type: str = ""
    issue: str = ""
    evidence: str = ""
    severity: str = "low"


class JDRiskReport(BaseAIResponse):
    """JD risk report — evidence only, never hallucinated (Module 8)."""

    level: str = "Low"
    findings: list[JDRiskFinding] = Field(default_factory=list)
    positive_signals: list[str] = Field(default_factory=list)


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


class JDAnalysis(BaseAIResponse):
    """Complete, enterprise-grade job-description intelligence (Module 12).

    Every field is derived from JD evidence; numeric quality lives in
    :attr:`quality`. The agent clearly separates **evidence** (text in the JD),
    **inference** (analysis, each with confidence) and **suggestions** (the
    improvement plan) — Module 17.
    """

    executive_summary: str
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    role_intelligence: RoleIntelligence = Field(default_factory=RoleIntelligence)
    technical_intelligence: TechnicalIntelligence = Field(default_factory=TechnicalIntelligence)
    hiring_intent: HiringIntent = Field(default_factory=HiringIntent)
    organization_intelligence: OrganizationIntelligence = Field(
        default_factory=OrganizationIntelligence
    )
    requirement_hierarchy: RequirementHierarchy = Field(default_factory=RequirementHierarchy)
    market_intelligence: MarketIntelligence = Field(default_factory=MarketIntelligence)
    quality: JDQuality = Field(default_factory=JDQuality)
    structure: StructureReport = Field(default_factory=StructureReport)
    risk_report: JDRiskReport = Field(default_factory=JDRiskReport)
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
