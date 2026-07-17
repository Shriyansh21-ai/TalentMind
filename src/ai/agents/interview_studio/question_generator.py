"""Adaptive question generation (Modules 3, 4, 5, 6).

Turns the existing structured intelligence into personalized interview
questions. Nothing is invented: every question is derived from the deterministic
interview plan, the candidate-intelligence strengths/weaknesses, the role
profile, or the risk/committee findings, and every question records the source
it traces back to (Module 16). Difficulty progresses Warm-up -> Core -> Deep ->
Stretch so the flow adapts to the candidate's seniority.

Four generators:
  * :func:`technical_questions` — coding / architecture / system-design / role
    stack (Module 3), enriched by the role profile (Module 5).
  * :func:`behavioral_questions` — leadership, ownership, conflict, growth
    (Module 4).
  * :func:`role_specific_questions` — the specialized competencies for the
    detected role (Module 5).
  * :func:`risk_validations` — resume / timeline / committee risks converted
    into validation questions with expected evidence + pass criteria (Module 6).
"""

from __future__ import annotations

from typing import Any

from src.ai.agents.interview_studio.schemas import InterviewQuestion, RiskValidation
from src.ai.agents.interview_studio.templates import RoleProfile

# Seniority thresholds (years) — align with the deterministic interview planner.
SENIOR_YEARS = 8.0
MID_YEARS = 4.0
STRONG_TECH = 75.0

_MAX_PER_SECTION = 10


