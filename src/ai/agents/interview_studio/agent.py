"""InterviewStudioAgent — the Enterprise AI Interview Studio (Phase 4 / M5).

A specialized :class:`~src.ai.core.base_agent.BaseAgent` that produces the
:class:`InterviewStudioNarrative` from the aggregated intelligence TalentMind
already computed. It adds **no hiring logic and no ranking** — it consumes
existing structured outputs and restates them as an interview strategy
(Module 16).

Everything infrastructural (prompt rendering, provider calls, retries,
validation, safety, caching, telemetry, deterministic fallback) comes for free
from :class:`AgentRunner`; this module only supplies the evidence packing + the
identity.

On import it auto-registers with:
  * the AI Platform agent registry,
  * the deterministic composer registry (offline reasoning),
  * the Multi-Agent Orchestration registry (via a ``RunnerAgent`` adapter),
so the orchestrator and the Recruiter Copilot discover it with no manual wiring.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

from src.ai.core.base_agent import BaseAgent
from src.ai.core.metadata import AgentMetadata
from src.ai.core.registry import registry
from src.ai.prompts.loader import PromptLoader
from src.ai.providers.base import LLMMessage
from src.ai.providers.composers import register_composer

from src.ai.agents.interview_studio.composer import compose_interview_narrative
from src.ai.agents.interview_studio.schemas import InterviewStudioNarrative

# Prompts co-locate with the agent; a dedicated loader points at this package's
# ``prompts/`` dir, leaving the shared prompt library untouched.
_PROMPTS_DIR = os.path.join(os.path.dirname(__file__), "prompts")
_prompt_loader = PromptLoader(_PROMPTS_DIR)


@dataclass
class InterviewStudioInput:
    """Typed input for the InterviewStudioAgent.

    Every field is an existing engine/agent output, already normalized to a dict
    by the engine — the agent recomputes nothing. All are optional so the agent
    degrades gracefully when a source is missing (Module 16).

    Attributes:
        candidate_id: Stable id (used for caching + telemetry).
        role: The detected role key (drives the role-specific path).
        role_name: Human-readable role name (for the prompt / narrative).
        depth: Interview-depth key (screen / standard / deep).
        candidate_overview: ``{candidate_id, title, company, years, location}``.
        resume: Flattened ResumeAnalysis.
        jd: Flattened JDAnalysis.
        committee: ``CommitteeReport.to_dict()``.
        intelligence: ``CandidateIntelligence`` dict.
        timeline: ``CareerTimelineAnalysis`` dict.
        risk: ``RiskReport`` dict.
        recommendation: ``HiringRecommendation`` dict.
        interview: Deterministic ``InterviewPlan`` dict.
    """

    candidate_id: str = ""
    role: str = "generalist"
    role_name: str = "Software Engineer"
    depth: str = "standard"
    candidate_overview: Dict[str, Any] = field(default_factory=dict)
    resume: Dict[str, Any] = field(default_factory=dict)
    jd: Dict[str, Any] = field(default_factory=dict)
    committee: Dict[str, Any] = field(default_factory=dict)
    intelligence: Dict[str, Any] = field(default_factory=dict)
    timeline: Dict[str, Any] = field(default_factory=dict)
    risk: Dict[str, Any] = field(default_factory=dict)
    recommendation: Dict[str, Any] = field(default_factory=dict)
    interview: Dict[str, Any] = field(default_factory=dict)


def build_interview_evidence(payload: InterviewStudioInput) -> Dict[str, Any]:
    """Pack the pre-gathered structured outputs into the evidence dict.

    This is the sole factual input to the narrative: it contains only existing
    engine/agent outputs, nothing the AI is allowed to invent (Module 16).
    """
    return {
        "candidate_overview": payload.candidate_overview or {},
        "role": payload.role,
        "role_name": payload.role_name,
        "depth": payload.depth,
        "resume": payload.resume or {},
        "jd": payload.jd or {},
        "committee": payload.committee or {},
        "intelligence": payload.intelligence or {},
        "timeline": payload.timeline or {},
        "risk": payload.risk or {},
        "recommendation": payload.recommendation or {},
        "interview": payload.interview or {},
    }


class InterviewStudioAgent(BaseAgent):
    """Synthesizes existing intelligence into a personalized interview strategy."""

    metadata = AgentMetadata(
        name="interview_studio",
        version="v1",
        title="Interview Studio",
        description=(
            "Transforms every structured intelligence output TalentMind already "
            "produced — resume, JD, committee, intelligence, timeline, risk, "
            "interview plan and recommendation — into a complete, personalized "
            "interview plan: strategy, adaptive question flow, evaluation rubrics, "
            "interviewer guides, feedback templates and a decision matrix. "
            "Consumes existing outputs only; never re-ranks or invents."
        ),
        prompt_id="interview_studio",
        prompt_version="v1",
        tags=["interview", "studio", "questions", "rubric", "decision", "hiring-lifecycle"],
    )
    output_schema = InterviewStudioNarrative

    def build_messages(self, payload, loader, evidence: Dict[str, Any]) -> List[LLMMessage]:
        """Render prompts from the agent's own ``prompts/`` directory."""
        return super().build_messages(payload, _prompt_loader, evidence)

    def build_evidence(self, payload: InterviewStudioInput) -> Dict[str, Any]:
        """Return the aggregated interview evidence for ``payload``."""
        return build_interview_evidence(payload)

    def prompt_values(
        self, payload: InterviewStudioInput, evidence: Dict[str, Any]
    ) -> Dict[str, str]:
        """Supply candidate id + role/depth placeholders for the prompt."""
        return {
            "candidate_id": payload.candidate_id or "unknown",
            "role_name": payload.role_name or "Software Engineer",
            "depth": payload.depth or "standard",
        }

    def cache_dimensions(self, payload: InterviewStudioInput) -> Tuple[str, str]:
        """Cache by candidate id (subject) + evidence + role/depth (scope)."""
        scope = json.dumps(
            {
                "r": payload.role,
                "d": payload.depth,
                "e": build_interview_evidence(payload),
            },
            sort_keys=True,
            default=str,
        )
        return payload.candidate_id or "interview_studio", scope


