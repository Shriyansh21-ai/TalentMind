"""ExecutiveHiringReportAgent — the Executive Decision Layer (Phase 4 / M4).

A specialized :class:`~src.ai.core.base_agent.BaseAgent` that produces the
one-page :class:`ExecutiveNarrative` from the aggregated intelligence TalentMind
already computed. It adds **no hiring logic and no ranking** — it consumes
existing structured outputs and restates them for executives (Module 16).

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
from typing import Any

from src.ai.agents.executive_report.composer import compose_executive_narrative
from src.ai.agents.executive_report.schemas import ExecutiveNarrative
from src.ai.core.base_agent import BaseAgent
from src.ai.core.metadata import AgentMetadata
from src.ai.core.registry import registry
from src.ai.prompts.loader import PromptLoader
from src.ai.providers.base import LLMMessage
from src.ai.providers.composers import register_composer

# Prompts co-locate with the agent; a dedicated loader points at this package's
# ``prompts/`` dir, leaving the shared prompt library untouched.
_PROMPTS_DIR = os.path.join(os.path.dirname(__file__), "prompts")
_prompt_loader = PromptLoader(_PROMPTS_DIR)


@dataclass
class ExecutiveReportInput:
    """Typed input for the ExecutiveHiringReportAgent.

    Every field is an existing engine/agent output, already normalized to a dict
    by the builder — the agent recomputes nothing. All are optional so the agent
    degrades gracefully when a source is missing (Module 16).

    Attributes:
        candidate_id: Stable id (used for caching + telemetry).
        template: The report template key (drives audience framing only).
        candidate_overview: ``{candidate_id, title, company, years, location}``.
        resume: Flattened ResumeAnalysis (executive_summary, quality, ...).
        jd: Flattened JDAnalysis (executive_summary, quality, ...).
        committee: ``CommitteeReport.to_dict()`` (consensus/decision/confidence).
        intelligence: ``CandidateIntelligence`` dict.
        timeline: ``CareerTimelineAnalysis`` dict.
        risk: ``RiskReport`` dict.
        recommendation: ``HiringRecommendation`` dict.
        interview: ``InterviewPlan`` dict.
        pipeline: Optional pipeline-status dict.
    """

    candidate_id: str = ""
    template: str = "executive"
    candidate_overview: dict[str, Any] = field(default_factory=dict)
    resume: dict[str, Any] = field(default_factory=dict)
    jd: dict[str, Any] = field(default_factory=dict)
    committee: dict[str, Any] = field(default_factory=dict)
    intelligence: dict[str, Any] = field(default_factory=dict)
    timeline: dict[str, Any] = field(default_factory=dict)
    risk: dict[str, Any] = field(default_factory=dict)
    recommendation: dict[str, Any] = field(default_factory=dict)
    interview: dict[str, Any] = field(default_factory=dict)
    pipeline: dict[str, Any] = field(default_factory=dict)


def build_executive_evidence(payload: ExecutiveReportInput) -> dict[str, Any]:
    """Pack the pre-gathered structured outputs into the evidence dict.

    This is the sole factual input to the narrative: it contains only existing
    engine/agent outputs, nothing the AI is allowed to invent (Module 16).
    """
    return {
        "candidate_overview": payload.candidate_overview or {},
        "resume": payload.resume or {},
        "jd": payload.jd or {},
        "committee": payload.committee or {},
        "intelligence": payload.intelligence or {},
        "timeline": payload.timeline or {},
        "risk": payload.risk or {},
        "recommendation": payload.recommendation or {},
        "interview": payload.interview or {},
        "pipeline": payload.pipeline or {},
        "template": payload.template,
    }


class ExecutiveHiringReportAgent(BaseAgent):
    """Synthesizes existing intelligence into a boardroom-grade executive narrative."""

    metadata = AgentMetadata(
        name="executive_hiring_report",
        version="v1",
        title="Executive Hiring Report",
        description=(
            "Transforms every structured intelligence output TalentMind already "
            "produced — resume, JD, committee, intelligence, timeline, risk, "
            "interview, recommendation — into an executive one-page hiring "
            "narrative. Consumes existing outputs only; never re-ranks or invents."
        ),
        prompt_id="executive_report",
        prompt_version="v1",
        tags=["executive", "report", "board", "synthesis", "decision-layer"],
    )
    output_schema = ExecutiveNarrative

    def build_messages(self, payload, loader, evidence: dict[str, Any]) -> list[LLMMessage]:
        """Render prompts from the agent's own ``prompts/`` directory."""
        return super().build_messages(payload, _prompt_loader, evidence)

    def build_evidence(self, payload: ExecutiveReportInput) -> dict[str, Any]:
        """Return the aggregated executive evidence for ``payload``."""
        return build_executive_evidence(payload)

    def prompt_values(
        self, payload: ExecutiveReportInput, evidence: dict[str, Any]
    ) -> dict[str, str]:
        """Supply candidate id + template placeholders for the prompt."""
        return {
            "candidate_id": payload.candidate_id or "unknown",
            "template": payload.template or "executive",
        }

    def cache_dimensions(self, payload: ExecutiveReportInput) -> tuple[str, str]:
        """Cache by candidate id (subject) + evidence + template signature (scope)."""
        scope = json.dumps(
            {"t": payload.template, "e": build_executive_evidence(payload)},
            sort_keys=True,
            default=str,
        )
        return payload.candidate_id or "executive_report", scope


def _orchestration_payload_builder(task, context) -> ExecutiveReportInput:
    """Build an :class:`ExecutiveReportInput` from an orchestration task + context."""
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
    return ExecutiveReportInput(
        candidate_id=str(
            payload.get("candidate_id", "")
            or overview.get("candidate_id", "")
            or "executive_report"
        ),
        template=payload.get("template", "executive"),
        candidate_overview=overview,
        resume=payload.get("resume", {}),
        jd=payload.get("jd", {}),
        committee=payload.get("committee", {}),
        intelligence=payload.get("intelligence", {}),
        timeline=payload.get("timeline", {}),
        risk=payload.get("risk", {}),
        recommendation=payload.get("recommendation", {}),
        interview=payload.get("interview", {}),
        pipeline=payload.get("pipeline", {}),
    )


def _register_with_orchestration(agent: ExecutiveHiringReportAgent) -> None:
    """Register the agent with the Multi-Agent Orchestration platform (best-effort)."""
    try:
        from src.ai.orchestration.adapters import RunnerAgent
        from src.ai.orchestration.registry.agent_registry import orchestration_registry

        orchestration_registry.register(
            RunnerAgent(
                agent,
                capabilities=["executive_report", "executive_hiring_report"],
                payload_builder=_orchestration_payload_builder,
                name="executive_hiring_report",
            )
        )
    except Exception:  # orchestration optional; never block agent registration
        pass


# ---------------------------------------------------------------------------
# Auto-registration (import side effects — the platform discovers the agent)
# ---------------------------------------------------------------------------

register_composer(ExecutiveNarrative.schema_name(), compose_executive_narrative)
executive_report_agent = registry.register(ExecutiveHiringReportAgent())
_register_with_orchestration(executive_report_agent)
