---
name: phase4-m1-resume-agent
description: TalentMind Phase 4/M1 ResumeAnalystAgent — first specialized business agent at src/ai/agents/resume
metadata:
  type: project
---

Phase 4 / Milestone 1 built the **ResumeAnalystAgent** — the first specialized
business agent — at `src/ai/agents/resume/`, on top of the AI Platform
([[phase3-m1-ai-platform]]) and orchestration ([[phase3-m3-orchestration]]).
Resume *quality* analysis only; never ranks candidates. Non-obvious facts:

- **Score-free constraint:** the AI platform `SafetyGuard.assert_schema_is_score_free`
  HARD-rejects any TOP-LEVEL output field containing `score`/`rating`/`percent`/
  `confidence_value`. So `ResumeAnalysis` keeps all numeric dims in the nested
  `ResumeQuality` model (overall/structure/writing/technical_depth/... 0-100).
  Any new scored agent must do the same.
- **Pipeline (all deterministic, offline-safe):** `extractors.py` (Candidate/raw
  text → `ResumeDocument`) → `metrics.py` (quality dims + tech/ATS/achievement
  facts) → `validators.py` (evidence-only risk findings) → `build_evidence` dict
  → `composer.py`+`report.py` restate evidence into `ResumeAnalysis`. Composer is
  registered via `register_composer` for the offline `local` provider. Evidence =
  facts only; composer never invents (Module 17 safety).
- **Prompts live with the agent** at `src/ai/agents/resume/prompts/` — the agent
  overrides `build_messages` to use its own `PromptLoader(_PROMPTS_DIR)` instead
  of the shared template dir.
- **Auto-registration on import of agent.py:** AI registry (`resume_analyst`) +
  composer + orchestration registry (via `RunnerAgent` adapter, capabilities
  `["resume_analysis","resume_review"]`). `resume_tools.py` imports the agent at
  module top so importing `tools.builtin` registers everything.
- **Copilot integration (additive, no manual routing):** new `Intent.RESUME_REVIEW`
  + planner keyword patterns (resume/cv/ats/weak/improve) + `tool_selector` entry
  → `resume_analysis` tool (`tools/resume_tools.py`, wraps agent via AgentRunner)
  + narrator summarizer/lead in `agents/recruiter_copilot.py`.
- **UI:** `src/ui/resume_intelligence_tab.render_resume_intelligence(candidate, jd)`
  + `render_resume_workspace(repo_factory)`, wired as 4th app.py workspace
  ("Resume Intelligence"). On-demand run with cache peek.

Tests: `pytest tests/ -p no:faulthandler` → 150 passing (adds test_resume_agent.py
+ test_resume_ui.py, offline AppTest via `AppTest.from_string`). See
PHASE4_MILESTONE1_REPORT.md.