def _years(evidence: dict[str, Any]) -> float:
    ov = evidence.get("candidate_overview") or {}
    try:
        return float(ov.get("years_of_experience", 0.0) or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _difficulty_ladder(years: float) -> list[str]:
    """Return the difficulty progression appropriate to seniority (Module 3)."""
    if years >= SENIOR_YEARS:
        return ["Core", "Deep", "Deep", "Stretch"]
    if years >= MID_YEARS:
        return ["Warm-up", "Core", "Deep", "Stretch"]
    return ["Warm-up", "Warm-up", "Core", "Deep"]


def _plan(evidence: dict[str, Any]) -> dict[str, Any]:
    """Return the deterministic interview-plan dict (never recomputed)."""
    return evidence.get("interview") or {}


# ---------------------------------------------------------------------------
# Module 3 — Technical interview
# ---------------------------------------------------------------------------


def technical_questions(evidence: dict[str, Any], role: RoleProfile) -> list[InterviewQuestion]:
    """Generate the technical question set (coding, architecture, system design)."""
    years = _years(evidence)
    ladder = _difficulty_ladder(years)
    plan = _plan(evidence)
    intelligence = evidence.get("intelligence") or {}
    tech_score = intelligence.get("technical_score")
    strong = isinstance(tech_score, (int, float)) and tech_score >= STRONG_TECH

    questions: list[InterviewQuestion] = []

    # 1) Depth on the candidate's proven skills (from the interview plan).
    for i, topic in enumerate((plan.get("technical_topics") or [])[:4]):
        questions.append(
            InterviewQuestion(
                text=f"Walk me through your hands-on work on: {topic}.",
                competency="Technical depth",
                category="technical",
                difficulty=ladder[min(i, len(ladder) - 1)],
                expected_answer=(
                    "Concrete, first-person detail: what they built, the trade-offs "
                    "they weighed, and the measurable outcome."
                ),
                evaluation_criteria=[
                    "Specific personal contribution (not team-level generalities)",
                    "Sound trade-off reasoning",
                    "Depth proportional to the seniority claimed",
                ],
                signals=["Depth", "Ownership", "Trade-off reasoning"],
                source="Interview Intelligence (technical_topics)",
            )
        )

    # 2) Role-specific technical focus (Module 5 enrichment).
    for i, topic in enumerate(role.technical_focus[:3]):
        questions.append(
            InterviewQuestion(
                text=f"{topic} — how have you approached this, and where did it break down?",
                competency=f"{role.name} core",
                category="technical",
                difficulty="Deep" if strong else "Core",
                expected_answer="Role-appropriate depth with a real example of a failure and the fix.",
                evaluation_criteria=[
                    f"Command of {role.name.lower()} fundamentals",
                    "Learns from failure; can articulate the fix",
                ],
                signals=["Role fit", "Depth"],
                source=f"Role profile: {role.name}",
            )
        )

    # 3) System design (scaled to seniority + role emphasis).
    if role.emphasize_system_design or years >= MID_YEARS:
        design_topics = (plan.get("system_design_topics") or []) or role.system_design_focus
        for topic in design_topics[:3]:
            questions.append(
                InterviewQuestion(
                    text=f"System design: {topic}",
                    competency="Architecture",
                    category="system_design",
                    difficulty="Stretch" if years >= SENIOR_YEARS else "Deep",
                    expected_answer=(
                        "A structured design: clarify requirements, sketch components, "
                        "reason about scale, trade-offs and failure modes."
                    ),
                    evaluation_criteria=[
                        "Clarifies requirements before designing",
                        "Right scope for the seniority",
                        "Reasons about trade-offs, scale and failure",
                    ],
                    signals=["Architecture", "Scale reasoning", "Communication"],
                    source="Interview Intelligence (system_design_topics)",
                )
            )

    # 4) Coding round (calibrated to demonstrated strength + role).
    coding = (plan.get("coding_focus") or []) or role.coding_focus
    for topic in coding[:2]:
        questions.append(
            InterviewQuestion(
                text=f"Coding: {topic}",
                competency="Coding",
                category="coding",
                difficulty="Deep" if strong else "Core",
                expected_answer="Correct, readable solution with edge-case handling and clear reasoning.",
                evaluation_criteria=[
                    "Correctness and edge-case handling",
                    "Code quality and readability",
                    "Communicates reasoning while coding",
                ],
                signals=["Coding", "Problem solving", "Communication"],
                source="Interview Intelligence (coding_focus)",
            )
        )

    return questions[:_MAX_PER_SECTION]


# ---------------------------------------------------------------------------
# Module 4 — Behavioral interview
# ---------------------------------------------------------------------------

# Standard behavioral competencies (Module 4). Each maps to an evaluation signal.
_BEHAVIORAL_BANK = [
    (
        "Ownership",
        "Tell me about a time you took ownership beyond your assigned scope. What happened?",
        ["Proactivity", "Accountability"],
    ),
    (
        "Conflict resolution",
        "Describe a serious disagreement with a colleague and how you resolved it.",
        ["Empathy", "Directness", "Outcome"],
    ),
    (
        "Decision making",
        "Walk me through a hard decision you made with incomplete information.",
        ["Judgment", "Reasoning under ambiguity"],
    ),
    (
        "Stakeholder management",
        "How have you managed conflicting priorities from different stakeholders?",
        ["Influence", "Prioritization"],
    ),
    (
        "Communication",
        "Tell me about a time you had to explain something complex to a non-technical audience.",
        ["Clarity", "Audience awareness"],
    ),
    (
        "Failure & learning",
        "Describe a project that failed or went badly. What did you learn?",
        ["Self-awareness", "Growth"],
    ),
    (
        "Career motivation",
        "What are you looking for next, and why this role specifically?",
        ["Motivation", "Role alignment"],
    ),
]

_LEADERSHIP_BANK = [
    (
        "Team building",
        "Describe a team you built or grew and the outcomes you drove.",
        ["People leadership", "Results"],
    ),
    (
        "Mentoring",
        "How do you develop and mentor the engineers who report to you?",
        ["Coaching", "Growth mindset"],
    ),
    (
        "Hard people decision",
        "Tell me about a difficult people decision you had to make.",
        ["Judgment", "Courage"],
    ),
    (
        "Technical direction",
        "How do you set and align technical direction across teams?",
        ["Vision", "Alignment"],
    ),
]


def behavioral_questions(evidence: dict[str, Any], role: RoleProfile) -> list[InterviewQuestion]:
    """Generate behavioral + leadership questions, tailored by the evidence."""
    intelligence = evidence.get("intelligence") or {}
    leadership = intelligence.get("leadership_score")
    strong_leader = isinstance(leadership, (int, float)) and leadership >= 70

    questions: list[InterviewQuestion] = []
    for competency, text, signals in _BEHAVIORAL_BANK:
        questions.append(
            InterviewQuestion(
                text=text,
                competency=competency,
                category="behavioral",
                difficulty="Core",
                expected_answer="A structured STAR answer with a specific, first-person example and a clear outcome.",
                evaluation_criteria=[
                    "Concrete situation and personal role (STAR)",
                    "Reflection and what changed afterwards",
                ],
                signals=list(signals),
                source="Behavioral competency framework",
            )
        )

    # Leadership depth scales with the leadership signal and role emphasis.
    if role.emphasize_leadership or strong_leader:
        for competency, text, signals in _LEADERSHIP_BANK:
            questions.append(
                InterviewQuestion(
                    text=text,
                    competency=competency,
                    category="leadership",
                    difficulty="Deep",
                    expected_answer="Evidence of real leadership scope with outcomes and lessons.",
                    evaluation_criteria=[
                        "Demonstrated scope of leadership",
                        "Outcomes and how they measured success",
                    ],
                    signals=list(signals),
                    source="Candidate Intelligence (leadership signal)"
                    if strong_leader
                    else f"Role profile: {role.name}",
                )
            )

    # Tailor by weaknesses the intelligence engine surfaced (probe, don't invent).
    for weakness in (intelligence.get("weaknesses") or [])[:2]:
        questions.append(
            InterviewQuestion(
                text=f"Tell me about how you've handled a situation involving: {weakness}.",
                competency="Development area",
                category="behavioral",
                difficulty="Deep",
                expected_answer="Honest, specific reflection showing awareness and progress on the flagged area.",
                evaluation_criteria=["Self-awareness", "Evidence of active improvement"],
                signals=["Self-awareness", "Growth"],
                source="Candidate Intelligence (weaknesses)",
            )
        )

    return questions[:_MAX_PER_SECTION]


# ---------------------------------------------------------------------------
# Module 5 — Role-specific interview
# ---------------------------------------------------------------------------


def role_specific_questions(evidence: dict[str, Any], role: RoleProfile) -> list[InterviewQuestion]:
    """Generate questions for the role's specialized competencies (Module 5)."""
    years = _years(evidence)
    questions: list[InterviewQuestion] = []
    for competency in role.competencies:
        questions.append(
            InterviewQuestion(
                text=f"For a {role.name}: give me a concrete example that demonstrates your strength in {competency}.",
                competency=competency,
                category="role",
                difficulty="Deep" if years >= SENIOR_YEARS else "Core",
                expected_answer=f"A specific, role-relevant example that clearly exercises {competency.lower()}.",
                evaluation_criteria=[
                    f"Genuine command of {competency.lower()}",
                    "Example is relevant to this role's day-to-day",
                ],
                signals=[competency, "Role fit"],
                source=f"Role profile: {role.name}",
            )
        )
    return questions[:_MAX_PER_SECTION]


# ---------------------------------------------------------------------------
# Module 6 — Risk validation
# ---------------------------------------------------------------------------


def _pass_criteria(risk_text: str) -> str:
    """Return a generic, evidence-based pass criterion for a validation."""
    return (
        "Pass if the candidate provides specific, verifiable detail that resolves "
        "the concern; flag if the answer is vague, evasive or inconsistent with the resume."
    )


def risk_validations(evidence: dict[str, Any]) -> list[RiskValidation]:
    """Convert resume / timeline / committee risks into validation questions.

    Implements the mandated chain (Module 6):
    Risk -> Validation Question -> Expected Evidence -> Pass Criteria.
    """
    validations: list[RiskValidation] = []
    seen: set = set()

    def _add(
        risk: str, category: str, source: str, question: str = "", evidence_txt: str = ""
    ) -> None:
        key = (risk or "").strip().lower()
        if not key or key in seen:
            return
        seen.add(key)
        validations.append(
            RiskValidation(
                risk=risk,
                category=category,
                validation_question=question or f"Help me understand the context behind: {risk}.",
                expected_evidence=evidence_txt
                or "A concrete, verifiable explanation consistent with the resume and timeline.",
                pass_criteria=_pass_criteria(risk),
                source=source,
            )
        )

    risk = evidence.get("risk") or {}
    # Explicit validation questions the risk engine already produced.
    for q in (risk.get("validation_questions") or [])[:4]:
        _add(
            q,
            "resume",
            "Resume Risk Detection",
            question=q,
            evidence_txt="Direct, specific answer that substantiates the claim in question.",
        )
    for flag in (risk.get("red_flags") or [])[:4]:
        _add(
            flag,
            "resume",
            "Resume Risk Detection",
            question=f"I want to give you a chance to address a flag we noticed: {flag}. What's the context?",
        )
    for factor in (risk.get("risk_factors") or [])[:3]:
        _add(factor, "resume", "Resume Risk Detection")

    # Timeline risks (gaps, job hopping, short tenures).
    timeline = evidence.get("timeline") or {}
    for concern in (timeline.get("risk_factors") or timeline.get("concerns") or [])[:3]:
        _add(concern, "timeline", "Career Timeline Intelligence")

    # Committee-flagged risks and remaining unknowns.
    committee = evidence.get("committee") or {}
    decision = committee.get("decision") or {}
    for hr in (decision.get("hiring_risks") or [])[:3]:
        _add(hr, "committee", "AI Hiring Committee")
    for unknown in (decision.get("remaining_unknowns") or [])[:3]:
        _add(
            unknown,
            "committee",
            "AI Hiring Committee",
            question=f"The committee left one thing open: {unknown}. Can you close the loop for us?",
            evidence_txt="Evidence that resolves the open question the committee identified.",
        )

    # Recommendation-engine concerns.
    recommendation = evidence.get("recommendation") or {}
    for concern in (recommendation.get("concerns") or [])[:3]:
        _add(concern, "recommendation", "Hiring Recommendation engine")

    if not validations:
        validations.append(
            RiskValidation(
                risk="No material risks surfaced",
                category="resume",
                validation_question="Confirm scope and personal contribution on the key projects listed.",
                expected_evidence="Consistent, specific detail matching the resume.",
                pass_criteria="Pass if the baseline claims hold up under light probing.",
                source="Resume Risk Detection",
            )
        )
    return validations[:_MAX_PER_SECTION]
