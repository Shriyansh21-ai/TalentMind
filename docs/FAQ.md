# TalentMind — FAQ

### What is TalentMind?
An AI-powered candidate intelligence and ranking platform. It combines a deterministic rule-based
scoring engine, semantic vector search (FAISS + sentence embeddings), a multi-agent AI reasoning
layer, and an enterprise SaaS platform foundation — all behind a single Streamlit application.

### Does it require an internet connection?
The **AI agent layer is offline by default** — the `local` provider composes results
deterministically with no network. The **core ranking** downloads the `BAAI/bge-small-en-v1.5`
embedding model (and KeyBERT) from Hugging Face on first use and caches them; subsequent runs are
offline. The enterprise platform is entirely in-memory and needs no network.

### Does the AI make up information or scores?
No. In offline mode every AI response is produced by a **deterministic composer** — a pure function
of the deterministic engines' output — so it cannot contradict the engines or invent facts. A
runtime `SafetyGuard` structurally forbids the AI from emitting any score/rating/percent field. The
AI **explains** rankings; it never **computes** them.

### Which LLM providers are supported?
`local` (default, offline, deterministic), plus `openai`, `claude`, `gemini`, and `ollama`. Vendor
SDKs are imported lazily, so booting never requires any provider library. If a selected remote
provider is unavailable, the runner falls back to `local` (unless `TALENTMIND_AI_STRICT=true`).

### Is there a REST API?
Not bundled. `src/platform/api` provides **REST-ready contracts** (response envelopes, pagination,
filtering, versioning, rate limiting, an OpenAPI skeleton) designed to sit behind a future HTTP
layer. The public surface today is in-process Python service classes. See
[`API_REFERENCE.md`](API_REFERENCE.md).

### Are the HRIS/ATS integrations real?
They are **offline reference interfaces** with real metadata and capability declarations, but no
live transport. Implement the transport behind the provider seam and supply credentials to go live.
See [`INTEGRATIONS.md`](INTEGRATIONS.md).

### How does the AI Hiring Committee decide?
Seven independent reviewers each read one slice of evidence (no reviewer sees another's opinion).
Their opinions are combined by an **evidence-weighted consensus** — not a majority vote — weighted
by confidence × evidence coverage × role/mode. A Committee Chair narrates and justifies the
consensus; it does not re-decide by fiat. See [`MULTI_AGENT_SYSTEM.md`](MULTI_AGENT_SYSTEM.md).

### How is data isolated between tenants?
Tenant isolation is enforced at the repository boundary: any cross-tenant read/write raises
`TenantIsolationError`. Tenant context is ambient and entered at the edge by middleware. See
[`SECURITY.md`](SECURITY.md).

### Where is data stored?
All enterprise-platform persistence is **in-memory** (`InMemoryRepository`). The AI cache is JSON
files under `data/ai_cache/`, telemetry is JSONL under `logs/`, and `rank.py` writes exports to
`outputs/`. To persist platform data, implement a repository/storage adapter behind the existing
interfaces.

### What Python version is required?
Python **3.11+** (3.13 recommended).

### How do I run the tests?
```bash
pip install -r requirements-dev.txt
pytest -q          # 761 tests
```

### How do I add a new agent or integration?
See [`DEVELOPER_GUIDE.md`](DEVELOPER_GUIDE.md) and
[`ENTERPRISE_AGENTS.md`](ENTERPRISE_AGENTS.md#adding-a-new-agent). New agents plug into
orchestration with no orchestration-code changes.

### What's the license?
MIT (declared in `pyproject.toml`). Add a `LICENSE` file with your copyright line before
publishing.
