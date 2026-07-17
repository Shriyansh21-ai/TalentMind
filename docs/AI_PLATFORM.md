# TalentMind — AI Platform

The AI Platform (`src/ai/`) turns the output of the deterministic hiring engines into
executive-quality narrative. It adds **explanation, never computation**: it does not score, rank,
or invent. This document describes the provider abstraction, the core runner, the safety model,
caching, and telemetry. For the agents themselves see [`ENTERPRISE_AGENTS.md`](ENTERPRISE_AGENTS.md);
for orchestration and the committee see [`MULTI_AGENT_SYSTEM.md`](MULTI_AGENT_SYSTEM.md).

---

## 1. Design principles

| Principle | How it is enforced |
|---|---|
| **Score-free** | `SafetyGuard.assert_schema_is_score_free` rejects any output schema whose field names contain `score` / `rating` / `percent` / `confidence_value`. Checked before every run. |
| **Offline-by-default** | The default `local` provider composes schema-valid JSON deterministically from evidence — no network, no model download. |
| **No hallucination in offline mode** | A response is a pure function of the deterministic engines' evidence via a registered *composer*, so it cannot contradict the engines or invent facts. |
| **Provider-agnostic** | Every agent depends only on `BaseLLMProvider`; vendor SDKs are imported lazily so booting never requires any provider library. |
| **No raw model output escapes** | Provider output is parsed and validated against a Pydantic schema; only the typed `AgentResult.data` crosses the boundary. |

---

## 2. Provider abstraction — `src/ai/providers/`

### Base interface — `providers/base.py`

`BaseLLMProvider(ABC)` is the single contract the rest of the app depends on:

- `generate(messages) -> AgentResponse`
- `generate_json(messages, *, schema, schema_name, evidence=None) -> AgentResponse`
- `health_check() -> bool`
- `stream()` — default yields the full non-streaming result once
- properties `model` and `is_deterministic` (default `False`)

`LLMMessage` is a `{role, content}` dataclass.

### Registered providers — `providers/factory.py`

| Key | Class | Module | Credential | Deterministic |
|---|---|---|---|---|
| `local` | `LocalHeuristicProvider` | `local.py` | — | ✅ (default) |
| `openai` | `OpenAIProvider` | `openai_provider.py` | `OPENAI_API_KEY` | ✗ |
| `claude` | `ClaudeProvider` | `claude_provider.py` | `ANTHROPIC_API_KEY` | ✗ |
| `gemini` | `GeminiProvider` | `gemini_provider.py` | `GOOGLE_API_KEY` | ✗ |
| `ollama` | `OllamaProvider` | `ollama_provider.py` | none (host `OLLAMA_HOST`) | ✗ |

Remote providers extend `RemoteProvider` (`providers/_remote.py`), a template-method base:
subclasses set `env_key` and implement `_sdk_available()`, `_client()`, and
`_complete(client, messages, json_mode)`. `health_check()` is API-key-present **and**
SDK-importable — it performs no network round-trip. `generate_json` prepends a system directive
forcing a single schema-valid JSON object and extracts it from the response.

### Selection & fallback

`get_provider(settings) -> (provider, warnings)`:

1. Build `settings.provider`.
2. If it is deterministic → return immediately.
3. Else if `health_check()` passes → return it.
4. Else if `settings.strict` → raise `ProviderUnavailableError`.
5. Else → fall back to `LocalHeuristicProvider` with a warning.

Extension points: `register_provider(key, cls)`, `build_provider(key, settings)`,
`available_providers(settings) -> {key: healthy}`.

### Deterministic composers — `providers/composers.py`

A **composer** is a `Callable[[dict], dict]` that restates evidence into a schema-shaped dict.
`register_composer(schema_name, composer)`, `get_composer`, `has_composer`. Each agent registers
its composer on import, so the `local` provider always has a deterministic way to answer.

---

## 3. Configuration — `src/ai/config/settings.py`

`AISettings` is a frozen dataclass built by `AISettings.from_env()`.

| Env var | Default | Notes |
|---|---|---|
| `TALENTMIND_AI_PROVIDER` | `local` | invalid values fall back to `local` |
| `TALENTMIND_AI_MODEL` | provider default | see `_DEFAULT_MODELS` |
| `TALENTMIND_AI_TEMPERATURE` | `0.2` | |
| `TALENTMIND_AI_MAX_TOKENS` | `1200` | |
| `TALENTMIND_AI_TIMEOUT` | `30` | seconds |
| `TALENTMIND_AI_MAX_RETRIES` | `2` | |
| `TALENTMIND_AI_CACHE_ENABLED` | `true` | |
| `TALENTMIND_AI_CACHE_DIR` | `data/ai_cache` | |
| `TALENTMIND_AI_TELEMETRY_DIR` | `logs` | |
| `TALENTMIND_AI_STRICT` | `false` | fail instead of falling back |

