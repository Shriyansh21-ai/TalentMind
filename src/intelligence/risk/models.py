"""Data model for Resume Risk Detection."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RiskReport:
    """Hiring-manager-style risk assessment for a candidate.

    This is intentionally *not* ATS keyword scoring. It surfaces the things an
    experienced hiring manager would want to validate before an interview, and
    proposes concrete validation questions. Fully heuristic; no LLM, no I/O.

    Attributes:
        overall_risk: Short overall risk statement.
        risk_score: Aggregate risk on 0-100 (higher == riskier).
        risk_level: ``"Low"`` / ``"Medium"`` / ``"High"``.
        risk_factors: Contributing factors (human-readable).
        red_flags: Serious items warranting scrutiny.
        validation_questions: Recruiter-friendly questions to ask.
        positive_signals: Mitigating / reassuring signals.
        career_consistency: 0-100 consistency of the career narrative.
        employment_gap_risk: Sub-risk level for employment gaps.
        job_hopping_risk: Sub-risk level for short tenures / frequent moves.
        skill_stagnation_risk: Sub-risk level for outdated / narrow skills.
        technical_depth_risk: Sub-risk level for shallow impact evidence.
        leadership_risk: Sub-risk level for absent leadership evidence.
        communication_risk: Sub-risk level for weak written communication.
    """

    overall_risk: str
    risk_score: float
    risk_level: str
    career_consistency: float
    employment_gap_risk: str
    job_hopping_risk: str
    skill_stagnation_risk: str
    technical_depth_risk: str
    leadership_risk: str
    communication_risk: str
    risk_factors: list[str] = field(default_factory=list)
    red_flags: list[str] = field(default_factory=list)
    validation_questions: list[str] = field(default_factory=list)
    positive_signals: list[str] = field(default_factory=list)
