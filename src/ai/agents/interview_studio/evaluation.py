"""Live interview assistant (Module 9).

Real-time interviewer support: a notes template, a question checklist, an
evaluation checklist, risk reminders, follow-up suggestions and interview-timer
hooks. **No voice / AI-interviewer features** — the shape is deliberately stable
so Module 14 (Voice, AI Interviewer, Coding Sandbox, Video/Emotion Analysis,
Meeting Transcript) can plug in without a redesign. Deterministic, offline,
derived from the plan already generated (Module 16).
"""

from __future__ import annotations

from typing import Any, Dict, List

from src.ai.agents.interview_studio.schemas import (
    InterviewQuestion,
    InterviewStage,
    LiveInterviewAssistant,
    RiskValidation,
    RubricDimension,
)


def build_live_assistant(
    stages: List[InterviewStage],
    questions: List[InterviewQuestion],
    rubrics: List[RubricDimension],
    risk_validations: List[RiskValidation],
) -> LiveInterviewAssistant:
    """Assemble the live interviewer support hooks.

    Args:
        stages: The interview roadmap (drives the timer hooks).
        questions: Every generated question (drives the checklist).
        rubrics: Evaluation dimensions (drives the evaluation checklist).
        risk_validations: Risks to keep front-of-mind during the interview.

    Returns:
        A populated :class:`LiveInterviewAssistant`.
    """
    notes_template = [
        "Candidate + role + stage",
        "Question asked -> what they actually said (verbatim where possible)",
        "Evidence FOR the rubric dimensions",
        "Evidence AGAINST / gaps",
        "Follow-ups you still owe",
        "Preliminary band (Strong Hire / Hire / Hold / Reject) — revisit at the end",
    ]

    # Checklist: one line per planned question (capped so it stays scannable).
    question_checklist = [
        f"[{q.difficulty}] {q.competency}: {q.text}" for q in questions[:15]
    ]

    evaluation_checklist = [
        f"{d.name} ({d.weight}): {d.evidence_to_look_for[0] if d.evidence_to_look_for else d.description}"
        for d in rubrics
    ]

    risk_reminders = [
        f"[{rv.category}] {rv.risk} -> ask: {rv.validation_question}"
        for rv in risk_validations[:6]
    ]

    followup_suggestions = [
        "If an answer is vague, ask for a specific example with numbers.",
        "If they describe team work, isolate THEIR personal contribution.",
        "If a claim is high-level, drill one level deeper to test real depth.",
        "If a risk answer is evasive, restate the concern and ask directly.",
    ]

    # Timer hooks: cumulative minute marks for each stage (Module 9 / 14 hook).
    timer_hooks: List[Dict[str, Any]] = []
    elapsed = 0
    for stage in stages:
        timer_hooks.append(
            {
                "at_minute": elapsed,
                "stage": stage.name,
                "duration_minutes": stage.duration_minutes,
                "checkpoint": stage.checkpoint,
            }
        )
        elapsed += stage.duration_minutes
    timer_hooks.append({"at_minute": elapsed, "stage": "Wrap-up", "duration_minutes": 0,
                        "checkpoint": "Leave time for the candidate's questions; finalize notes."})

    return LiveInterviewAssistant(
        interviewer_notes_template=notes_template,
        question_checklist=question_checklist,
        evaluation_checklist=evaluation_checklist,
        risk_reminders=risk_reminders,
        followup_suggestions=followup_suggestions,
        timer_hooks=timer_hooks,
    )
