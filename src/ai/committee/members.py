"""The committee panel — independent specialist reviewers (Modules 1, 2).

Each member is a *virtual role* that consumes a slice of the already-computed
structured evidence (resume analysis, JD analysis, candidate intelligence,
timeline, risk, recommendation, interview plan) and produces an independent
:class:`MemberOpinion`. **No member re-runs a deterministic engine** — they only
interpret existing outputs — and no member can see another's opinion (the reviews
run in parallel). Every strength / concern / evidence item names its source, so
nothing is fabricated (Module 16).

Members are pure functions of ``(bundle, mode)``, which makes them deterministic
and trivially testable. The moderator wraps each as an orchestration agent to run
the reviews in parallel through the workflow engine.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from src.ai.committee.schemas import CommitteeMode, MemberOpinion, Recommendation

if TYPE_CHECKING:  # avoid a runtime import cycle with committee.py
    from src.ai.committee.committee import EvidenceBundle

ReviewFn = Callable[["EvidenceBundle", CommitteeMode], MemberOpinion]


@dataclass
class CommitteeMember:
    """A committee seat: a role identity + its independent review function."""

    role: str
    role_title: str
    capability: str
    review_fn: ReviewFn

    def review(self, bundle: EvidenceBundle, mode: CommitteeMode) -> MemberOpinion:
        """Produce this member's independent opinion for ``bundle``."""
        return self.review_fn(bundle, mode)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _rec_from_score(score: float) -> Recommendation:
    """Map a 0-100 evidence score to a member recommendation label."""
    if score >= 78:
        return Recommendation.HIRE
    if score >= 64:
        return Recommendation.LEAN_HIRE
    if score >= 48:
        return Recommendation.HOLD
    if score >= 34:
        return Recommendation.LEAN_NO_HIRE
    return Recommendation.NO_HIRE


def _rec_from_risk(level: str) -> Recommendation:
    """Map a risk level to a stance (higher risk → more negative)."""
    low = (level or "").lower()
    if "high" in low:
        return Recommendation.NO_HIRE
    if low.startswith("medium"):
        return Recommendation.LEAN_NO_HIRE
    if "low-medium" in low or "low medium" in low:
        return Recommendation.HOLD
    return Recommendation.LEAN_HIRE  # Low risk is a (mild) positive signal


def _map_rec_string(text: str) -> Recommendation:
    """Fuzzy-map an engine recommendation string to a stance label."""
    low = (text or "").lower()
    if "strong" in low and "hire" in low:
        return Recommendation.HIRE
    if "reject" in low or "no hire" in low or low == "no":
        return Recommendation.NO_HIRE
    if "lean" in low and ("no" in low or "reject" in low):
        return Recommendation.LEAN_NO_HIRE
    if "lean" in low:
        return Recommendation.LEAN_HIRE
    if "hire" in low:
        return Recommendation.HIRE
    if "consider" in low or "maybe" in low:
        return Recommendation.LEAN_HIRE
    return Recommendation.HOLD


def _abstain(role: str, title: str, reason: str) -> MemberOpinion:
    """Return a low-confidence abstention when required evidence is absent."""
    return MemberOpinion(
        role=role,
        role_title=title,
        recommendation=Recommendation.HOLD,
        confidence=25.0,
        opinion=f"Abstaining: {reason}",
        strengths=[],
        concerns=[f"Insufficient evidence: {reason}"],
        evidence=[],
        evidence_sources=[],
        abstained=True,
    )


# ---------------------------------------------------------------------------
# Member reviewers
# ---------------------------------------------------------------------------


def _resume_expert(bundle: EvidenceBundle, mode: CommitteeMode) -> MemberOpinion:
    """Resume Expert — reads the ResumeAnalysis (resume quality as evidence)."""
    ra = bundle.resume_analysis
    if ra is None:
        return _abstain("resume_expert", "Resume Expert", "no resume analysis available")
    q = ra.resume_quality
    rec = _rec_from_score(q.overall)
    evidence = [
        f"[Resume Analysis] overall resume quality {q.overall:.0f}/100",
        f"[Resume Analysis] technical depth {q.technical_depth:.0f}, achievements {q.achievements:.0f}",
        f"[Resume Analysis] ATS friendliness {ra.ats_report.friendliness}",
    ]
    concerns = list(ra.weaknesses[:3])
    if ra.risk_report.findings:
        concerns.append(
            f"Resume risk: {ra.risk_report.level} ({len(ra.risk_report.findings)} finding(s))"
        )
    return MemberOpinion(
        role="resume_expert",
        role_title="Resume Expert",
        recommendation=rec,
        confidence=min(90.0, 55.0 + q.overall * 0.3),
        opinion=(
            f"The resume presents {('strong' if q.overall >= 65 else 'adequate' if q.overall >= 50 else 'weak')} "
            f"evidence of the candidate's background (quality {q.overall:.0f}/100)."
        ),
        strengths=list(ra.strengths[:3]),
        concerns=concerns[:4],
        evidence=evidence,
        evidence_sources=["Resume Analyst Agent"],
    )