Default models: local `deterministic-composer-v1`, openai `gpt-4o-mini`, claude `claude-sonnet-5`,
gemini `gemini-1.5-flash`, ollama `llama3.1`.

---

## 4. Core runtime — `src/ai/core/`

| Component | Module | Responsibility |
|---|---|---|
| `BaseAgent` | `base_agent.py` | Declares `metadata` + `output_schema`; hooks `build_evidence`, `prompt_values`, `cache_dimensions`. Generic `build_messages()` renders `{prompt_id}_system/_user` templates. |
| `AgentConfig` | `agent_config.py` | Per-run overrides: `use_cache`, `force_refresh`, `allow_fallback`, `max_retries`. |
| `AgentMetadata` | `metadata.py` | `name`, `version`, `title`, `description`, `prompt_id`, `prompt_version`, `tags`. |
| `AgentResult` / `AgentStatus` | `response.py` | Public result envelope; status ∈ `SUCCESS`, `CACHED`, `FALLBACK`, `FAILED`. |
| `AgentRegistry` | `registry.py` | Process-wide registry; agents self-register on import. |
| `AgentRunner` | `runner.py` | The generic execution engine (below). |
| `ContextBuilder` | `memory/context_builder.py` | Builds a request-scoped `AgentContext` with a UUID request id. |

### `AgentRunner.run(agent, payload, config)` flow

1. `safety.assert_schema_is_score_free(schema_cls)`
2. `agent.build_evidence(payload)`
3. `agent.cache_dimensions(payload)` → `build_cache_key(...)`
4. Cache lookup → return `CACHED` on hit
5. Execute: select provider → retry loop (`max_retries + 1`; deterministic providers get one
   attempt) → `validate_text` each attempt
6. On real-provider failure with `allow_fallback` and not `strict` → deterministic
   `LocalHeuristicProvider` fallback → status `FALLBACK`
7. Soft `safety.review()` (non-blocking warnings)
8. Cache write-back
9. Telemetry emit

`peek(agent, payload)` returns a cached result **without ever calling a provider** — used by the
UI to load an analysis on demand.

---

## 5. Safety — `src/ai/validators/safety.py`

- `assert_schema_is_score_free(schema_cls)` — raises `SafetyViolationError` if any output field
  name contains a score-like token. This is the structural guarantee that **the AI never emits a
  score**.
- `review(result)` — returns soft warnings (e.g. missing uncertainty acknowledgement,
  transferable skills that cannot be traced to evidence). Non-blocking.

`validators/json_validator.py::validate_text(text, schema_cls)` parses JSON then validates against
the Pydantic schema, raising `JSONParseError` / `SchemaValidationError`.

---

## 6. Caching — `src/ai/cache/`

- `BaseCache` / `NullCache` (`base.py`)
- `FileCache` (`file_cache.py`) — one JSON file per key, atomic write-then-replace; **reads never
  raise** (a corrupt or missing entry is a cache miss, so the cache can never break a request).
- `build_cache_key(...)` (`key.py`) hashes agent, agent version, prompt version, provider, model,
  subject id, and scope — so a cached answer is never served across a changed dimension.

Cache location defaults to `data/ai_cache/` (git-ignored).

---

## 7. Telemetry — `src/ai/telemetry/`

`TelemetryLogger` appends `TelemetryEvent` records to `logs/ai_telemetry.jsonl` and keeps a
200-entry in-memory ring buffer. It **never raises** — telemetry failures cannot break a request.
`get_default_logger()` returns the process logger.

---

## 8. Prompts & schemas

- **Prompts** (`prompts/loader.py`) — versioned Markdown templates named `{name}.{version}.md`
  with `{{placeholder}}` substitution. Prompts are never hard-coded in Python; a missing
  placeholder raises `PromptRenderError`.
- **Schemas** (`schemas/`) — `BaseAIResponse(BaseModel)` provides `schema_name`, `field_names`,
  `json_schema`, `to_dict`, with `extra="ignore"`. Concrete schemas live with their agents.

---

## 9. UI-facing facade — `src/ai/services/`

`hiring_analyst_service.py` exposes a process-wide `AgentRunner` singleton (via `lru_cache`) and
convenience functions: `analyze_candidate(...)`, `peek_cached_analysis(...)`,
`get_platform_status()`, `recent_telemetry()`. The Streamlit workspaces call this facade rather
than constructing a runner themselves.
