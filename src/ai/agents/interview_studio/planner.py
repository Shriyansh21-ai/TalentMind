"""Adaptive interview planning (Module 2).

Builds a personalized interview *roadmap* — the ordered stages, their objectives,
durations, interviewer and decision checkpoint — from the strategy, the role
profile and the aggregated evidence. The roadmap adapts to seniority (senior
loops add a dedicated architecture + leadership stage) and to the candidate's
own strengths/risks, so **no two candidates get the same generic loop**
(Module 2). Deterministic and offline.
"""

from __future__ import annotations

from typing import Any

from src.ai.agents.interview_studio.schemas import InterviewStage, InterviewStrategy
from src.ai.agents.interview_studio.templates import RoleProfile


def _focus_from_priorities(evidence: dict[str, Any], limit: int = 3) -> list[str]:
    """Return the top interview priorities to weave into stage focus."""
    committee = evidence.get("committee") or {}
    priorities = list((committee.get("decision") or {}).get("interview_priorities", []) or [])
    recommendation = evidence.get("recommendation") or {}
    priorities += list(recommendation.get("interview_focus", []) or [])
    return list(dict.fromkeys(p for p in priorities if p))[:limit]


def build_roadmap(
    evidence: dict[str, Any],
    strategy: InterviewStrategy,
    role: RoleProfile,
) -> list[InterviewStage]:
    """Assemble the adaptive interview roadmap (Module 2).

    Args:
        evidence: The aggregated interview evidence dict.
        strategy: The interview strategy (drives depth/length).
        role: The resolved role profile.

    Returns:
        An ordered list of :class:`InterviewStage`.
    """
    priorities = _focus_from_priorities(evidence)
    intelligence = evidence.get("intelligence") or {}
    top_strengths = list(intelligence.get("strengths") or [])[:2]
    has_risks = bool((evidence.get("risk") or {}).get("red_flags"))

    stages: list[InterviewStage] = []

    # 1) Always: recruiter / screening stage.
    stages.append(
        InterviewStage(
            name="Recruiter Screen",
            objective="Confirm motivation, logistics, comp alignment and a baseline signal.",
            duration_minutes=30 if strategy.depth != "screen" else 45,
            interviewer="Recruiter",
            focus=[
                "Motivation and role alignment",
                "Notice period / logistics",
                "Baseline depth check",
            ],
            checkpoint="Proceed only if motivation and baseline are credible.",
        )
    )

    if strategy.depth == "screen":
        # Fast path: a single technical signal check then decide.
        stages.append(
            InterviewStage(
                name="Technical Screen",
                objective=f"Fast depth check on {role.name} fundamentals.",
                duration_minutes=strategy.length_minutes - 45,
                interviewer=f"{role.name} (senior)",
                focus=(priorities or role.technical_focus[:2]) + top_strengths,
                checkpoint="Advance to the full loop only if depth is credible.",
            )
        )
        return stages

    # 2) Technical deep-dive.
    stages.append(
        InterviewStage(
            name="Technical Deep-Dive",
            objective=f"Verify {role.name} depth on proven skills and the role's stack.",
            duration_minutes=60,
            interviewer=f"{role.name} (senior)",
            focus=(priorities[:1] or [])
            + [f"Depth: {s}" for s in top_strengths]
            + role.technical_focus[:2],
            checkpoint="Proceed only if technical depth is confirmed.",
        )
    )

    # 3) Coding (skip for pure PM roles handled by role emphasis).
    stages.append(
        InterviewStage(
            name="Coding",
            objective="Assess correctness, code quality and reasoning under time pressure.",
            duration_minutes=60,
            interviewer=f"{role.name}",
            focus=role.coding_focus[:2] or ["Algorithmic problem", "Code quality and tests"],
            checkpoint="Calibrate the coding bar against the seniority.",
        )
    )

    # 4) System design (senior / design-heavy roles).
    if role.emphasize_system_design or strategy.depth == "deep":
        stages.append(
            InterviewStage(
                name="System Design",
                objective="Assess architecture maturity and trade-off reasoning at the right scope.",
                duration_minutes=60,
                interviewer="Staff / Principal Engineer",
                focus=role.system_design_focus[:3],
                checkpoint="Calibrate level (offer band) from design maturity.",
            )
        )

    # 5) Behavioral + (for senior/leadership) leadership stage.
    behavioral_focus = ["Ownership", "Collaboration", "Communication", "Failure & learning"]
    if role.emphasize_leadership or strategy.depth == "deep":
        stages.append(
            InterviewStage(
                name="Leadership & Behavioral",
                objective="Evaluate leadership, ownership, stakeholder management and collaboration.",
                duration_minutes=60,
                interviewer="Hiring Manager",
                focus=behavioral_focus + ["Leadership scope", "Stakeholder management"],
                checkpoint="Confirm collaboration and (where relevant) leadership scope.",
            )
        )
    else:
        stages.append(
            InterviewStage(
                name="Behavioral",
                objective="Evaluate ownership, collaboration, communication and growth.",
                duration_minutes=45,
                interviewer="Hiring Manager",
                focus=behavioral_focus,
                checkpoint="Confirm collaboration, communication and growth signals.",
            )
        )

    # 6) Risk validation stage only when the engines flagged material risk.
    if has_risks:
        stages.append(
            InterviewStage(
                name="Risk Validation",
                objective="Directly validate the risks the engines and committee flagged.",
                duration_minutes=30,
                interviewer="Bar Raiser",
                focus=[
                    f"Validate: {f}" for f in (evidence.get("risk") or {}).get("red_flags", [])[:3]
                ],
                checkpoint="Each flagged risk is either resolved or escalated with evidence.",
            )
        )

    # Final: debrief + decision.
    stages.append(
        InterviewStage(
            name="Debrief & Decision",
            objective="Evidence-based go / no-go against the rubric and decision matrix.",
            duration_minutes=30,
            interviewer="Full panel + Hiring Manager",
            focus=["Rubric roll-up", "Decision-matrix banding", "Committee alignment check"],
            checkpoint="Committee-style decision; escalate any contradiction with the committee.",
        )
    )

    return stages