def _jd_expert(bundle: EvidenceBundle, mode: CommitteeMode) -> MemberOpinion:
    """JD Expert — reads the JDAnalysis (role readiness / clarity as context)."""
    ja = bundle.jd_analysis
    if ja is None:
        return _abstain("jd_expert", "JD Expert", "no job description provided")
    q = ja.quality
    # The JD expert assesses whether the role is defined clearly enough to hire
    # against confidently — an unclear/high-risk JD lowers decision confidence.
    if ja.risk_report.level.lower().startswith("high"):
        rec = Recommendation.HOLD
    elif q.role_clarity >= 65 and q.requirement_quality >= 60:
        rec = Recommendation.LEAN_HIRE
    else:
        rec = Recommendation.HOLD
    evidence = [
        f"[JD Analysis] role clarity {q.role_clarity:.0f}/100, requirement quality {q.requirement_quality:.0f}/100",
        f"[JD Analysis] inferred role: {ja.role_intelligence.seniority}",
        f"[JD Analysis] hiring intent: {ja.hiring_intent.primary_intent} ({ja.hiring_intent.confidence:.0f}%)",
    ]
    concerns = []
    if ja.risk_report.findings:
        concerns.append(
            f"JD risk: {ja.risk_report.level} ({len(ja.risk_report.findings)} finding(s))"
        )
    return MemberOpinion(
        role="jd_expert",
        role_title="JD Expert",
        recommendation=rec,
        confidence=min(85.0, 50.0 + q.overall * 0.3),
        opinion=(
            f"The role is {('well-defined' if q.role_clarity >= 65 else 'loosely defined')}; "
            f"decisions should account for this clarity level."
        ),
        strengths=list(ja.strengths[:2]),
        concerns=concerns,
        evidence=evidence,
        evidence_sources=["JD Analyst Agent"],
    )


def _technical_hiring_manager(bundle: EvidenceBundle, mode: CommitteeMode) -> MemberOpinion:
    """Technical Hiring Manager — reads Candidate Intelligence technical signals."""
    intel = bundle.intelligence
    if intel is None:
        return _abstain(
            "technical_hiring_manager", "Technical Hiring Manager", "no candidate intelligence"
        )
    score = float(getattr(intel, "technical_score", 0.0))
    rec = _rec_from_score(score)
    evidence = [
        f"[Candidate Intelligence] technical {score:.0f}/100, overall {getattr(intel, 'overall_score', 0):.0f}/100",
        f"[Candidate Intelligence] learning velocity {getattr(intel, 'learning_velocity', 'n/a')}",
    ]
    if bundle.gap:
        evidence.append(f"[Skill Gap] JD skill match {bundle.gap.get('match_percent', 0)}%")
    return MemberOpinion(
        role="technical_hiring_manager",
        role_title="Technical Hiring Manager",
        recommendation=rec,
        confidence=float(getattr(intel, "confidence", 60.0)),
        opinion=(
            f"Technical readiness reads as {('strong' if score >= 70 else 'moderate' if score >= 50 else 'limited')} "
            f"({score:.0f}/100)."
        ),
        strengths=[s for s in getattr(intel, "strengths", [])][:3],
        concerns=[w for w in getattr(intel, "weaknesses", [])][:3],
        evidence=evidence,
        evidence_sources=["Candidate Intelligence engine", "Skill-gap analyzer"],
    )


def _risk_officer(bundle: EvidenceBundle, mode: CommitteeMode) -> MemberOpinion:
    """Risk Officer — reads Risk Intelligence (+ resume/JD risk signals)."""
    risk = bundle.risk
    if risk is None:
        return _abstain("risk_officer", "Risk Officer", "no risk report")
    level = getattr(risk, "risk_level", "Low")
    rec = _rec_from_risk(level)
    red_flags = list(getattr(risk, "red_flags", []))
    evidence = [
        f"[Risk Intelligence] risk level {level} (score {getattr(risk, 'risk_score', 0):.0f}/100)",
    ]
    for flag in red_flags[:3]:
        evidence.append(f"[Risk Intelligence] red flag: {flag}")
    if bundle.resume_analysis and bundle.resume_analysis.risk_report.findings:
        evidence.append(f"[Resume Analysis] resume risk {bundle.resume_analysis.risk_report.level}")
    return MemberOpinion(
        role="risk_officer",
        role_title="Risk Officer",
        recommendation=rec,
        confidence=80.0 if red_flags else 70.0,
        opinion=f"Hiring risk is {level}. "
        + ("Red flags require validation." if red_flags else "No blocking red flags."),
        strengths=list(getattr(risk, "positive_signals", []))[:3],
        concerns=red_flags[:4] or list(getattr(risk, "risk_factors", []))[:3],
        evidence=evidence,
        evidence_sources=["Risk Intelligence"],
    )


