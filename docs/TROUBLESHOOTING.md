# TalentMind — Troubleshooting

Common issues and their resolutions. See also [`INSTALL.md`](INSTALL.md),
[`CONFIGURATION.md`](CONFIGURATION.md), and [`OPERATIONS.md`](OPERATIONS.md).

---

## Startup

### The process segfaults at import on Windows
`app.py` and `rank.py` import `faiss` **before** `torch` / `sentence-transformers` on purpose — the
reverse OpenMP load order segfaults on Windows. Do not reorder that import (the `import faiss` line
carries a `# noqa: F401` comment explaining this). If you add a new entry point, import `faiss`
first there too.

### First run is slow or fails to fetch a model
The core ranking uses `BAAI/bge-small-en-v1.5` (and JD parsing uses KeyBERT), downloaded from
Hugging Face on first use and cached locally afterward. The **first run requires network**; later
runs are offline. The AI *agent* layer is offline regardless (default `local` provider). If the
download fails, check connectivity/proxy, or pre-populate the Hugging Face cache.

### `streamlit: command not found`
Activate the virtualenv first (`source venv/bin/activate` / `venv\Scripts\activate`) and run
`pip install -r requirements.txt`. Or run `python -m streamlit run app.py`.

---

## Data

### No candidates appear / empty results
The app reads `data/raw/candidates.jsonl`. That file is git-ignored, so a fresh clone has no
candidate data. Provide a JSONL file (one candidate object per line) matching the schema in
`src/models/candidates.py`. The Recruiter Console also requires a JD uploaded via the sidebar.

### `AttributeError: 'str' object has no attribute 'to_text'` when running `rank.py`
`hybrid_score` expects a parsed `JobProfile` (it calls `.to_text()`), while the JD is loaded as raw
text. Parse it first, mirroring `app.py`:

```python
from src.intelligence.jd_parser import parse_jd
from src.intelligence.jd_analyzer import analyze
job_profile = analyze(parse_jd(jd_text))
score = hybrid_score(candidate, job_profile)
```

---

## AI layer

### An AI workspace shows a fallback/warning banner
If you selected a remote provider (`openai`/`claude`/`gemini`/`ollama`) and it is unavailable
(missing key, SDK not installed, endpoint down), the runner falls back to the deterministic `local`
provider and marks the result `FALLBACK`. Set the credential, install the SDK, or set
`TALENTMIND_AI_PROVIDER=local` to silence it. Set `TALENTMIND_AI_STRICT=true` to fail instead of
falling back.

### Results seem stale after a change
Results are cached in `data/ai_cache/`, keyed on agent/prompt/provider/model/subject. Bump a
version, pass `AgentConfig(force_refresh=True)`, or clear the cache:
`rm -rf data/ai_cache/*` (safe — reads never raise, results recompute deterministically).

### `SafetyViolationError` when adding an agent
The safety guard rejects any output schema whose field names contain `score` / `rating` /
`percent` / `confidence_value`. Rename the field — the AI layer must not emit scores. See
[`ENTERPRISE_AGENTS.md`](ENTERPRISE_AGENTS.md#adding-a-new-agent).

---

## Windows cache/permission flakes in tests

A single AI-cache test (`test_force_refresh_recomputes`) can intermittently raise a Windows
`PermissionError` on `os.replace` when antivirus/Search indexing briefly locks the newly written
`.tmp` file. It is environmental (the atomic write is correct); re-run the suite, or exclude the
`data/` and temp directories from real-time scanning.

---

## Platform layer

### `ConfigurationError: unknown key`
The DI container was asked to resolve a service that was not registered. Use `build_platform()` /
the relevant `build_*_platform()` factory rather than constructing services directly.

### `TenantIsolationError`
A tenant-scoped repository was accessed with the wrong `tenant_id`. This is the isolation guard
working as intended — scope the operation to the correct tenant context.

### A cloud provider raises "not ready"
External IdP, cloud secret, cloud storage, and notification-channel providers are **reference
stubs**. Implement the transport behind the provider seam and supply credentials to make them live
(see [`INTEGRATIONS.md`](INTEGRATIONS.md) and [`SECURITY.md`](SECURITY.md)).
