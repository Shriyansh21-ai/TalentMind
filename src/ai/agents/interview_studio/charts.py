"""Visualization data for the Interview Studio dashboard (Module 12).

Pure data builders (no plotting, no Streamlit import) that turn the assembled
package into chart-ready structures: an interview timeline, a competency-coverage
radar, a risk heatmap, a question-distribution breakdown and a decision-readiness
gauge. Keeping this pure makes it trivially testable and lets the UI render it
with any charting library. Numbers here are *coverage counts* and normalized
readiness — never hiring scores.
"""

from __future__ import annotations

from typing import Any

from src.ai.agents.interview_studio.schemas import (
    DecisionMatrix,
    InterviewQuestion,
    InterviewStage,
    InterviewStrategy,
    RiskValidation,
    RubricDimension,
)

# The competency axes the coverage radar reports on.
_RADAR_AXES = [
    "Technical Depth",
    "Architecture",
    "Coding",
    "Behavioral",
    "Leadership",
    "Role Fit",
    "Risk",
]

_RISK_LEVEL = {"high": 3, "medium": 2, "moderate": 2, "low": 1, "": 0, "none": 0}


def _coverage_radar(
    questions: list[InterviewQuestion], risks: list[RiskValidation]
) -> dict[str, int]:
    """Return question-count coverage per competency axis."""
    radar = {axis: 0 for axis in _RADAR_AXES}
    for q in questions:
        cat = q.category
        if cat in ("technical",):
            radar["Technical Depth"] += 1
        elif cat == "system_design":
            radar["Architecture"] += 1
        elif cat == "coding":
            radar["Coding"] += 1
        elif cat == "behavioral":
            radar["Behavioral"] += 1
        elif cat == "leadership":
            radar["Leadership"] += 1
        elif cat == "role":
            radar["Role Fit"] += 1
    radar["Risk"] = len(risks)
    return radar


def _risk_heatmap(evidence: dict[str, Any], risks: list[RiskValidation]) -> dict[str, int]:
    """Return a risk heatmap keyed by risk dimension -> severity (0-3)."""
    risk = evidence.get("risk") or {}
    heatmap = {
        "Job Hopping": _RISK_LEVEL.get(str(risk.get("job_hopping_risk", "")).lower(), 0),
        "Career Gaps": _RISK_LEVEL.get(
            str(risk.get("gap_risk", risk.get("employment_gap_risk", ""))).lower(), 0
        ),
        "Communication": _RISK_LEVEL.get(str(risk.get("communication_risk", "")).lower(), 0),
        "Overall": _RISK_LEVEL.get(str(risk.get("risk_level", "")).lower(), 0),
    }
    # Committee + timeline validations add a "Committee" axis.
    committee_risks = sum(1 for r in risks if r.category == "committee")
    heatmap["Committee Concerns"] = min(3, committee_risks)
    return heatmap


def _question_distribution(questions: list[InterviewQuestion]) -> dict[str, int]:
    """Return the count of questions per category."""
    dist: dict[str, int] = {}
    for q in questions:
        label = q.category.replace("_", " ").title()
        dist[label] = dist.get(label, 0) + 1
    return dist


def _difficulty_distribution(questions: list[InterviewQuestion]) -> dict[str, int]:
    """Return the count of questions per difficulty band."""
    order = ["Warm-up", "Core", "Deep", "Stretch"]
    dist = {d: 0 for d in order}
    for q in questions:
        dist[q.difficulty] = dist.get(q.difficulty, 0) + 1
    return dist


def _decision_readiness(
    evidence: dict[str, Any], questions: list[InterviewQuestion], risks: list[RiskValidation]
) -> float:
    """Return a 0-1 readiness gauge (coverage-based, NOT a hiring score)."""
    # Readiness = how well-prepared the loop is: has questions, has risk coverage,
    # has upstream evidence. Bounded to [0, 1].
    have_questions = 1.0 if questions else 0.0
    have_risk = 1.0 if risks else 0.0
    sources = sum(
        1
        for k in ("resume", "intelligence", "risk", "recommendation", "committee", "interview")
        if evidence.get(k)
    )
    coverage = min(1.0, sources / 6.0)
    return round((have_questions + have_risk + coverage) / 3.0, 3)


def _timeline(stages: list[InterviewStage]) -> list[dict[str, Any]]:
    """Return a cumulative timeline of stages for the Gantt-style view."""
    timeline: list[dict[str, Any]] = []
    start = 0
    for stage in stages:
        timeline.append(
            {
                "stage": stage.name,
                "start_minute": start,
                "duration_minutes": stage.duration_minutes,
                "end_minute": start + stage.duration_minutes,
            }
        )
        start += stage.duration_minutes
    return timeline


def build_chart_data(
    *,
    evidence: dict[str, Any],
    strategy: InterviewStrategy,
    stages: list[InterviewStage],
    questions: list[InterviewQuestion],
    rubrics: list[RubricDimension],
    risk_validations: list[RiskValidation],
    decision_matrix: DecisionMatrix,
) -> dict[str, Any]:
    """Build every chart structure for the Interview Studio dashboard (Module 12)."""
    return {
        "timeline": _timeline(stages),
        "coverage_radar": _coverage_radar(questions, risk_validations),
        "risk_heatmap": _risk_heatmap(evidence, risk_validations),
        "question_distribution": _question_distribution(questions),
        "difficulty_distribution": _difficulty_distribution(questions),
        "decision_readiness": _decision_readiness(evidence, questions, risk_validations),
        "rubric_weights": {d.name: d.weight for d in rubrics},
        "stage_count": len(stages),
        "total_minutes": sum(s.duration_minutes for s in stages),
    }
