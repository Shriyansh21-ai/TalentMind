---
name: phase5-m5-hiring-intelligence
description: TalentMind Phase 5/M5 HiringIntelligenceAgent — org-level workforce analytics at src/ai/agents/hiring_intelligence
metadata:
  type: project
---

Phase 5 / Milestone 5 (final) built the **Enterprise Workforce Hiring Intelligence
System** at `src/ai/agents/hiring_intelligence/`. FIRST org-level agent (all prior
agents were per-candidate). NOT BI/reporting/dashboards. Strategic org intelligence,
NEVER individual ranking. Non-obvious facts:

- **Cohort-based, not per-candidate:** `HiringIntelligenceEngine.build(candidates=...,
  repository=..., limit=ANALYTICS_COHORT=25)`. Aggregates via the CHEAP cached
  `insights_fn` per candidate (intelligence/risk/recommendation/timeline) — does NOT
  run the heavy governance chain per member (perf, Module 14). `build_cohort_snapshots`
  → per-candidate dict; `build_distributions` = Module 1.
- **Data-gated honesty (Module 15):** org-wide event data (trends/delays/dept-BU/
  capacity) is NOT persisted → all trends Unavailable, timing bottlenecks Unavailable,
  dept/BU/hiring-manager/recruiter team metrics Unavailable, governance/transparency/
  compliance/audit KPIs Unavailable (null value), UNLESS a `WorkforceDataProvider`
  (Protocol + `NullWorkforceDataProvider` default in analytics_engine.py;
  get_trends/get_team_metrics/get_capacity) is injected. Observed = cohort-derived
  (recommendation/risk/role/location distributions, hiring-health/interview/strategic
  KPIs, role/location team health, benchmarks). Estimated = cohort heuristics
  (risk-validation + interview bottlenecks). Forecast = scenario scaling (never certain).
- **Import-cycle fix:** shared helpers (`hiring_health_label`, `share`, `is_positive`,
  `role_family_of`) live in analytics_engine.py; leaf modules import them at top;
  the engine imports leaf modules LAZILY inside build() to break the cycle.
- **Score-free schema:** `WorkforceNarrative` (BaseAIResponse); KPI/numbers in nested
  dataclasses. KPI.value is None when register==Unavailable (asserted by validators +
  test).
- **Never ranks individuals:** report exposes aggregates only (test asserts no
  candidate-ranking surface).
- **Copilot tool is ORG-LEVEL (no candidate_id):** `hiring_intelligence_tools.py`
  validate() returns None; planner `_input_for` returns `{}`; NOT in response_builder
  single_intents (no candidate actions). Cohort bounded to 15 for copilot.
- **Recommendation labels contain non-ASCII stars** ("★☆☆☆☆ Reject") from the existing
  recommendation engine — safe in JSON persistence (ensure_ascii) + Streamlit; don't
  print raw to cp1252 console.
- **Auto-registration on import of agent.py:** AI registry (`hiring_intelligence`) +
  composer + orchestration (RunnerAgent). Own prompt loader.
- **Copilot (additive):** NEW `Intent.HIRING_INTELLIGENCE`. Patterns coexist with all
  prior intents ("how healthy is our hiring", "hiring analytics", "bottlenecks",
  "workforce report", "hiring trends", "which departments"); "dashboard distribution"
  stays DASHBOARD_QUESTION. narrator + follow-ups.
- **UI:** `src/ui/hiring_intelligence_tab.render_hiring_intelligence_workspace()` wired
  as 13th app.py workspace ("Hiring Intelligence"); cohort-size slider, 11 tabs.

Tests: `pytest tests/ -p no:faulthandler` → 444 (adds test_hiring_intelligence.py=30,
test_hiring_intelligence_ui.py=2). See PHASE5_MILESTONE5_REPORT.md. COMPLETES Phase 5
governance/intelligence stack: Compensation → Pay Equity → Compliance → Audit →
Hiring Intelligence.
