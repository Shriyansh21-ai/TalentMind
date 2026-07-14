# TalentMind — Phase 3 / Milestone 1 Report
## AI Platform Foundation

**Status:** ✅ Complete and verified — the app boots (Streamlit `AppTest`), all
imports resolve, the AI Platform is fully integrated, the **HiringAnalystAgent**
works end-to-end **offline with zero API keys**, and there are **no regressions**
(60 automated tests passing).

This milestone adds a reusable, provider-agnostic **AI Platform** that sits *on
top* of the existing deterministic engines. It is a reasoning layer, not a
chatbot and not a prompt wrapper: every future intelligent module plugs into the
same core. The first agent (HiringAnalystAgent) proves the platform works.

---

## 1. Guiding principles

- **Extend, never rewrite.** No ranking, scoring, or recommendation formula was
  touched. The AI layer *consumes* structured intelligence; it never produces a
  score. This is enforced *structurally* — the response schema has no numeric
  fields and the safety guard fails fast if one is ever added.
- **Provider independence.** The application never imports a vendor SDK. All
  provider SDKs are imported lazily, only when a provider is actually selected
  and used. The default provider is **offline and deterministic**, so the
  platform runs with no keys, no network, and no new hard dependencies.
- **Minimal boilerplate for new agents.** A new agent implements three small
  hooks and registers a deterministic composer; the runner handles everything
  cross-cutting (prompts, providers, retries, validation, safety, cache,
  telemetry, fallback).
- **SOLID / DRY / KISS.** Single-responsibility modules, dependency injection
  throughout the runner, one place for each concern, no duplicated logic.

---

## 2. Architecture

### 2.1 How deterministic intelligence feeds the AI Platform

```
┌──────────────────────────────────────────────────────────────────────────┐
│                     DETERMINISTIC ENGINES (unchanged)                       │
│  Ranking · Rule Scoring · Semantic/FAISS · CrossEncoder ·                  │
│  Candidate Intelligence · Career Timeline · Risk Detection ·               │
│  Hiring Recommendation · Interview Planner                                  │
└───────────────────────────────┬──────────────────────────────────────────┘
                                 │  (already aggregated by Phase 2)
                                 ▼
                    ┌──────────────────────────┐
                    │  src/insights            │  CandidateInsights bundle
                    │  (+ InterviewPlan, JD)   │
                    └────────────┬─────────────┘
                                 │  agent.build_evidence()  →  EVIDENCE (JSON)
                                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                            AI PLATFORM  (src/ai)                            │
│                                                                            │
│   AgentRunner ── orchestrates ──────────────────────────────────────────┐ │
│     1. ContextBuilder → AgentContext                                      │ │
│     2. Cache lookup  (FileCache, composite key)                          │ │
│     3. Provider select (factory) ── OpenAI/Claude/Gemini/Ollama/**Local**│ │
│     4. PromptLoader → system+user messages (templates on disk)           │ │
│     5. provider.generate_json(evidence, schema)  + retry loop            │ │
│     6. JSON + Schema validation  →  HiringAnalysis                       │ │
│     7. SafetyGuard (no fabrication / uncertainty / score-free)          │ │
│     8. Cache write-back + TelemetryLogger                                │ │
│        (on provider failure → deterministic composer FALLBACK)          │ │
│   ───────────────────────────────────────────────────────────────────────┘ │
│                                 │ AgentResult (validated, standardized)      │
└─────────────────────────────────┬──────────────────────────────────────────┘
                                  ▼
                    ┌──────────────────────────┐
                    │  UI: "AI Hiring Analyst" │  on-demand / cache only
                    │  profile tab             │  (never during ranking)
                    └──────────────────────────┘
```

The **deterministic engines remain the single source of numeric truth.** The AI
layer only interprets their output into human-quality narrative.

### 2.2 Folder structure

