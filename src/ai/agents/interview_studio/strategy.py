"""Interview strategy determination (Module 1).

Given the aggregated evidence (seniority, role fit, risk posture, committee
priorities), decide the interview *shape*: depth, length, stage count,
difficulty framing, objectives, priorities and decision checkpoints. Everything
here is a deterministic function of the existing engine outputs — no LLM, no I/O
and nothing invented (Modules 15 / 16).
"""

from __future__ import annotations

from typing import Any

from src.ai.agents.interview_studio.schemas import InterviewStrategy
from src.ai.agents.interview_studio.templates import DepthProfile, RoleProfile, get_depth

# Seniority thresholds (years) — mirror the deterministic interview planner.
SENIOR_YEARS = 8.0
MID_YEARS = 4.0


def _years(evidence: dict[str, Any]) -> float:
    """Return the candidate's years of experience from the overview."""
    ov = evidence.get("candidate_overview") or {}
    try:
        return float(ov.get("years_of_experience", 0.0) or 0.0)
    except (TypeError, ValueError):
        return 0.0


def choose_depth(evidence: dict[str, Any], role: RoleProfile) -> str:
    """Pick an interview-depth key from seniority + role.

    Leadership-heavy roles and senior candidates get the deep loop; everyone
    else gets the standard loop. (A recruiter can still override the depth.)
    """
    years = _years(evidence)
    if role.emphasize_leadership or years >= SENIOR_YEARS:
        return "deep"
    return "standard"


def _difficulty(evidence: dict[str, Any]) -> str:
    """Return a qualitative difficulty framing scaled to seniority + strength."""
    years = _years(evidence)
    intelligence = evidence.get("intelligence") or {}
    tech = intelligence.get("technical_score")
    strong = isinstance(tech, (int, float)) and tech >= 75
    if years >= SENIOR_YEARS:
        return (
            "Senior — architecture-heavy, high bar"
            if strong
            else "Senior — validate depth carefully"
        )
    if years >= MID_YEARS:
        return "Mid — solid depth with a stretch component"
    return "Early-career — fundamentals with growth signals"


def _objectives(evidence: dict[str, Any], role: RoleProfile) -> list[str]:
    """Interview objectives derived from role fit + evidence coverage."""
    objectives = [
        f"Confirm {role.name} depth against the role's mandatory requirements",
        "Validate the strengths this candidate's intelligence surfaced",
        "Probe the concerns and risks flagged by the engines",
    ]
    if role.emphasize_system_design:
        objectives.append("Assess system-design maturity at the right scope")
    if role.emphasize_leadership:
        objectives.append("Evaluate leadership, ownership and stakeholder management")
    objectives.append("Assess communication and collaboration under ambiguity")
    return objectives


def _priorities(evidence: dict[str, Any]) -> list[str]:
    """Interview priorities, committee-first then recommendation focus.

    The committee's interview priorities are authoritative when present; the
    recommendation engine's interview focus fills any gap. Never invented.
    """
    priorities: list[str] = []
    committee = evidence.get("committee") or {}
    priorities.extend((committee.get("decision") or {}).get("interview_priorities", []) or [])
    recommendation = evidence.get("recommendation") or {}
    priorities.extend(recommendation.get("interview_focus", []) or [])
    intelligence = evidence.get("intelligence") or {}
    priorities.extend(
        f"Probe development area: {w}" for w in (intelligence.get("weaknesses") or [])[:2]
    )
    # De-duplicate, preserve order, keep it scannable.
    return list(dict.fromkeys(p for p in priorities if p))[:6]


def _checkpoints(depth: DepthProfile) -> list[str]:
    """Decision checkpoints keyed to the loop's structure (Module 8 handoff)."""
    checkpoints = [
        "After the technical stage: proceed only if depth is confirmed",
        "After system design: calibrate level and offer band",
    ]
    if depth.stage_count >= 5:
        checkpoints.append("After behavioral/leadership: confirm collaboration and ownership")
    checkpoints.append("At debrief: evidence-based go / no-go against the rubric")
    return checkpoints


def build_strategy(
    evidence: dict[str, Any], role: RoleProfile, depth_key: str = ""
) -> InterviewStrategy:
    """Assemble the :class:`InterviewStrategy` for a candidate (deterministic).

    Args:
        evidence: The aggregated interview evidence dict.
        role: The resolved role profile.
        depth_key: Optional explicit depth override; auto-chosen when empty.

    Returns:
        A populated :class:`InterviewStrategy`.
    """
    depth_key = depth_key or choose_depth(evidence, role)
    depth = get_depth(depth_key)

    summary = (
        f"A {depth.name.lower()} for a {role.name} ({depth.length_minutes} min "
        f"across {depth.stage_count} stages). {depth.summary} Difficulty is "
        f"calibrated to the candidate's seniority; priorities follow the "
        f"committee and recommendation engines."
    )

    return InterviewStrategy(
        depth=depth.key,
        length_minutes=depth.length_minutes,
        stage_count=depth.stage_count,
        difficulty=_difficulty(evidence),
        objectives=_objectives(evidence, role),
        priorities=_priorities(evidence),
        decision_checkpoints=_checkpoints(depth),
        summary=summary,
    )
