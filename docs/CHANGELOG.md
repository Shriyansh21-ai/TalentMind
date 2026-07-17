# Changelog

All notable changes to TalentMind are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] — 2026-07-17 — Enterprise Edition

First production release. TalentMind combines a deterministic candidate-ranking core, a
semantic search layer, a multi-agent AI reasoning layer, and an additive enterprise SaaS platform.

### Added
- **Business core** — 10-component rule scoring engine, hybrid rule+semantic scoring, FAISS
  recruiter search, explainability, candidate/risk/timeline intelligence, talent-pool
  segmentation, hiring pipeline state machine, filtering, comparison, and dashboards.
- **AI platform** (`src/ai`) — provider abstraction (offline `local` default plus optional
  OpenAI/Claude/Gemini/Ollama), a generic agent runner with caching, telemetry, and a runtime
  `SafetyGuard` that structurally forbids AI-emitted scores.
- **AI agents** — Hiring Analyst, Resume, JD, Interview Studio, Executive Report, Compensation
  Governance, Pay Equity Guardian, Hiring Compliance, Hiring Audit, Hiring Intelligence, Recruiter
  Copilot, and Committee Chair.
- **Multi-agent orchestration** — deterministic planner, DAG workflow engine, capability routing,
  and the AI Hiring Committee (7 reviewers → evidence-weighted consensus).
- **Enterprise platform** (`src/platform`) — multi-tenancy, authentication (PBKDF2 + rotating
  sessions), RBAC + ABAC, tamper-evident hash-chained audit, runtime platform (jobs/workers/
  resilience), integration framework, and deployment platform. Isolation from the business core is
  enforced by architecture tests.
- **Delivery** — multi-stage Dockerfile, Docker Compose (base/dev/prod), Kubernetes manifests, and
  CI/Release GitHub Actions workflows.

### Changed (1.0.0 production-hardening pass)
- Rewrote `README.md` to accurately reflect all three layers, with an explicit scope note that
  external connectors are offline reference interfaces and there is no bundled HTTP server.
- Authored a complete documentation suite under `docs/` (user, developer, architecture, API, AI
  platform, multi-agent, enterprise agents, security, runtime, integrations, deployment,
  operations, configuration, troubleshooting, FAQ, demo, project structure).
- Applied a repository-wide code-quality pass: ruff lint auto-fixes (unused imports, import
  ordering, typing modernization, trailing newlines) and formatting across the codebase, with the
  full test suite verified green (no behavior changes).
- Repointed CI documentation-validation and the release artifact list away from
  non-existent `PHASE6_MILESTONE*_REPORT.md` files onto the real documentation set (fixes a broken
  CI job).
- Expanded `.gitignore` to cover `.claude/` and `.ruff_cache/`.

### Removed
- Verified dead code with zero inbound references: `src/scoring/candidate_score.py` (stub),
  `src/utils/jd_analyzer.py` (unused keyword dict), `src/ai/memory/session.py` (unused memory
  class), `src/semantic/cross_encoder_reranker.py` (unwired re-ranker that eagerly loaded a model),
  and `src/ai/agents/compensation/executive_summary.py` (unused module with a stale docstring).
- Internal, non-user-facing artifacts: `REPOSITORY_HEALTH.md` (a regenerable status report) and the
  `memory/` directory of development phase notes.

### Notes
- The AI agent layer runs fully offline and deterministically by default.
- The core ranking downloads embedding models from Hugging Face on first use, then runs offline.
- All enterprise-platform persistence is in-memory; storage/connector interfaces are provided as
  seams for real backends.

[1.0.0]: https://github.com/your-org/talentmind/releases/tag/v1.0.0