def _career_growth(bundle: EvidenceBundle, mode: CommitteeMode) -> MemberOpinion:
    """Career Growth Specialist — reads Timeline Intelligence."""
    tl = bundle.timeline
    if tl is None:
        return _abstain("career_growth", "Career Growth Specialist", "no timeline analysis")
    score = float(getattr(tl, "timeline_score", getattr(tl, "career_growth_score", 0.0)))
    rec = _rec_from_score(score)
    evidence = [
        f"[Timeline Intelligence] timeline score {score:.0f}/100",
        f"[Timeline Intelligence] {getattr(tl, 'promotion_count', 0)} promotion(s), stability {getattr(tl, 'career_stability', 'n/a')}",
    ]
    return MemberOpinion(
        role="career_growth",
        role_title="Career Growth Specialist",
        recommendation=rec,
        confidence=68.0,
        opinion=getattr(tl, "timeline_summary", "Career trajectory reviewed."),
        strengths=list(getattr(tl, "strengths", []))[:3],
        concerns=list(getattr(tl, "concerns", []))[:3],
        evidence=evidence,
        evidence_sources=["Career Timeline Intelligence"],
    )


def _interview_lead(bundle: EvidenceBundle, mode: CommitteeMode) -> MemberOpinion:
    """Interview Lead — reads the Interview plan + recommendation focus."""
    plan = bundle.interview_plan
    if plan is None:
        return _abstain("interview_lead", "Interview Lead", "no interview plan")
    validation = list(getattr(plan, "validation_questions", [])) + list(
        getattr(plan, "risk_followups", [])
    )
    # Many open validation items → hold pending interview; few → lean positive.
    if len(validation) >= 4:
        rec = Recommendation.HOLD
    elif len(validation) >= 2:
        rec = Recommendation.LEAN_HIRE
    else:
        rec = Recommendation.LEAN_HIRE
    topics = list(getattr(plan, "technical_topics", [])) + list(
        getattr(plan, "system_design_topics", [])
    )
    evidence = [
        f"[Interview Intelligence] {len(topics)} technical topic(s), {len(validation)} validation item(s)",
    ]
    for topic in topics[:2]:
        evidence.append(f"[Interview Intelligence] focus: {topic}")
    return MemberOpinion(
        role="interview_lead",
        role_title="Interview Lead",
        recommendation=rec,
        confidence=62.0,
        opinion=(
            f"Interview should validate {len(validation)} open item(s) before a final call."
            if validation
            else "Few open questions; interview is largely confirmatory."
        ),
        strengths=topics[:3],
        concerns=validation[:4],
        evidence=evidence,
        evidence_sources=["Interview Intelligence"],
    )


def _hiring_analyst(bundle: EvidenceBundle, mode: CommitteeMode) -> MemberOpinion:
    """Hiring Analyst — reads the Hiring Recommendation engine output."""
    rec_obj = bundle.recommendation
    if rec_obj is None:
        return _abstain("hiring_analyst", "Hiring Analyst", "no hiring recommendation")
    rec = _map_rec_string(getattr(rec_obj, "recommendation", ""))
    evidence = [
        f"[Hiring Recommendation] engine recommendation: {getattr(rec_obj, 'recommendation', 'n/a')} "
        f"({getattr(rec_obj, 'confidence', 0):.0f}% confidence)",
    ]
    for reason in list(getattr(rec_obj, "reasons", []))[:2]:
        evidence.append(f"[Hiring Recommendation] reason: {reason}")
    return MemberOpinion(
        role="hiring_analyst",
        role_title="Hiring Analyst",
        recommendation=rec,
        confidence=float(getattr(rec_obj, "confidence", 60.0)),
        opinion=(
            f"The recommendation engine reads this as '{getattr(rec_obj, 'recommendation', 'n/a')}'."
        ),
        strengths=list(getattr(rec_obj, "reasons", []))[:3],
        concerns=list(getattr(rec_obj, "concerns", []))[:3],
        evidence=evidence,
        evidence_sources=["Hiring Recommendation engine"],
    )


_PANEL = [
    CommitteeMember("resume_expert", "Resume Expert", "committee_review:resume", _resume_expert),
    CommitteeMember("jd_expert", "JD Expert", "committee_review:jd", _jd_expert),
    CommitteeMember(
        "technical_hiring_manager",
        "Technical Hiring Manager",
        "committee_review:technical",
        _technical_hiring_manager,
    ),
    CommitteeMember("risk_officer", "Risk Officer", "committee_review:risk", _risk_officer),
    CommitteeMember(
        "career_growth", "Career Growth Specialist", "committee_review:career", _career_growth
    ),
    CommitteeMember(
        "interview_lead", "Interview Lead", "committee_review:interview", _interview_lead
    ),
    CommitteeMember(
        "hiring_analyst", "Hiring Analyst", "committee_review:analyst", _hiring_analyst
    ),
]


def build_panel() -> list[CommitteeMember]:
    """Return the ordered committee panel (7 reviewing members; chair is separate)."""
    return list(_PANEL)
