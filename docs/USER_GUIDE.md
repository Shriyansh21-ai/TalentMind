# TalentMind — User Guide

This guide walks through the TalentMind application from a user's perspective. Launch it with:

```bash
streamlit run app.py     # http://localhost:8501
```

The left sidebar has a **Workspace** selector with 17 workspaces: one core Recruiter Console, 12
AI workspaces, and 4 platform workspaces. Each workspace is described below.

> **Data note:** the app reads its candidate pool from `data/raw/candidates.jsonl`. If you cloned
> the repo, provide your own candidate dataset in that JSONL format (one candidate object per
> line — see `src/models/candidates.py` for the schema). The job description is uploaded via the
> Recruiter Console sidebar. On first use the app downloads the sentence-transformer model.

---

## Recruiter Console (core)

The primary ranking workflow.

1. **Upload a job description** in the sidebar and click **Rank**.
2. TalentMind parses and analyzes the JD into a **Job Profile** and shows a job dashboard
   (complexity, hiring difficulty, skills, seniority).
3. Candidates are ranked by the **10-component rule score**, then the top pool is re-ranked by a
   **hybrid score** (rule + semantic cosine similarity).
4. Results render as: an enterprise workspace (analytics, talent-pool segmentation, filtering,
   comparison), a natural-language recruiter search, the top candidate cards (with score
   breakdowns and reasons), and an export panel (CSV / JSON).

**Recruiter search** accepts natural-language queries (e.g. *"ML engineer with RAG experience"*)
and returns the closest candidates via FAISS.

---

## AI workspaces

All AI workspaces are offline-by-default and produce **score-free, evidence-grounded** narratives.
They load on demand and cache results.

| Workspace | What it does |
|---|---|
| **AI Recruiter Copilot** | Conversational assistant. Ask about candidates in natural language; it classifies intent, runs the right deterministic tools, and narrates the results. Every fact traces to a tool. |
| **Multi-Agent Orchestration** | Inspect and run the orchestration framework — plan a goal into a task DAG and execute it. |
| **Resume Intelligence** | Recruiter-grade resume-quality analysis (structure, depth, achievements, ATS coverage, risks). Quality only — never a ranking. |
| **JD Intelligence** | Job-description intelligence (role level, technical shape, hiring intent, requirement hierarchy, market posture, quality/risk). |
| **AI Hiring Committee** | Convenes 7 independent reviewers → evidence-weighted consensus → chair decision. Choose a mode (balanced / optimistic / conservative). |
| **Executive Hiring Report** | Boardroom-grade one-page narrative synthesized from all intelligence; exportable (docx/html/pdf/ppt). |
| **Interview Studio** | Personalized interview plan: strategy, adaptive questions, rubrics, interviewer guides, decision matrix. |
| **Compensation Governance** | Explains and documents a defensible compensation *range* for HR/Finance/Legal approval — never predicts a fixed salary. |
| **Pay Equity Guardian** | Internal-fairness checks (compression, inversion, promotion equity). Data-gated; not a bias detector or legal engine. |
| **Hiring Compliance** | Checks whether a hiring workflow follows governance (steps, approvals, documentation, audit readiness). Data-gated; not legal advice. |
| **Hiring Audit** | Reconstructs the full decision journey with provenance, separating observed facts, inferred insights, AI recommendations, and human decisions. |
| **Hiring Intelligence** | Organizational workforce analytics (hiring health, bottlenecks, trends, KPIs). Cohort-level; never ranks individuals. |

---

## Platform workspaces

| Workspace | What it does |
|---|---|
| **Platform Administration** | Multi-tenant admin dashboard (organizations, users, roles, licenses, feature flags, seats, audit) seeded with demo tenants. |
| **Integration Marketplace** | Browse the HRIS/ATS/calendar/communication/document provider catalogue and connection lifecycle (offline reference providers). |
| **Runtime Operations** | Runtime platform view — jobs, workers, execution, health, load, resilience. |
| **Security & Operations Center** | Security platform view — identity, authorization, audit, secrets, monitoring, governance, compliance, incidents, analytics. |

---

## Tips

- **Everything is deterministic offline.** The same inputs always produce the same output; you can
  demo without network access.
- **Nothing is a black box.** Every card, committee opinion, and narrative names its evidence.
- **The AI never invents a score.** Scores come from the deterministic engines; the AI explains
  them.

See [`DEMO_GUIDE.md`](DEMO_GUIDE.md) for guided presentation flows and
[`TROUBLESHOOTING.md`](TROUBLESHOOTING.md) if something doesn't load.
