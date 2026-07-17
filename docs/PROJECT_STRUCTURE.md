# TalentMind — Project Structure

A map of the repository. See [`ARCHITECTURE.md`](ARCHITECTURE.md) for the layered design and
dependency rules.

```
TalentMind/
├── app.py                     Streamlit entry point (thin orchestrator, 17 workspaces)
├── rank.py                    CLI batch-ranking entry point
├── requirements.txt           runtime dependencies
├── requirements-dev.txt       test-only dependencies (pytest)
├── pyproject.toml             ruff / pytest / mypy config + package metadata
├── Dockerfile                 multi-stage production image
├── docker-compose.yml         base compose
├── docker-compose.dev.yml     development overrides
├── docker-compose.prod.yml    production overrides
├── .dockerignore .gitignore
├── .github/workflows/         ci.yml (lint/type/test/scan/docs/build), release.yml
├── k8s/                       Kubernetes manifests (00–10) + README + HELM_STRUCTURE
├── data/raw/                  input data (job_description.txt tracked; candidates local)
├── docs/                      this documentation suite
├── tests/                     761 tests (unit · architecture · UI AppTests)
└── src/                       application source (see below)
```

## `src/` — application source

### AI layer — `src/ai/`

```
src/ai/
├── providers/        provider abstraction: local (default, offline) · openai · claude · gemini · ollama
├── core/             BaseAgent, AgentRunner, AgentConfig, registry, response, context
├── config/           AISettings (environment-driven)
├── cache/            FileCache / NullCache + cache-key builder
├── telemetry/        append-only JSONL logger + in-memory ring
├── validators/       JSON validation + SafetyGuard (score-free enforcement)
├── prompts/          versioned Markdown prompt templates + loader
├── schemas/          BaseAIResponse + shared response schemas
├── memory/           BaseMemory + request-scoped ContextBuilder
├── services/         UI-facing facade (hiring_analyst_service)
├── tools/            engine-wrapping tools for the copilot (never reimplement logic)
├── copilot/          RecruiterCopilot: intent classification, planning, narration
├── orchestration/    domain-free multi-agent framework (planner, engine, delegation, registry)
├── committee/        AI Hiring Committee (7 reviewers → evidence-weighted consensus → chair)
└── agents/           the concrete business agents:
    ├── hiring_analyst.py           recruiter_copilot.py           analysis_interfaces.py (seam)
    ├── resume/  jd/  interview_studio/  executive_report/
    └── compensation/  pay_equity/  compliance/  audit/  hiring_intelligence/
```

### Enterprise platform — `src/platform/`

```
src/platform/
├── common/           base models, errors, ids, clock, repository (tenant isolation)
├── container.py      lazy DI container
├── bootstrap.py      composition root — build_platform()
├── demo.py           seeded demo platform
├── organizations/    org hierarchy (org → business unit → department → office)
├── tenancy/          multi-tenancy: context, resolver, middleware, isolation, cache, storage
├── auth/             local auth: PBKDF2 passwords, rotating sessions, identity seam, recovery
├── rbac/             12 roles, resource:action permissions, default-deny PolicyEngine
├── workspaces/       org-owned workspaces (projects, teams, pipelines, agent bindings)
├── config/           per-tenant feature flags, licensing, usage limits
├── subscription/     plans, quotas, seats (BillingHook seam — no payments)
├── notifications/    channels/templates/preferences (interface-only channels)
├── audit/            tamper-evident hash-chained audit trail
├── storage/          storage + vector-store interfaces (in-memory)
├── developer/        plugin/extension framework (hooks, extensions, SDK, marketplace)
├── api/              REST-ready contracts (responses, pagination, filtering, versioning, ratelimit, openapi)
├── integrations/     integration platform (M2): providers, gateway, webhooks, event bus, sync
├── runtime/          runtime platform (M3): jobs, workers, execution, cache, health, load, resilience
├── security/         security platform (M4): identity, authz (RBAC+ABAC), audit, secrets, monitoring, governance, compliance, threat, incidents, analytics
└── deployment/       deployment platform (M5): manager, config, backup, release, validation, benchmark, packaging
```

### Business core (deterministic)

```
src/
├── ingestion/     load candidates (JSONL) and job descriptions
├── models/        Candidate pydantic schema (profile, career, education, skills, signals)
├── scoring/       10-component rule engine + hybrid, explainability, recommendation, skill gap
├── semantic/      embeddings (BGE), FAISS index, recruiter search, similar candidates
├── intelligence/  JD parse/analyze, keyword/skill extraction, candidate/risk/timeline engines
├── hiring/        recommendation, offer prediction, salary band, interview focus
├── recruiter/     legacy candidate action store
├── pipeline/      hiring-funnel state machine (stages, transitions, store)
├── reasoning/     human-readable recruiter reason generation
├── insights/      shared aggregation (build_insights) consumed across the app
├── comparison/    candidate comparison reports
├── talent_pool/   deterministic talent-pool segmentation
├── interview/     deterministic interview-plan builder
├── filtering/     declarative candidate filtering engine
├── dashboard/     chart-ready aggregations
├── llm/           template-based recruiter summary (no external LLM)
├── utils/         dataset analyzer
└── ui/            Streamlit workspaces & components (sidebar, cards, tabs, workspace, export)
```

## Conventions

- **Models / Repository / Service** per platform module; interfaces before implementations.
- **Prompts** are versioned Markdown, never hard-coded in Python.
- **AI output schemas are score-free** (enforced at runtime).
- **`src/platform/*` never imports the business core** (enforced by architecture tests).
- Some business-core packages use PEP 420 implicit namespace packages (no `__init__.py`); the
  platform and agent packages use explicit `__init__.py`.