```
src/ai/
├── config/
│   └── settings.py            # AISettings.from_env() — provider/model/cache/telemetry
├── core/
│   ├── base_agent.py          # BaseAgent (the agent contract)
│   ├── runner.py              # AgentRunner (lifecycle, DI, retries, fallback)
│   ├── registry.py            # AgentRegistry (+ default `registry`)
│   ├── context.py             # AgentContext (request-scoped DI)
│   ├── metadata.py            # AgentMetadata (identity → cache key)
│   ├── agent_config.py        # AgentConfig (per-run knobs)
│   ├── response.py            # AgentResponse / AgentResult / AgentStatus / TokenUsage
│   └── exceptions.py          # AgentException hierarchy
├── providers/
│   ├── base.py                # BaseLLMProvider + LLMMessage
│   ├── local.py               # LocalHeuristicProvider (offline, deterministic)
│   ├── composers.py           # deterministic composer registry
│   ├── _remote.py             # RemoteProvider template (DRY)
│   ├── openai_provider.py     # lazy `openai`
│   ├── claude_provider.py     # lazy `anthropic`
│   ├── gemini_provider.py     # lazy `google.generativeai`
│   ├── ollama_provider.py     # lazy `ollama`
│   └── factory.py             # get_provider() + graceful fallback
├── prompts/
│   ├── loader.py              # versioned, file-based templates + validation
│   └── templates/
│       ├── hiring_analyst_system.v1.md
│       └── hiring_analyst_user.v1.md
├── schemas/
│   ├── base.py                # BaseAIResponse
│   └── hiring_analysis.py     # HiringAnalysis (score-free by design)
├── validators/
│   ├── json_validator.py      # parse + schema-validate (typed errors)
│   └── safety.py              # SafetyGuard (Module 8)
├── cache/
│   ├── base.py                # BaseCache + NullCache
│   ├── key.py                 # composite cache key
│   └── file_cache.py          # FileCache (JSON on disk)
├── memory/
│   ├── base.py                # BaseMemory interface
│   ├── session.py             # SessionMemory (in-session)
│   └── context_builder.py     # ContextBuilder
├── telemetry/
│   ├── models.py              # TelemetryEvent
│   └── logger.py              # TelemetryLogger (JSONL + ring buffer)
├── agents/
│   └── hiring_analyst.py      # HiringAnalystAgent + deterministic composer
├── services/
│   └── hiring_analyst_service.py  # UI-facing facade (singleton runner)
└── utils/
    └── json_utils.py          # robust JSON extraction

src/ui/ai_analyst_tab.py       # Module 10 — the AI Hiring Analyst tab
src/ui/profile_tabs.py         # (modified) 10th tab wired in
src/ui/candidate_card.py       # (modified) passes insights + jd through
```

`app.py` was **not modified** — the AI tab is nested inside the existing card →
profile-tabs flow, keeping the orchestrator minimal (Module 12).

---

## 3. Agent lifecycle

For each call to `AgentRunner.run(agent, payload, config)`:

1. **Evidence** — `agent.build_evidence(payload)` returns the authoritative,
   structured facts (candidate + all engine outputs). Nothing else is factual.
2. **Context** — `ContextBuilder` mints a request id and an `AgentContext`.
3. **Cache** — a composite key (`agent · version · prompt_version · provider ·
   model · candidate_id · hash(jd)`) is checked; a hit returns a `CACHED` result.
4. **Provider** — the factory returns the configured provider, transparently
   substituting the offline provider if a remote one is unhealthy (non-strict).
5. **Prompt** — `PromptLoader` renders the on-disk system + user templates,
   injecting the evidence JSON and the schema field list.
6. **Generation + retries** — `provider.generate_json(...)`; on malformed JSON /
   schema failure the runner re-asks with a corrective message up to
   `max_retries` (deterministic providers are exact → single attempt).
7. **Validation** — output is parsed and validated into the Pydantic schema; no
   raw provider text ever escapes this boundary.
8. **Safety** — `SafetyGuard` asserts the schema is score-free and adds soft
   warnings (e.g. missing uncertainty, unverifiable transferable skills).
9. **Fallback** — if a real provider produced nothing usable and fallback is
   allowed, the **deterministic composer** produces the answer (`FALLBACK`).
10. **Cache write-back + telemetry** — the result is cached and one
    `TelemetryEvent` is recorded.

**Adding a new agent** (e.g. `ResumeAnalystAgent`): subclass `BaseAgent`
(implement `build_evidence`, `prompt_values`, `cache_dimensions`), define a
score-free schema, drop two prompt templates in `prompts/templates/`, register a
deterministic composer, and `registry.register(...)`. No runner changes.

---

## 4. Provider abstraction

`BaseLLMProvider` defines `generate` / `generate_json` / `stream` /
`health_check`. Concrete providers:

| Provider | SDK (lazy) | Credential | Notes |
|---|---|---|---|
| `local` | none | none | Offline deterministic composer — **default** |
| `openai` | `openai` | `OPENAI_API_KEY` | JSON mode |
| `claude` | `anthropic` | `ANTHROPIC_API_KEY` | system prompt separated |
| `gemini` | `google-generativeai` | `GOOGLE_API_KEY` | JSON mime type |
| `ollama` | `ollama` | none | local server (`OLLAMA_HOST`) |

Selection is via `TALENTMIND_AI_PROVIDER`. `health_check()` performs **no network
round-trip** (SDK importable + key present), so it is safe to call during
rendering and tests. Remote providers share a `RemoteProvider` template so a new
vendor is ~30 lines (DRY).

---

## 5. Prompt management

Prompts are **never** hard-coded in Python. They live as
`{name}.{version}.md` files under `prompts/templates/`, use `{{placeholder}}`
syntax, and are loaded, validated (missing-placeholder detection) and rendered by
`PromptLoader`. Versioning is first-class and participates in the cache key, so
publishing a new prompt version never serves a stale cached answer.

---

## 6. Cache strategy

