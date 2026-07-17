"""ResumeAnalystAgent — recruiter-grade resume intelligence (Modules 1-12, 16, 17).

A specialized :class:`~src.ai.core.base_agent.BaseAgent` built entirely on the
existing AI Platform: prompt loader, provider layer, cache, telemetry, safety and
structured output all come for free from :class:`AgentRunner`. This module only
adds *intelligence* — the deterministic resume analysis pipeline
(extractors → metrics → validators → composer) — never infrastructure.

On import it auto-registers with:
  * the AI Platform agent registry,
  * the deterministic composer registry (offline reasoning),
  * the Multi-Agent Orchestration registry (via a ``RunnerAgent`` adapter),
so the orchestrator and the Recruiter Copilot discover it with no manual wiring.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

from src.ai.agents.resume import extractors, validators
from src.ai.agents.resume import metrics as metrics_mod
from src.ai.agents.resume.composer import compose_resume_analysis
from src.ai.agents.resume.schemas import ResumeAnalysis
from src.ai.core.base_agent import BaseAgent
from src.ai.core.metadata import AgentMetadata
from src.ai.core.registry import registry
from src.ai.prompts.loader import PromptLoader
from src.ai.providers.base import LLMMessage
from src.ai.providers.composers import register_composer

# The agent's prompts live with the agent (Module architecture). A dedicated
# loader points at this package's ``prompts/`` dir; the shared prompt library is
# left untouched.
_PROMPTS_DIR = os.path.join(os.path.dirname(__file__), "prompts")
_prompt_loader = PromptLoader(_PROMPTS_DIR)


@dataclass
class ResumeAnalystInput:
    """Typed input for the ResumeAnalystAgent.

    Accepts a structured :class:`~src.models.candidates.Candidate` and/or raw
    resume text, so it works for the current dataset today and for future
    raw-resume ingestion (Module 15) without a schema change.

    Attributes:
        candidate_id: Stable id (used for caching + telemetry).
        candidate: The candidate record (optional if ``resume_text`` given).
        resume_text: Raw resume text (optional).
        jd: Optional job-description text used only for ATS keyword coverage
            (never for ranking).
    """

    candidate_id: str = ""
    candidate: Any = None
    resume_text: str = ""
    jd: str = ""


def build_resume_evidence(payload: ResumeAnalystInput) -> dict[str, Any]:
    """Run the deterministic pipeline and return the evidence dict.

    This is the sole factual input to the analysis: extracted document + computed
    metrics + evidence-backed risk findings. It contains nothing the AI is
    allowed to invent (Module 17).
    """
    doc = extractors.extract(
        payload.candidate,
        resume_text=payload.resume_text,
        candidate_id=payload.candidate_id,
    )
    metrics = metrics_mod.compute_metrics(doc, jd=payload.jd)
    risks = validators.detect_risks(doc, metrics)
    return {
        "document": doc.to_dict(),
        "metrics": metrics.to_dict(),
        "risks": [r.to_dict() for r in risks],
        "risk_level": validators.risk_level(risks),
        "positive_signals": validators.positive_signals(doc, metrics),
        "jd_present": bool(payload.jd),
    }


class ResumeAnalystAgent(BaseAgent):
    """Analyzes resume quality like a senior recruiter + career coach."""

    metadata = AgentMetadata(
        name="resume_analyst",
        version="v1",
        title="Resume Analyst",
        description=(
            "Recruiter-grade resume intelligence: structure, writing, technical "
            "depth, projects, achievements, ATS, career story and evidence-based "
            "risks — resume quality only, never hiring ranking."
        ),
        prompt_id="resume_analyst",
        prompt_version="v1",
        tags=["resume", "quality", "career-coach", "ats", "writing"],
    )
    output_schema = ResumeAnalysis

    def build_messages(self, payload, loader, evidence: dict[str, Any]) -> list[LLMMessage]:
        """Render prompts from the agent's own ``prompts/`` directory.

        Overrides the base to use this agent's dedicated loader instead of the
        shared prompt library, keeping the resume prompts co-located with the
        agent while reusing the platform's rendering machinery.
        """
        return super().build_messages(payload, _prompt_loader, evidence)

    def build_evidence(self, payload: ResumeAnalystInput) -> dict[str, Any]:
        """Return the deterministic resume evidence for ``payload``."""
        return build_resume_evidence(payload)

    def prompt_values(
        self, payload: ResumeAnalystInput, evidence: dict[str, Any]
    ) -> dict[str, str]:
        """Supply the candidate id + JD-context placeholders for the prompt."""
        return {
            "candidate_id": payload.candidate_id or "unknown",
            "jd_context": (payload.jd or "").strip() or "(no job description provided)",
        }

    def cache_dimensions(self, payload: ResumeAnalystInput) -> tuple[str, str]:
        """Cache by candidate id (subject) + a resume-content signature (scope)."""
        doc = evidence_signature(payload)
        return payload.candidate_id or "resume", doc


def evidence_signature(payload: ResumeAnalystInput) -> str:
    """Return a stable scope signature for caching a resume analysis."""

    doc = extractors.extract(
        payload.candidate, resume_text=payload.resume_text, candidate_id=payload.candidate_id
    )
    sig = {
        "summary": doc.summary,
        "skills": sorted(doc.skills),
        "experiences": [(e.title, e.company, e.start_date, e.end_date) for e in doc.experiences],
        "jd": (payload.jd or "")[:200],
    }
    return json.dumps(sig, sort_keys=True, default=str)


def _orchestration_payload_builder(task, context) -> ResumeAnalystInput:
    """Build a :class:`ResumeAnalystInput` from an orchestration task + context."""
    payload = task.payload or {}
    candidate = payload.get("candidate")
    if candidate is None and context is not None:
        candidate = getattr(context, "candidate", None)
    jd = payload.get("jd") or (getattr(context, "jd", "") if context is not None else "")
    return ResumeAnalystInput(
        candidate_id=str(
            payload.get("candidate_id", "") or getattr(candidate, "candidate_id", "") or "resume"
        ),
        candidate=candidate,
        resume_text=payload.get("resume_text", ""),
        jd=jd,
    )


def _register_with_orchestration(agent: ResumeAnalystAgent) -> None:
    """Register the agent with the Multi-Agent Orchestration platform (best-effort).

    Uses the ``RunnerAgent`` adapter so orchestration runs the agent through the
    same :class:`AgentRunner` (reusing cache/telemetry/safety). Failure to wire
    orchestration must never break the AI-platform agent, so this is defensive.
    """
    try:
        from src.ai.orchestration.adapters import RunnerAgent
        from src.ai.orchestration.registry.agent_registry import orchestration_registry

        orchestration_registry.register(
            RunnerAgent(
                agent,
                capabilities=["resume_analysis", "resume_review"],
                payload_builder=_orchestration_payload_builder,
                name="resume_analyst",
            )
        )
    except Exception:  # orchestration optional; never block agent registration
        pass


# ---------------------------------------------------------------------------
# Auto-registration (import side effects — the platform discovers the agent)
# ---------------------------------------------------------------------------

register_composer(ResumeAnalysis.schema_name(), compose_resume_analysis)
resume_analyst_agent = registry.register(ResumeAnalystAgent())
_register_with_orchestration(resume_analyst_agent)
