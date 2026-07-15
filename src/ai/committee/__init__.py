"""AI Hiring Committee — enterprise multi-agent decision engine (Phase 4 / M3).

TalentMind's flagship capability: a panel of independent AI specialists that each
review the *already-computed* structured outputs of the existing engines, then
debate, reconcile disagreements and produce one transparent, evidence-backed
executive hiring decision.

It behaves like a real hiring committee — not a chain of prompts:

    gather evidence (cached) → independent reviews (parallel, via the
    orchestration WorkflowEngine) → discussion round → evidence-weighted
    consensus → conflict resolution → executive chair decision → memory.

It builds **no new infrastructure** and **modifies no engine**: it reuses the AI
Platform (runner, cache, telemetry, safety, structured output), the Multi-Agent
Orchestration framework (workflow engine, shared context, delegation, events,
memory, communication bus) and the existing agents' outputs.

Importing this package auto-registers the committee chair with the AI Platform
and the committee itself with the Orchestration registry; the Recruiter Copilot
discovers the ``hiring_committee`` tool automatically.
"""

from __future__ import annotations

from src.ai.committee.committee import (
    EvidenceBundle,
    HiringCommitteeEngine,
    gather_evidence,
    hiring_committee_engine,
)
from src.ai.committee.schemas import (
    CommitteeDecision,
    CommitteeMode,
    CommitteeReport,
    ConsensusLevel,
    Recommendation,
)

__all__ = [
    "HiringCommitteeEngine",
    "hiring_committee_engine",
    "EvidenceBundle",
    "gather_evidence",
    "CommitteeReport",
    "CommitteeDecision",
    "CommitteeMode",
    "ConsensusLevel",
    "Recommendation",
]
