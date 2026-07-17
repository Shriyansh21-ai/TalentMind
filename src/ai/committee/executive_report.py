"""Confidence metrics + executive report assembly (Modules 9, 13).

`compute_confidence_metrics` produces five explainable 0-100 hiring-confidence
signals; `build_committee_report` assembles the full :class:`CommitteeReport`
from every deliberation artefact plus the Chair's decision.
"""

from __future__ import annotations

import statistics
from typing import TYPE_CHECKING

from src.ai.committee.schemas import (
    CommitteeDecision,
    CommitteeReport,
    ConfidenceMetrics,
    Conflict,
    Consensus,
    ConsensusLevel,
    DiscussionRound,
    MemberOpinion,
)

if TYPE_CHECKING:
    from src.ai.committee.committee import EvidenceBundle

_CONSENSUS_STRENGTH = {
    ConsensusLevel.STRONG: 92.0,
    ConsensusLevel.MODERATE: 72.0,
    ConsensusLevel.SPLIT: 45.0,
    ConsensusLevel.NONE: 25.0,
}

# Evidence sources the committee ideally has for a full-confidence decision.
_EXPECTED_SOURCES = 7


def _clamp(v: float) -> float:
    """Clamp a value into 0-100."""
    return max(0.0, min(100.0, v))


def compute_confidence_metrics(
    opinions: list[MemberOpinion],
    consensus: Consensus,
    bundle: EvidenceBundle,
) -> ConfidenceMetrics:
    """Compute the five explainable confidence signals (Module 13)."""
    active = [o for o in opinions if not o.abstained]
    n_sources = len(bundle.available_sources)

    coverage = _clamp(100.0 * (n_sources / _EXPECTED_SOURCES))
    consensus_strength = _clamp(
        0.6 * _CONSENSUS_STRENGTH.get(consensus.level, 25.0)
        + 0.4 * consensus.agreement_ratio * 100.0
    )

    confidences = [o.confidence for o in active] or [0.0]
    spread = statistics.pstdev(confidences) if len(confidences) > 1 else 0.0
    distribution = _clamp(statistics.fmean(confidences) - 0.5 * spread)

    abstentions = sum(1 for o in opinions if o.abstained)
    risk_penalty = (
        25.0
        if (bundle.risk and "high" in str(getattr(bundle.risk, "risk_level", "")).lower())
        else 0.0
    )
    unknown_risk = _clamp(
        (1 - n_sources / _EXPECTED_SOURCES) * 55.0
        + (abstentions / max(1, len(opinions))) * 30.0
        + risk_penalty
    )

    stability = _decision_stability(opinions, consensus)

    overall = _clamp(
        0.20 * coverage
        + 0.35 * consensus_strength
        + 0.15 * distribution
        + 0.15 * stability
        + 0.15 * (100.0 - unknown_risk)
    )

    explanations = {
        "evidence_coverage": (
            f"{n_sources}/{_EXPECTED_SOURCES} expected evidence sources contributed "
            f"-> {coverage:.0f}/100."
        ),
        "consensus_strength": (
            f"{consensus.level.value} with {consensus.agreement_ratio * 100:.0f}% weighted "
            f"agreement -> {consensus_strength:.0f}/100."
        ),
        "confidence_distribution": (
            f"Members' mean confidence {statistics.fmean(confidences):.0f}% with spread "
            f"{spread:.0f} -> {distribution:.0f}/100 (tighter is better)."
        ),
        "unknown_risk": (
            f"{abstentions} abstention(s), {_EXPECTED_SOURCES - n_sources} missing source(s)"
            + (", elevated risk level" if risk_penalty else "")
            + f" -> {unknown_risk:.0f}/100 unknown risk (lower is better)."
        ),
        "decision_stability": (
            f"Recommendation is {'stable' if stability >= 60 else 'sensitive'} to dropping the "
            f"single highest-weight member -> {stability:.0f}/100."
        ),
    }

    return ConfidenceMetrics(
        evidence_coverage=coverage,
        consensus_strength=consensus_strength,
        confidence_distribution=distribution,
        unknown_risk=unknown_risk,
        decision_stability=stability,
        overall=overall,
        explanations=explanations,
    )


def _decision_stability(opinions: list[MemberOpinion], consensus: Consensus) -> float:
    """Return 0-100 stability: does the label survive dropping the top voice?"""
    from src.ai.committee.consensus import build_consensus
    from src.ai.committee.schemas import CommitteeMode

    if len(opinions) <= 1 or not consensus.member_weights:
        return 50.0
    top_role = max(consensus.member_weights, key=consensus.member_weights.get)
    reduced = [o for o in opinions if o.role != top_role]
    if not reduced:
        return 50.0
    recomputed = build_consensus(reduced, CommitteeMode.BALANCED)
    return 85.0 if recomputed.recommendation == consensus.recommendation else 40.0


def build_committee_report(
    *,
    meeting_id: str,
    bundle: EvidenceBundle,
    mode: str,
    opinions: list[MemberOpinion],
    discussion: DiscussionRound,
    consensus: Consensus,
    conflicts: list[Conflict],
    confidence: ConfidenceMetrics,
    decision: CommitteeDecision,
    warnings: list[str],
) -> CommitteeReport:
    """Assemble the full :class:`CommitteeReport` (Module 9)."""
    overview = {
        "candidate_id": bundle.candidate_id,
        "title": bundle.title,
        "company": bundle.company,
        "years_of_experience": bundle.years_of_experience,
        "location": bundle.location,
    }
    resume_summary = (
        bundle.resume_analysis.executive_summary
        if bundle.resume_analysis
        else "No resume analysis available."
    )
    jd_summary = (
        bundle.jd_analysis.executive_summary
        if bundle.jd_analysis
        else "No job description provided."
    )
    sources = sorted({s for o in opinions for s in o.evidence_sources})
    return CommitteeReport(
        meeting_id=meeting_id,
        candidate_id=bundle.candidate_id,
        mode=mode,
        candidate_overview=overview,
        resume_summary=resume_summary,
        jd_summary=jd_summary,
        opinions=opinions,
        discussion=discussion,
        consensus=consensus,
        conflicts=conflicts,
        confidence=confidence,
        decision=decision,
        evidence_sources=sources,
        warnings=warnings,
    )
