---
name: phase4-m2-jd-agent
description: TalentMind Phase 4/M2 JDAnalystAgent — second business agent at src/ai/agents/jd
metadata:
  type: project
---

Phase 4 / Milestone 2 built the **JDAnalystAgent** — the second specialized
business agent — at `src/ai/agents/jd/`, mirroring the ResumeAnalystAgent
([[phase4-m1-resume-agent]]). Understands a Job Description (role level, technical
shape, hiring intent, org context, requirement hierarchy, market, quality, risk);
JD *quality* only, never candidate ranking. Non-obvious facts:

- **Same score-free constraint** as the resume agent: numeric dims live in nested
  `JDQuality` (overall/structure/technical_clarity/role_clarity/requirement_quality/
  business_context/hiring_readiness/market_alignment/organization_clarity).
- **Pipeline:** `extractors.py` (raw JD text → `JDDocument`, section-header-aware,
  degrades to whole-body pool) → `metrics.py` (tech taxonomy + dims + offline
  market heuristics) → `validators.py` (evidence-only risks) → `report.py`
  (role/hiring-intent/org/requirement-hierarchy builders, every inference carries
  confidence) → `composer.py`. Input is `JDAnalystInput(jd_text, jd_id, title)`;
  cached by sha256(jd_text).
- **Tech matching bug fixed:** `metrics._present` uses TOKEN-boundary matching
  (with `+term+"s"` plural tolerance) so "scalable" doesn't match language "scala".
  Phrases / special-char techs (c++, ci/cd, node.js) still use substring.
- **Auto-registration on import of agent.py:** AI registry (`jd_analyst`) +
  composer + orchestration registry (RunnerAgent, capabilities `["jd_analysis",
  "jd_review"]`). Own prompt loader at `src/ai/agents/jd/prompts/`.
- **Copilot (additive):** `Intent.JD_ANALYSIS` + planner patterns (job description/
  this jd/what level/mandatory/realistic) + `tool_selector` + planner `_input_for`
  returns `{}` for jd_analysis (JD read from `ToolContext.jd`) + `jd_tools.py`
  `JDAnalysisTool` + narrator summarizer/lead. Existing + resume intents unchanged.
- **UI:** `src/ui/jd_intelligence_tab.render_jd_workspace()` wired as 5th app.py
  workspace ("JD Intelligence"); paste-a-JD → dashboard.
- **Module 15 cross-agent:** `src/ai/agents/analysis_interfaces.py` — extension
  points only (AnalysisProvider Protocol + CombinedAnalysisInputs), NO comparison
  logic. Resume & JD agents stay independent (no cross-import).

Tests: `pytest tests/ -p no:faulthandler` (adds test_jd_agent.py + test_jd_ui.py).
See PHASE4_MILESTONE2_REPORT.md.
