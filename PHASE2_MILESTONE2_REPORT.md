# TalentMind — Phase 2 / Milestone 2 Report
## From Candidate Intelligence System → Enterprise Hiring Workspace

**Status:** ✅ Complete and verified (38 automated tests passing, app boots via
Streamlit `AppTest`, imports resolve, no circular dependencies, no regressions).

This milestone extends TalentMind with a full enterprise hiring workspace —
pipeline management, candidate comparison, talent-pool segmentation, deterministic
interview intelligence, a Plotly analytics dashboard, and smart filtering that
composes with the existing FAISS semantic search — **without modifying any of the
existing, protected business logic**.

---

## 1. Architecture

### 1.1 Guiding principle — *extend, never rewrite*

Every protected engine was treated as a black box and consumed through its
existing public interface:

- Ranking Engine, Rule Scoring, Semantic Search, Cross Encoder, FAISS Search
- Candidate Intelligence, Timeline Intelligence, Risk Detection
- Hiring Recommendation, AI Recruiter Summary, Explainability

None of these files were touched. The new modules read their outputs and
re-shape them for new recruiter surfaces.

### 1.2 The keystone: a shared insight bundle

The new workspace surfaces (comparison, segmentation, interview plans, dashboard,
filters) all need the *same* expensive per-candidate signals. Rather than let
each module re-invoke the intelligence / timeline / risk engines independently
(the single most expensive computation in the platform), a new foundation module
computes them **once** per candidate and shares the result:

```
                 ┌────────────────────────────┐
                 │   src/insights/builder.py   │  build_insights(candidate, jd)
                 │   (pure, no Streamlit)      │
                 └──────────────┬─────────────┘
                                │ CandidateInsights
        ┌───────────┬──────────┼───────────┬────────────┬───────────┐
        ▼           ▼          ▼           ▼            ▼           ▼
   comparison   talent_pool  interview   dashboard    filtering   candidate_card
```

The UI layer wraps `build_insights` in `st.cache_data` (`get_insights` in
`src/ui/helpers.py`), keyed by `(candidate_id, jd, match_score)`, so the engines
run **at most once per candidate per session** across the entire workspace *and*
the candidate cards.

### 1.3 Layering

| Layer | Rule |
|-------|------|
| **Domain logic** (`src/pipeline`, `src/comparison`, `src/talent_pool`, `src/interview`, `src/dashboard`, `src/filtering`, `src/insights`) | Pure Python, **no Streamlit import**, fully unit-testable, deterministic. |
| **Presentation** (`src/ui/*`) | Streamlit only. Consumes domain output; no scoring/ranking. |
| **Orchestration** (`app.py`) | Thin. Gained exactly **one import + one call**. |

---

## 2. New folders & modules

```
src/
├── insights/                     # Shared foundation (NEW)
│   ├── models.py                 # CandidateInsights bundle
│   └── builder.py                # build_insights() — composes existing engines
│
├── pipeline/                     # Module 1 — Hiring Pipeline Engine (NEW)
│   ├── models.py                 # PipelineStage, Priority, CandidatePipelineStatus,
│   │                             #   StageEvent, declarative transition rules
│   ├── engine.py                 # move_candidate/update_stage/add_note/
│   │                             #   assign_recruiter/change_priority/add_tag (validated)
│   └── store.py                  # PipelineStore — JSON persistence (own file)
│
├── comparison/                   # Module 2 — Comparison Workspace (NEW)
│   ├── models.py                 # ComparisonRow, ComparisonReport
│   └── builder.py                # build_comparison() — up to 5 candidates
│
├── talent_pool/                  # Module 3 — Talent Pool Segmentation (NEW)
│   ├── models.py                 # TalentPool enum, PoolAssignment
│   └── segmentation.py           # deterministic segment/filter/count
│
├── interview/                    # Module 4 — Interview Intelligence (NEW)
│   ├── models.py                 # InterviewPlan dataclass (9 fields)
│   └── planner.py                # build_interview_plan() — deterministic, no LLM
│
├── dashboard/                    # Module 5 — Recruiter Dashboard (NEW)
│   ├── analytics.py              # pure aggregations (counts/pairs/value-lists)
│   └── charts.py                 # Plotly figure builders (shared visual system)
│
├── filtering/                    # Module 6 — Smart Filtering (NEW)
│   ├── models.py                 # FilterCriteria
│   └── engine.py                 # apply_filters() — composes with FAISS via allowed_ids
│
└── ui/                           # Module 7 — UI integration
    ├── workspace.py              # (NEW) enterprise workspace orchestrator (tabs)
    ├── workspace_state.py        # (NEW) session-state helpers (compare shortlist)
    ├── analytics_dashboard.py    # (NEW) dashboard UI
    ├── comparison_view.py        # (NEW) comparison UI (matrix + qualitative)
    ├── talent_pool_view.py       # (NEW) pools UI (composition + drill-down)
    ├── filters_panel.py          # (NEW) smart filters UI (+ lazy FAISS gate)
    ├── pipeline_controls.py      # (NEW) per-card pipeline controls
    ├── interview_tab.py          # (NEW) interview plan renderer
    ├── candidate_card.py         # (MODIFIED) uses shared insights + compare + pipeline
    ├── profile_tabs.py           # (MODIFIED) Interview Plan tab now renders real plan
    └── helpers.py                # (MODIFIED) added cached get_insights()

tests/                            # Module 10 — verification (NEW)
├── conftest.py                   # synthetic Candidate factory (no dataset / no torch)
├── test_pipeline.py             # 12 tests — transitions, validation, persistence
├── test_workspace_modules.py    # comparison/pools/interview/dashboard/filtering
├── test_app_boot.py             # Streamlit AppTest — app boots, guards work
└── test_ui_rendering.py         # renders every workspace surface (synthetic data)

app.py                            # (MODIFIED) one import + one call
PHASE2_MILESTONE2_REPORT.md       # (NEW) this document
```

