# TalentMind — Configuration

TalentMind is configured through **environment variables**. It is offline-by-default: with no
configuration at all, the app boots, the enterprise platform runs entirely in-memory, and the AI
layer uses the deterministic `local` provider.

---

## 1. AI platform (`src/ai/config/settings.py`)

Read by `AISettings.from_env()`.

| Variable | Default | Purpose |
|---|---|---|
| `TALENTMIND_AI_PROVIDER` | `local` | `local`, `openai`, `claude`, `gemini`, `ollama`. Invalid → `local`. |
| `TALENTMIND_AI_MODEL` | provider default | Override the model name. |
| `TALENTMIND_AI_TEMPERATURE` | `0.2` | Sampling temperature (remote providers). |
| `TALENTMIND_AI_MAX_TOKENS` | `1200` | Max output tokens. |
| `TALENTMIND_AI_TIMEOUT` | `30` | Provider timeout (seconds). |
| `TALENTMIND_AI_MAX_RETRIES` | `2` | Retries on a failed/invalid completion. |
| `TALENTMIND_AI_CACHE_ENABLED` | `true` | Enable the file cache. |
| `TALENTMIND_AI_CACHE_DIR` | `data/ai_cache` | Cache directory. |
| `TALENTMIND_AI_TELEMETRY_DIR` | `logs` | Telemetry JSONL directory. |
| `TALENTMIND_AI_STRICT` | `false` | If `true`, a broken provider raises instead of falling back to `local`. |

**Provider credentials** (only needed if you switch away from `local`):

| Variable | Provider |
|---|---|
| `OPENAI_API_KEY` | OpenAI |
| `ANTHROPIC_API_KEY` | Claude |
| `GOOGLE_API_KEY` | Gemini |
| `OLLAMA_HOST` (default `http://localhost:11434`) | Ollama |

**Default models:** local `deterministic-composer-v1`, openai `gpt-4o-mini`, claude
`claude-sonnet-5`, gemini `gemini-1.5-flash`, ollama `llama3.1`.

### Choosing a provider

```bash
# Fully offline, deterministic (default) — no keys, no network for the agent layer
export TALENTMIND_AI_PROVIDER=local

# Use a hosted model, but never crash if it is unavailable
export TALENTMIND_AI_PROVIDER=claude
export ANTHROPIC_API_KEY=sk-...
# (leave TALENTMIND_AI_STRICT=false so it falls back to `local` on any error)
```

Even with a remote provider selected, output is parsed and validated against a score-free schema;
if it fails or is unavailable, the runner falls back to the deterministic composer (unless
`TALENTMIND_AI_STRICT=true`).

---

## 2. Streamlit / application

| Variable | Default (in Docker) | Purpose |
|---|---|---|
| `STREAMLIT_SERVER_PORT` | `8501` | HTTP port. |
| `STREAMLIT_SERVER_ADDRESS` | `0.0.0.0` | Bind address. |
| `STREAMLIT_SERVER_HEADLESS` | `true` | Headless mode. |
| `STREAMLIT_BROWSER_GATHER_USAGE_STATS` | `false` | Disable telemetry. |
| `HF_HUB_DISABLE_SYMLINKS_WARNING` | `1` (set in `app.py`) | Silence a Hugging Face warning. |
| `TOKENIZERS_PARALLELISM` | `false` (set in `app.py`) | Avoid tokenizer fork warnings. |
| `TALENTMIND_ENV` | `production` (in Docker) | Free-form environment label. |

The application reads its candidate pool from `data/raw/candidates.jsonl` (constant
`CANDIDATES_PATH` in `app.py`) and the JD via the sidebar upload.

---

## 3. Enterprise platform configuration (`src/platform/config`)

The platform has its own **per-tenant** configuration service (`ConfigurationService`), separate
from process environment variables. It manages feature flags, licensing, usage limits, AI
provider/model config, localization, and custom prompts, all stored in-memory per tenant:

```python
from src.platform.bootstrap import build_platform
p = build_platform()
cfg = p.config.ensure(tenant_id)
p.config.set_feature(tenant_id, "ai_committee", enabled=True)
p.config.is_feature_enabled(tenant_id, "ai_committee")   # -> True
```

Deployment-time configuration profiles (dev/staging/prod) are modeled separately by the deployment
platform's `ConfigurationPlatform` (`src/platform/deployment/configuration.py`): `profiles`,
`load`, `validate`, `export`, `template`, `document`.

---

## 4. Runtime directories

| Path | Contents | Tracked? |
|---|---|---|
| `data/raw/` | Input data (`job_description.txt`; `candidates.jsonl` is local/ignored) | partial |
| `data/ai_cache/` | AI response cache | ignored |
| `data/pipeline_state.json` | Recruiter pipeline state | ignored |
| `outputs/` | `rank.py` CSV/JSON exports | ignored |
| `logs/` | Telemetry & app logs | ignored |

All runtime directories are created lazily and are safe to delete between runs.
