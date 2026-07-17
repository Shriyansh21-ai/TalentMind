<div align="center">

# 🧠 TalentMind

### Enterprise Candidate Intelligence Platform

*Explainable, deterministic, offline-first AI for modern hiring teams.*

<!-- Badges are placeholders — point them at your fork/CI once published. -->
![Status](https://img.shields.io/badge/status-1.0.0%20Enterprise-blue)
![Python](https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white)
![Tests](https://img.shields.io/badge/tests-761%20passing-brightgreen)
![License](https://img.shields.io/badge/license-MIT-green)
![Code style](https://img.shields.io/badge/lint-ruff-000000)
![Offline](https://img.shields.io/badge/AI-offline--by--default-success)

</div>

---

## Overview

**TalentMind** is an AI-powered candidate intelligence and ranking platform that helps
recruiters and hiring teams identify, evaluate, and prioritize talent from large candidate
pools. It combines a transparent rule-based scoring engine, semantic vector search, a
multi-agent AI reasoning layer, and an enterprise SaaS platform foundation — all behind a
single Streamlit application.

Unlike traditional ATS keyword matching, TalentMind pairs **deterministic scoring** with an
**explainable AI layer** whose outputs are, by design, a pure function of the underlying
engines. In its default configuration the AI layer runs **fully offline** and **never emits a
score it did not compute** — hallucination is structurally prevented, not merely discouraged.

### Vision

Give hiring teams the reasoning of a senior recruiting committee — evidence-weighted,
auditable, and explainable — without sacrificing determinism, privacy, or control. Every
recommendation should trace back to a concrete signal, every AI narrative should be grounded
in a deterministic engine, and the whole platform should boot and run with no external service.

---

## Key Features

| Capability | What it does |
|---|---|
| **Multi-factor ranking engine** | 10-component rule score (skills, experience, title, behavior, company, career trajectory, JD match, availability, red flags, penalties). |
| **Semantic matching** | `BAAI/bge-small-en-v1.5` sentence embeddings + hybrid rule/semantic scoring. |
| **FAISS vector search** | Natural-language recruiter search over the candidate pool (`IndexFlatIP`). |
| **Explainable AI** | Per-component score breakdowns, ranking reasons, matched/missing skills, skill-gap %. |
| **Candidate Intelligence** | Deterministic engines for candidate profiling, career-timeline analysis, and resume-risk detection. |
| **12 AI agents** | Resume, JD, Hiring Analyst, Interview Studio, Executive Report, Compensation, Pay Equity, Compliance, Audit, Hiring Intelligence, Copilot, Committee Chair. |
| **AI Hiring Committee** | 7 independent reviewers → evidence-weighted consensus → chair decision (never a majority vote). |
| **Multi-agent orchestration** | Deterministic planner + DAG workflow engine + capability routing; new agents plug in without touching orchestration. |
| **Recruiter Copilot** | Intent-classified conversational assistant that only speaks facts produced by deterministic tools. |
| **Enterprise platform** | Multi-tenancy, authentication, RBAC + ABAC, hash-chained audit, runtime/jobs, integration framework, deployment tooling. |
| **Data export** | Ranked candidates to CSV / JSON for ATS and reporting. |

---

## Enterprise Capabilities

The `src/platform/` layer is an **additive, offline, deterministic** enterprise SaaS foundation.
It is architecturally isolated from the hiring engines (a test guard enforces that
`src/platform/*` never imports the business core).

- **Multi-tenancy** — tenant-per-organization isolation enforced at the repository boundary
  (`TenantIsolationError`); ambient tenant context, resolver, and middleware.
- **Authentication** — local identity provider with PBKDF2-HMAC-SHA256 (240k iterations)
  password hashing, rotating refresh tokens, device sessions, and an SSO-ready provider seam.
- **Authorization** — 12 built-in roles, `resource:action` permissions with wildcards, and a
  combined **RBAC + ABAC** policy engine that is default-deny and produces explainable decisions.
- **Audit** — two independent tamper-evident, hash-chained audit trails with `verify_chain`.
- **Runtime platform** — background jobs, worker pools, a task-execution engine, distributed
  cache, health aggregation, load management, and a resilience engine (retry/timeout/circuit
  breaker) — all deterministic with no real threads or wall-clock sleeps.
- **Integration framework** — a uniform provider model with **40+ HRIS/ATS/calendar/
  communication/document connectors as offline reference interfaces**, plus an in-process API
  gateway, webhook platform, event bus, and sync framework.
- **Deployment platform** — deployment/rollback planning, config governance, backup & recovery,
  release engineering (semantic versioning), and production-readiness validation.
- **Governance & security** — secrets management, observability, monitoring, threat detection,
  and representative control catalogues (GDPR / SOC 2 / ISO 27001 / HIPAA / PCI-DSS / AI-governance).

> **Scope note (honest by design):** the enterprise platform is a fully-implemented,
> in-memory, deterministic *architecture*. External connectors (cloud IdPs, HRIS/ATS APIs,
> cloud secret stores, notification channels, cloud storage, telemetry exporters) are
> **interfaces / reference stubs** — bring your own transport and credentials to make them live.
> There is no bundled HTTP server; `api/` and the integration gateway are in-process contracts.

---

## Architecture Overview

```
        ┌───────────────────────────────────────────────────────────────┐
        │  Presentation   app.py (Streamlit) · src/ui/* (17 workspaces)  │
        └───────────────────────────────┬───────────────────────────────┘
                                         │
        ┌────────────────────────────────┴──────────────────────────────┐
        │  AI Layer  src/ai/                                             │
        │    providers (local·openai·claude·gemini·ollama) · core runner │
        │    12 agents · Hiring Committee · orchestration · copilot      │
        │    SafetyGuard (score-free) · deterministic composers · cache  │
        └────────────────────────────────┬──────────────────────────────┘
                                         │  consumes (never re-ranks)
        ┌────────────────────────────────┴──────────────────────────────┐
        │  Business Core  (deterministic, unchanged)                     │
        │    scoring · semantic · intelligence · hiring · recruiter ·    │
        │    pipeline · reasoning · ingestion · insights · comparison ·  │
        │    talent_pool · interview · filtering · dashboard · llm       │
        └────────────────────────────────┬──────────────────────────────┘
                                         │  (no dependency upward)
        ┌────────────────────────────────┴──────────────────────────────┐
        │  Enterprise Platform  src/platform/  (additive · isolated)     │
        │    tenancy · auth · rbac · security · runtime · integrations · │
        │    deployment · audit · config · subscription · storage · …    │
        └───────────────────────────────────────────────────────────────┘
```

### Ranking pipeline (Recruiter Console)

```
  Job Description ─▶ parse + analyze ─▶ Job Profile
        │
  Candidates ─▶ Rule Ranking (10 components) ─▶ top pool
        │
        └─▶ Semantic embeddings (BGE) ─▶ Hybrid score (rule + cosine)
                    │
                    ▶ Explainability ─▶ Dashboard · Search · Cards · Export
```

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full layered map, dependency graph,
and module registry.

---

## Technology Stack

| Area | Technology |
|---|---|
| UI / App | Streamlit |
| Language | Python 3.11+ (3.13 recommended) |
| Embeddings | `sentence-transformers` (`BAAI/bge-small-en-v1.5`), cross-encoder & KeyBERT (optional stages) |
| Vector search | FAISS (`faiss-cpu`) |
| Data / ML | pandas, NumPy, scikit-learn, PyTorch |
| Validation | Pydantic |
| Optional LLM providers | OpenAI, Anthropic Claude, Google Gemini, Ollama (SDKs imported lazily) |
| Tooling | ruff (lint + format), pytest, mypy |
| Packaging / Deploy | Docker (multi-stage), Docker Compose, Kubernetes manifests |

---

## Project Structure

```
TalentMind/
├── app.py                     Streamlit entry point (thin orchestrator, 17 workspaces)
├── rank.py                    CLI batch-ranking entry point
├── requirements.txt           runtime dependencies
├── requirements-dev.txt       test-only dependencies
├── pyproject.toml             ruff / pytest / mypy config + package metadata
├── Dockerfile                 multi-stage production image
├── docker-compose*.yml        base / dev / prod compose files
├── k8s/                       Kubernetes manifests (+ Helm structure notes)
├── .github/workflows/         CI + Release pipelines
├── docs/                      architecture, guides, API, security, deployment, …
├── data/raw/                  input data (job_description.txt; candidates.jsonl is local)
├── tests/                     761 tests (unit · architecture · UI AppTests)
└── src/
    ├── ai/                    AI providers, 12 agents, committee, orchestration, copilot
    ├── platform/              enterprise SaaS platform (additive, isolated)
    ├── scoring/               10-component rule engine + hybrid scoring
    ├── semantic/              embeddings, FAISS index, recruiter search, re-ranker
    ├── intelligence/          JD parsing/analysis, candidate/risk/timeline engines
    ├── hiring/ recruiter/ pipeline/ reasoning/ ingestion/ insights/
    ├── comparison/ talent_pool/ interview/ filtering/ dashboard/ llm/ models/ utils/
    └── ui/                    Streamlit workspaces & components
```

A file-by-file map lives in [`docs/PROJECT_STRUCTURE.md`](docs/PROJECT_STRUCTURE.md).

---

## Installation

**Requirements:** Python 3.11+ (3.13 recommended), ~4 GB RAM (8 GB with the ML stack).
The first run downloads the sentence-transformer / KeyBERT model weights from Hugging Face and
caches them locally; the AI *agent* layer runs offline regardless.

```bash
# 1. Clone
git clone https://github.com/your-org/talentmind.git
cd talentmind

# 2. Create & activate a virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt   # optional: to run the test suite
```

Full platform-specific instructions (Windows / Linux / macOS / Docker / Compose / Kubernetes /
offline / enterprise) are in [`docs/INSTALL.md`](docs/INSTALL.md).

---

## Quick Start

```bash
# Launch the Streamlit application
streamlit run app.py
# → open http://localhost:8501
```

Batch ranking from the command line:

```bash
python rank.py
# reads data/raw/*, writes outputs/top_100_candidates.{json,csv}
```

With Docker:

```bash
docker compose up          # app on http://localhost:8501
```

---

## Configuration

TalentMind is configured entirely through environment variables and is **offline-by-default**.

| Variable | Default | Purpose |
|---|---|---|
| `TALENTMIND_AI_PROVIDER` | `local` | AI provider: `local`, `openai`, `claude`, `gemini`, `ollama`. |
| `TALENTMIND_AI_MODEL` | provider default | Override the model name. |
| `TALENTMIND_AI_STRICT` | `false` | Fail instead of falling back to the deterministic provider. |
| `TALENTMIND_AI_CACHE_ENABLED` | `true` | Cache AI results to `data/ai_cache/`. |
| `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / `GOOGLE_API_KEY` | — | Keys for optional cloud providers. |
| `OLLAMA_HOST` | `http://localhost:11434` | Local Ollama endpoint. |

With the default `local` provider, every AI narrative is produced by a **deterministic
composer** — a pure function of the deterministic engines' output — so results are reproducible
and require no network. See [`docs/CONFIGURATION.md`](docs/CONFIGURATION.md) for the full matrix.

---

## AI Platform Overview

The `src/ai/` layer turns deterministic engine output into executive-quality narrative — and
nothing more. Its guarantees are enforced in code:

- **Score-free** — `SafetyGuard.assert_schema_is_score_free` rejects any AI output schema with a
  score/rating/percent field. The AI *explains* rankings; it never *computes* them.
- **Offline-by-default** — the `local` provider composes schema-valid JSON deterministically
  from evidence. No network, no hallucination.
- **Provider-agnostic** — OpenAI / Claude / Gemini / Ollama plug in behind one interface, with
  automatic, safe fallback to the deterministic provider.
- **Cached & telemetered** — every result is cache-keyed on agent/prompt/provider/model/subject
  and logged to append-only JSONL telemetry.

Details: [`docs/AI_PLATFORM.md`](docs/AI_PLATFORM.md).

### Multi-Agent Platform

The **AI Hiring Committee** convenes 7 independent reviewers (Resume Expert, JD Expert,
Technical Hiring Manager, Risk Officer, Career Growth Specialist, Interview Lead, Hiring
Analyst). Each reads one slice of evidence, no reviewer sees another's opinion, and the outcome
is an **evidence-weighted consensus** — not a majority vote — narrated by a Committee Chair.

The **orchestration framework** compiles a goal into a task DAG and executes it with capability
routing, parallel layers, retries, and fallback. See
[`docs/MULTI_AGENT_SYSTEM.md`](docs/MULTI_AGENT_SYSTEM.md) and
[`docs/ENTERPRISE_AGENTS.md`](docs/ENTERPRISE_AGENTS.md).

---

## Enterprise Governance, Runtime & Security

- **Governance** — compensation transparency, pay-equity fairness checks, hiring-compliance
  workflow governance, and full decision-journey audit/explainability. Governance agents are
  *data-gated*: they mark unavailable data honestly and never fabricate legal conclusions.
- **Runtime** — jobs, workers, execution strategies, resilience, health, and load control:
  [`docs/RUNTIME.md`](docs/RUNTIME.md).
- **Security** — identity, RBAC + ABAC, hash-chained audit, secrets, threat detection, and
  compliance catalogues: [`docs/SECURITY.md`](docs/SECURITY.md).

---

## Deployment

```bash
# Docker
docker build -t talentmind:1.0.0 .
docker run -p 8501:8501 talentmind:1.0.0

# Docker Compose (base / dev / prod)
docker compose -f docker-compose.yml up
docker compose -f docker-compose.dev.yml up
docker compose -f docker-compose.prod.yml up

# Kubernetes
kubectl apply -f k8s/          # apply in numeric order — see k8s/README.md
```

Deployment, scaling, backup/recovery, and production-readiness validation are documented in
[`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md), [`docs/OPERATIONS.md`](docs/OPERATIONS.md), and
[`docs/DISASTER_RECOVERY.md`](docs/DISASTER_RECOVERY.md).

---

## Screenshots

> 📸 **Placeholder.** Capture the running app and drop images into
> [`docs/assets/`](docs/assets/), then embed them here. Suggested captures:
>
> - `docs/assets/screenshot-console.png` — Recruiter Console (ranked candidates + score breakdown)
> - `docs/assets/screenshot-committee.png` — AI Hiring Committee (reviewers + consensus)
> - `docs/assets/screenshot-platform.png` — Platform Administration (tenants + audit)
>
> Once added, replace this block with image embeds pointing at those files under `docs/assets/`.

---

## Demo

A guided demo script — recruiter, executive, committee, governance, and copilot flows with
suggested timings — is in [`docs/DEMO_GUIDE.md`](docs/DEMO_GUIDE.md).

---

## Documentation

| Guide | Description |
|---|---|
| [INSTALL](docs/INSTALL.md) | Installation across Windows/Linux/macOS/Docker/K8s/offline |
| [USER_GUIDE](docs/USER_GUIDE.md) | Using the 17 workspaces |
| [DEVELOPER_GUIDE](docs/DEVELOPER_GUIDE.md) | Local dev, standards, extension points |
| [ARCHITECTURE](docs/ARCHITECTURE.md) | Layered architecture & module registry |
| [PROJECT_STRUCTURE](docs/PROJECT_STRUCTURE.md) | Directory & file map |
| [AI_PLATFORM](docs/AI_PLATFORM.md) | Providers, core runner, safety, caching |
| [MULTI_AGENT_SYSTEM](docs/MULTI_AGENT_SYSTEM.md) | Orchestration & committee |
| [ENTERPRISE_AGENTS](docs/ENTERPRISE_AGENTS.md) | Every agent, in detail |
| [API_REFERENCE](docs/API_REFERENCE.md) | Service & API contracts |
| [CONFIGURATION](docs/CONFIGURATION.md) | Environment variables |
| [INTEGRATIONS](docs/INTEGRATIONS.md) | Integration framework & providers |
| [RUNTIME](docs/RUNTIME.md) | Runtime platform |
| [SECURITY](docs/SECURITY.md) | Security & governance |
| [DEPLOYMENT](docs/DEPLOYMENT.md) | Deployment topologies |
| [OPERATIONS](docs/OPERATIONS.md) | Day-2 operations |
| [TROUBLESHOOTING](docs/TROUBLESHOOTING.md) | Common issues |
| [FAQ](docs/FAQ.md) | Frequently asked questions |
| [DEMO_GUIDE](docs/DEMO_GUIDE.md) | Presentation flows |
| [CHANGELOG](docs/CHANGELOG.md) | Version history |
| [CONTRIBUTING](docs/CONTRIBUTING.md) | Contribution workflow |
| [CODE_OF_CONDUCT](docs/CODE_OF_CONDUCT.md) | Community standards |

---

## Roadmap

- [x] Multi-agent recruiter copilot
- [x] Candidate comparison & talent-pool segmentation
- [x] Interview question generation (Interview Studio)
- [x] Enterprise platform (multi-tenancy, RBAC, runtime, deployment)
- [ ] Live HRIS/ATS connectors over the existing provider interfaces
- [ ] Resume parsing from PDF
- [ ] Persistent (PostgreSQL) storage adapters behind the repository interfaces
- [ ] Bound REST server in front of the in-process API contracts
- [ ] Real-time analytics & team collaboration workflows

---

## Contributing

Contributions are welcome. Please read [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md) and the
[`docs/CODE_OF_CONDUCT.md`](docs/CODE_OF_CONDUCT.md). In short: run `ruff format .`,
`ruff check .`, and `pytest -q` before opening a pull request, and keep the additive-architecture
rule intact.

---

## License

Released under the **MIT License** (see `pyproject.toml`). Add a `LICENSE` file with your
organization's copyright line before publishing.

---

## Acknowledgements

Built with [Streamlit](https://streamlit.io), [FAISS](https://github.com/facebookresearch/faiss),
[sentence-transformers](https://www.sbert.net), [Pydantic](https://pydantic.dev), and the
BAAI BGE embedding models.

---

## Contact

Open an issue on the repository for questions, bugs, or feature requests. For enterprise
inquiries, use the contact channel configured in your fork.

<div align="center">
<sub>TalentMind 1.0.0 — Enterprise Edition · Explainable · Deterministic · Offline-first</sub>
</div>