**Files modified:** `app.py`, `src/ui/candidate_card.py`, `src/ui/profile_tabs.py`,
`src/ui/helpers.py`. **All four are presentation/orchestration only** — no protected
business logic was altered.

---

## 3. Module-by-module design decisions

### Module 1 — Hiring Pipeline Engine
- The funnel is modelled as an **explicit state machine**. Transition rules are
  declarative (`_ALLOWED_TRANSITIONS`, built from the funnel order): a candidate
  may advance one step, step back to any earlier active stage, or be
  parked/rejected from anywhere. Illegal moves raise `InvalidTransition`.
- Every mutation stamps an **audit trail** (`StageEvent`) and updates a derived
  coarse `status` (Active / Rejected / Hired / On Hold).
- **Dependency injection**: every engine function accepts an optional
  `PipelineStore` and `timestamp`, making the core deterministic and testable and
  keeping side-effects (I/O, clock) at the edges.
- **Zero-regression persistence**: the rich pipeline state lives in its own file
  (`data/pipeline_state.json`). The legacy `src/recruiter/pipeline.py` action
  store (the simple card buttons) is left completely untouched, so both coexist.

### Module 2 — Candidate Comparison Workspace
- `build_comparison` projects up to **5** insight bundles into a uniform
  `ComparisonReport`, computing the per-metric leader (risk is correctly treated
  as lower-is-better). The UI renders a metric matrix (🏆 leader highlighting)
  plus qualitative panels.

### Module 3 — Talent Pool Segmentation
- Deterministic, threshold-based segmentation across **three orthogonal axes**
  (readiness / shape / domain) so a candidate can belong to several pools.
- Domain keyword matching uses **alphanumeric-boundary matching** (not naive
  substring) so `"ml"` matches `"AI/ML"` but never `"html"`, and symbols like
  `"c++"` are matched literally. Every assignment carries a rationale string for
  explainability.

### Module 4 — Interview Intelligence
- `build_interview_plan` fills all **nine** `InterviewPlan` fields from heuristics
  over the insight bundle: technical topics blend proven skills with JD gaps;
  system-design scope scales with seniority; leadership depth scales with the
  leadership score; validation/risk-followups are sourced from the risk engine.
  **No LLM, fully deterministic** (verified by a determinism test).

### Module 5 — Recruiter Dashboard
- Clean split: `analytics.py` (pure aggregation) + `charts.py` (Plotly figures
  with one shared visual system + graceful empty-state placeholders).
- Delivers all ten required charts: hiring funnel, stage distribution, pipeline,
  risk, score, experience, top skills, location, company, recommendation.
- **Cost discipline**: field-only charts run over the full pool; engine-backed
  charts run over the bounded insight cohort; pipeline charts over persisted state.

### Module 6 — Smart Filtering
- `FilterCriteria` covers every requested dimension (experience, skills, company,
  location, risk, recommendation, pipeline stage, timeline/technical/leadership/
  career-growth/learning-velocity/skill-match).
