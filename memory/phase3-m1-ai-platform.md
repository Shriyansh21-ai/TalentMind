---
name: phase3-m1-ai-platform
description: TalentMind Phase 3/M1 AI Platform (src/ai) — provider-agnostic agent foundation, offline-by-default, first agent HiringAnalystAgent
metadata:
  type: project
---

Phase 3 / Milestone 1 added a reusable **AI Platform** at `src/ai/` that sits on
top of the deterministic engines (never modifies them). Key non-obvious facts:

- **Offline by default, zero deps.** Default provider is `local`
  (`LocalHeuristicProvider`) — a deterministic composer that restates the
  structured evidence, so the platform works with no API keys / no network. Real
  providers (openai/claude/gemini/ollama) import their SDK **lazily inside
  methods** and are chosen via `TALENTMIND_AI_PROVIDER`. This is why the app still
  boots without any LLM SDK and why tests run offline.
- **Structural safety.** The `HiringAnalysis` schema has NO numeric fields;
  `SafetyGuard.assert_schema_is_score_free` enforces "AI never computes scores".
  The composer maps the engine recommendation to the verdict, so the AI reflects
  (never contradicts) the deterministic engines.
- **Add an agent** = subclass `BaseAgent` (build_evidence / prompt_values /
  cache_dimensions) + score-free schema + two prompt templates in
  `src/ai/prompts/templates/{id}_system.v1.md` & `{id}_user.v1.md` +
  `register_composer(...)` + `registry.register(...)`. The `AgentRunner` handles
  prompts/providers/retries/validation/cache/telemetry/fallback generically.
- **UI:** new profile tab "🤖 AI Hiring Analyst" (`src/ui/ai_analyst_tab.py`),
  wired via `render_profile_tabs(..., insights=, jd=)` from `candidate_card.py`.
  Generation is on-demand only; `service.peek_cached_analysis` loads cached
  results without calling a provider (Module 11 — never runs during ranking).
  `app.py` was NOT modified.
- **Runtime artifacts** (gitignored): `data/ai_cache/`, `logs/ai_telemetry.jsonl`.
  Cache key = agent+version+prompt_version+provider+model+candidate_id+hash(jd).

Tests: `pytest tests/ -p no:faulthandler` → 60 passing (adds test_ai_platform.py,
test_ai_ui.py). See PHASE3_MILESTONE1_REPORT.md. Builds on [[phase2-m2-workspace]]
and the [[faiss-torch-import-order]] constraint.