def _orchestration_payload_builder(task, context) -> InterviewStudioInput:
    """Build an :class:`InterviewStudioInput` from an orchestration task + context."""
    payload = task.payload or {}
    overview = payload.get("candidate_overview") or {}
    if not overview and context is not None:
        candidate = getattr(context, "candidate", None)
        if candidate is not None:
            profile = getattr(candidate, "profile", None)
            overview = {
                "candidate_id": getattr(candidate, "candidate_id", ""),
                "title": getattr(profile, "current_title", ""),
                "company": getattr(profile, "current_company", ""),
                "years_of_experience": getattr(profile, "years_of_experience", 0.0),
                "location": getattr(profile, "location", ""),
            }
    return InterviewStudioInput(
        candidate_id=str(payload.get("candidate_id", "") or overview.get("candidate_id", "") or "interview_studio"),
        role=payload.get("role", "generalist"),
        role_name=payload.get("role_name", "Software Engineer"),
        depth=payload.get("depth", "standard"),
        candidate_overview=overview,
        resume=payload.get("resume", {}),
        jd=payload.get("jd", {}),
        committee=payload.get("committee", {}),
        intelligence=payload.get("intelligence", {}),
        timeline=payload.get("timeline", {}),
        risk=payload.get("risk", {}),
        recommendation=payload.get("recommendation", {}),
        interview=payload.get("interview", {}),
    )


def _register_with_orchestration(agent: "InterviewStudioAgent") -> None:
    """Register the agent with the Multi-Agent Orchestration platform (best-effort)."""
    try:
        from src.ai.orchestration.adapters import RunnerAgent
        from src.ai.orchestration.registry.agent_registry import orchestration_registry

        orchestration_registry.register(
            RunnerAgent(
                agent,
                capabilities=["interview_studio", "interview_plan", "interview_generation"],
                payload_builder=_orchestration_payload_builder,
                name="interview_studio",
            )
        )
    except Exception:  # orchestration optional; never block agent registration
        pass


# ---------------------------------------------------------------------------
# Auto-registration (import side effects — the platform discovers the agent)
# ---------------------------------------------------------------------------

register_composer(InterviewStudioNarrative.schema_name(), compose_interview_narrative)
interview_studio_agent = registry.register(InterviewStudioAgent())
_register_with_orchestration(interview_studio_agent)