- **Composes with FAISS**: pass semantic-search hit ids as `allowed_ids` and the
  structured filters apply *on top of* the semantic result set. The torch-heavy
  FAISS import is **lazy** — structured filtering never pulls in the ML stack.

### Module 7 — UI Integration
- `app.py` stays thin (one import, one call to `render_enterprise_workspace`).
- The workspace is organized into four tabs (Dashboard / Talent Pools / Smart
  Filters / Compare) to keep the page uncluttered.
- Candidate cards gained a **➕ Compare** toggle (session-state shortlist, capped
  at 5) and inline **pipeline controls** (valid-only stage moves, priority,
  recruiter, notes). The Profile view is otherwise unchanged; the previously-
  placeholder **Interview Plan tab now renders the real structured plan**.

---

## 4. Performance considerations (Module 8)

- **Single computation, shared everywhere.** `get_insights` is cached by
  `(candidate_id, jd, match_score)`; the intelligence/timeline/risk engines run
  once per candidate per session and are reused by the cards *and* the workspace.
- **Bounded intelligence cohort.** Engine-backed analytics/segmentation/filtering
  operate on the top `ANALYTICS_COHORT = 40` ranked candidates (configurable in
  `src/ui/workspace.py`). Cheap field-only charts still use the full pool. This
  keeps the workspace responsive on the 487 MB / ~100k-candidate dataset — the
  platform never computes intelligence for the whole database.
- **Lazy ML import.** The FAISS/torch dependency is only imported when a recruiter
  actually runs a semantic query.
- **Existing cache patterns reused.** `@st.cache_data` / `@st.cache_resource` and
  the `Candidate → candidate_id` hash-func pattern are followed exactly.

---

## 5. Verification (Module 10)

| Check | Result |
|-------|--------|
| Compile all modules (`compileall`) | ✅ |
| Imports resolve / no circular dependencies (full UI chain import) | ✅ |
| Pipeline engine (transitions, validation, persistence) — 12 tests | ✅ |
| Comparison / talent-pool / interview / dashboard / filtering — 16 tests | ✅ |
| Streamlit `AppTest` — app boots, title & sidebar render, JD guard works — 3 tests | ✅ |
| Workspace UI surfaces render without exception — 2 tests | ✅ |
| **Total** | **38 passed** |
| Profile / candidate cards / exports / recruiter search | ✅ unchanged / preserved |

Run: `pytest tests/ -p no:faulthandler`
(`-p no:faulthandler` silences a benign faiss/torch OpenMP traceback printed
during interpreter shutdown on Windows; results and exit code are unaffected.)

> **Note on the faiss/torch load order.** Per the project's known constraint,
> `app.py` imports `faiss` first. This was preserved, and each new test module
> imports `faiss` before torch. The lazy FAISS import in the filters panel also
> means the workspace never forces torch to load out of order.

---

## 6. Future extension points

- **Pipeline analytics come alive** once candidates are moved through stages —
  the funnel/stage/pipeline charts already read live `PipelineStore` state.
- **Bulk pipeline actions** (multi-select a pool → advance/assign in one action).
- **Persisted saved filters / saved searches** per recruiter.
- **Comparison export** (PDF/CSV of the comparison matrix).
- **Configurable talent-pool thresholds** surfaced in an admin panel (currently
  centralized constants in `segmentation.py`).
- **Interview plan export** to ATS / calendar.
- **Pluggable pipeline stages** — the transition map is data-driven and can be
  extended to bespoke funnels.

---

## 7. Technical debt / known limitations

- **Insight cohort is bounded (top 40).** Dashboard risk/score/recommendation
  charts describe the top-ranked cohort, not the entire database, by design (cost).
  A background pre-compute job could widen this without hurting responsiveness.
- **`PipelineStore` rewrites the whole JSON file per mutation.** Fine at recruiter
  scale (tens–hundreds of tracked candidates); would warrant a keyed store /
  database at very large scale.
- **`get_or_create` writes on first card view**, so simply viewing a card enrolls
  a candidate at `Applied`. This is intended (they enter the funnel) but means
  first render of N cards performs N small writes.
- **Two pipeline stores coexist** (legacy simple actions + new rich pipeline) to
  guarantee zero regression; a future milestone could unify them behind one API.
- **`pytest` was added as a dev/test dependency** (not previously present). It is
  test-only and not imported by the application.
