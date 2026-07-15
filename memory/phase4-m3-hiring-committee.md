---
name: phase4-m3-hiring-committee
description: TalentMind Phase 4/M3 AI Hiring Committee — multi-agent decision engine at src/ai/committee
metadata:
  type: project
---

Phase 4 / Milestone 3 built the **AI Hiring Committee** (flagship) at
`src/ai/committee/`. Orchestrates existing structured outputs into a panel that
independently reviews → discusses → reaches evidence-weighted consensus →
resolves conflicts → executive chair decision. Builds NO new infra; modifies NO
engine. Non-obvious facts:

- **Genuine multi-agent, not prompt-chain:** the 7 member reviews run IN PARALLEL
  through the orchestration `WorkflowEngine` (`moderator.py`): each member wrapped
  as a `FunctionAgent`, one dependency-free task layer, `SharedContext` carries the
  `EvidenceBundle`, events → telemetry bridge. Members are deterministic reviewers
  (`members.py`, `build_panel()`), consume a slice of evidence, abstain if missing.
- **Consumes cached outputs only (never re-runs engines):** `gather_evidence()`
  runs ResumeAnalystAgent + JDAnalystAgent (AI-cached) + `insights_fn` (injected,
  session-cached candidate insights: intelligence/timeline/risk/recommendation) +
  `build_interview_plan`. All existing.
- **Consensus is evidence-weighted, NOT majority** (`voting.py`+`consensus.py`):
  weight = confidence×evidence_coverage×mode_mult; level from agreement_ratio +
  dispersion. Modes (balanced/optimistic/conservative) re-weight deterministically
  (fixed multipliers + ±0.25 bias) — no randomness.
- **Chair = BaseAgent** (`chair.py`, `committee_chair` in AI registry + composer);
  narrates/justifies the consensus, does NOT re-decide. Output `CommitteeDecision`
  is score-free top-level (safety guard). Own prompt dir. Engine falls back to the
  composer directly if the runner fails.
- **Registration:** chair→AI registry+composer; committee→orchestration registry
  (`hiring_committee` capability, FunctionAgent). `HiringCommitteeEngine.run(candidate,
  jd, mode)` → `CommitteeReport`. Memory: `CommitteeMemory` over
  `InMemoryOrchestrationMemory`.
- **Copilot (additive):** `Intent.HIRING_COMMITTEE` + patterns (committee/disagree/
  rejected/evidence supports/concerns remain) + `tool_selector` + `committee_tools.py`
  `HiringCommitteeTool` + narrator `_summarize_committee`. Added HIRING_COMMITTEE +
  RESUME_REVIEW to response_builder single_intents (offer candidate actions).
- **UI:** `src/ui/committee_tab.render_committee_workspace()` wired as 6th app.py
  workspace ("AI Hiring Committee"); consensus meter + opinion/conflict/decision/
  confidence tabs.

Tests: `pytest tests/ -p no:faulthandler` (adds test_committee.py + test_committee_ui.py).
See PHASE4_MILESTONE3_REPORT.md. Note: avoided non-ASCII "->" arrows in confidence
explanations (cp1252 console). [[phase4-m1-resume-agent]] [[phase4-m2-jd-agent]]
