"""Unified per-candidate insight bundle for the Enterprise Hiring Workspace.

Phase 2 / Milestone 2 introduces several recruiter-facing surfaces (comparison,
talent-pool segmentation, interview intelligence, the enterprise dashboard) that
all need the *same* set of pre-computed candidate signals. Rather than have each
of those modules re-invoke the intelligence / timeline / risk / skill-gap engines
independently (which would duplicate the most expensive computation in the
platform), they all consume a single :class:`CandidateInsights` bundle.

This module owns **no business logic**. It is a pure aggregation layer over the
existing, unmodified engines in ``src/``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from src.models.candidates import Candidate
from src.intelligence.candidate.models import CandidateIntelligence
from src.intelligence.timeline.models import CareerTimelineAnalysis
from src.intelligence.risk.models import RiskReport
from src.hiring.recommendation_model import HiringRecommendation


@dataclass
class CandidateInsights:
    """Everything the workspace needs to know about one candidate, computed once.

    Every field below is produced by an existing engine and copied here verbatim.
    Nothing in this bundle recomputes or alters engine output — it only groups the
    results so downstream workspace modules share a single computation.

    Attributes:
        candidate: The source candidate record.
        match_score: Hybrid match score from the ranking pipeline (0 if unranked).
        intelligence: Output of the Candidate Intelligence engine.
        timeline: Output of the Career Timeline Intelligence engine.
        risk: Output of the Resume Risk Detection engine.
        gap: Skill-gap analysis (``matched`` / ``missing`` / ``match_percent``).
        explanation: Rule-based explainability payload.
        summary: AI recruiter summary lines.
        recommendation: Intelligence-engine hiring recommendation object.
    """

    candidate: Candidate
    match_score: float
    intelligence: CandidateIntelligence
    timeline: CareerTimelineAnalysis
    risk: RiskReport
    gap: Dict[str, Any]
    explanation: Dict[str, Any]
    summary: List[str] = field(default_factory=list)
    recommendation: HiringRecommendation = None  # type: ignore[assignment]

    # -- Convenience accessors (read-only views over the bundled engine output) --

    @property
    def candidate_id(self) -> str:
        """Return the underlying candidate id."""
        return self.candidate.candidate_id

    @property
    def title(self) -> str:
        """Return the candidate's current title."""
        return self.candidate.profile.current_title

    @property
    def company(self) -> str:
        """Return the candidate's current company."""
        return self.candidate.profile.current_company

    @property
    def location(self) -> str:
        """Return the candidate's location."""
        return self.candidate.profile.location

    @property
    def years_of_experience(self) -> float:
        """Return the candidate's years of experience."""
        return self.candidate.profile.years_of_experience

    @property
    def skill_match_percent(self) -> float:
        """Return the JD skill-match percentage (0-100)."""
        return float(self.gap.get("match_percent", 0.0))

    @property
    def missing_skills(self) -> List[str]:
        """Return the JD skills the candidate is missing."""
        return list(self.gap.get("missing", []))

    @property
    def matched_skills(self) -> List[str]:
        """Return the JD skills the candidate already has."""
        return list(self.gap.get("matched", []))