`FileCache` stores each response as a JSON file keyed by the composite key in
§3.3. The key includes **candidate_id, job description, prompt version, provider,
and model** (exactly as required), so answers are never reused across different
inputs. Reads never raise (a corrupt/stale entry is a miss), and a stale entry
that no longer validates against the current schema is transparently ignored.
The UI uses a provider-free `peek()` to show cached analyses instantly while
keeping generation strictly on demand (Module 11).

---

## 7. Safety design (Module 8)

- **Cannot alter scores — structurally.** The `HiringAnalysis` schema has no
  numeric fields; `SafetyGuard.assert_schema_is_score_free` fails fast if any
  agent ever violates this. The AI physically cannot emit a score.
- **Cannot fabricate — in offline mode.** The deterministic composer only
  restates provided evidence, so hallucination is impossible on the default path.
- **Cannot contradict the engines.** The system prompt forbids recomputing or
  arguing with scores; the composer maps the engine recommendation to the
  narrative verdict (a weak candidate can never be narrated "Strong Hire" — this
  is covered by a test).
- **Must state uncertainty.** When evidence signals low confidence / high risk,
  the composer emits explicit uncertainty and the guard warns if a remote model
  omits it. The verdict falls back to `Insufficient Evidence` when unclear.

---

## 8. Telemetry (Module 7)

Every run emits a `TelemetryEvent` (provider, model, status, latency, prompt/
completion tokens, cache hit, retries, warnings, error) to
`logs/ai_telemetry.jsonl` plus an in-memory ring buffer for live display. Logging
never raises — observability cannot break a request. Telemetry is entirely
outside the business logic (`services.recent_telemetry` exposes it read-only).

---

## 9. Performance (Module 11)

The AI never runs during ranking. Generation happens only:
- **on demand** (the recruiter clicks *Generate* / *Refresh* in the AI tab), or
- **from cache** (a provider-free `peek` auto-loads a prior analysis).

The offline default provider is fast and deterministic, so the tab is responsive
even without any external service. Existing application performance is unchanged.

---

## 10. Verification (Module 13)

| Check | Result |
|---|---|
| Compile entire `src/ai` (`compileall`) | ✅ |
| Imports resolve / no circular deps (faiss-before-torch preserved) | ✅ |
| Config + provider factory + health + graceful fallback | ✅ |
| Prompt loading + placeholder validation | ✅ |
| Schema validation + malformed-output handling | ✅ |
| Cache key composition + file round-trip + force-refresh + peek | ✅ |
| Safety (score-free schema, reflects-not-contradicts) | ✅ |
| Telemetry recording | ✅ |
| Runner lifecycle + HiringAnalystAgent (offline) | ✅ |
| AI Hiring Analyst tab renders + on-demand generation (AppTest) | ✅ |
| Streamlit app boots; no Phase 1/2 regressions | ✅ |
| **Total** | **60 tests passing** |

Run: `pytest tests/ -p no:faulthandler`
(`-p no:faulthandler` silences a benign faiss/torch OpenMP shutdown traceback on
Windows; exit code is 0.)

---

## 11. Future extension points

The platform was designed so these agents are mostly "implement `BaseAgent` +
register":

- `ResumeAnalystAgent`, `JDAnalystAgent`, `InterviewPlannerAgent`,
  `SalaryAdvisorAgent`, `OfferAdvisorAgent`, `HiringCommitteeAgent`,
  `ExecutiveReportAgent`, `TalentInsightsAgent`, `RecruiterCopilotAgent`.

Concrete seams already in place:
- **Multi-agent routing** — `AgentRegistry` already discovers agents by name.
- **Streaming** — `BaseLLMProvider.stream` is defined (safe default provided).
- **Durable / long-term memory** — `BaseMemory` interface + `ContextBuilder`
  seam are ready; only `SessionMemory` ships now.
- **New providers / caches** — add a class behind `BaseLLMProvider` / `BaseCache`
  and register it; no caller changes.
- **Prompt experimentation** — drop `*.v2.md` templates; bump `prompt_version`.

---

## 12. Configuration quick reference

```bash
# Use the offline default (no setup needed) — this is the default.
TALENTMIND_AI_PROVIDER=local

# Or plug in a real provider (SDK + key required):
TALENTMIND_AI_PROVIDER=openai   OPENAI_API_KEY=...
TALENTMIND_AI_PROVIDER=claude   ANTHROPIC_API_KEY=...
TALENTMIND_AI_PROVIDER=gemini   GOOGLE_API_KEY=...
TALENTMIND_AI_PROVIDER=ollama   OLLAMA_HOST=http://localhost:11434

# Optional tuning
TALENTMIND_AI_MODEL=...            TALENTMIND_AI_TEMPERATURE=0.2
TALENTMIND_AI_MAX_RETRIES=2        TALENTMIND_AI_CACHE_ENABLED=true
TALENTMIND_AI_STRICT=false         # true = never fall back to the composer
```

No configuration is required for the platform to work — it ships fully functional
offline, which is exactly what makes it a foundation rather than a bolt-on.
