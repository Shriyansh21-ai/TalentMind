# TalentMind — Phase 2, Milestone 1 Report

**Career Timeline Intelligence + Resume Risk Detection**

Status: ✅ Complete and verified (app boots, all 9 profile tabs render, no
regressions).

---

## 1. Overview

Milestone 1 evolves TalentMind from a ranking system into a **Candidate
Intelligence Platform** by adding two new, fully heuristic (no-LLM) analysis
engines and surfacing them through the modular UI:

1. **Career Timeline Intelligence** — infers trajectory, promotion velocity,
   stability, domain focus, employer-quality trend and a recruiter narrative
   from raw career history.
2. **Resume Risk Detection** — a hiring-manager-style risk assessment that
   surfaces gaps, instability, stagnation, shallow impact and missing
   leadership/communication signals, and generates concrete validation
   questions.

No existing business logic, scoring formula, ranking algorithm, embedding,
FAISS index or CrossEncoder was modified. The work is purely additive, except
for three **pre-existing crash bugs** discovered during verification and fixed
minimally (see §7).

---

## 2. Architecture

The new engines follow the project's existing separation of concerns:
**pure analysis logic in `src/intelligence/…`**, **presentation in `src/ui/…`**,
and **cached orchestration wrappers in `src/ui/helpers.py`** — the same pattern
introduced in Phase 1 for `build_candidate_intelligence`.

```
Candidate (pydantic model)
        │
        ├─ build_career_timeline() ──► CareerTimelineAnalysis ─┐
        │      (src/intelligence/timeline)                     │
        │                                                       ├─► render_profile_tabs()
        ├─ build_risk_report() ───────► RiskReport ─────────────┘        (src/ui)
        │      (src/intelligence/risk)
        │
        └─ shared primitives: src/intelligence/common/career_utils.py
```

Both engines are deterministic, side-effect free, and depend only on the
`Candidate` data model + shared `career_utils`. UI renderers receive
**precomputed** dataclasses (dependency injection) and never call the engines
directly, keeping presentation and logic decoupled and testable.

---

## 3. New folders

| Folder | Purpose |
|---|---|
| `src/intelligence/common/` | Shared, reusable career-analysis primitives used by both new engines (single source of truth — no duplicated heuristics). |
| `src/intelligence/timeline/` | Career Timeline Intelligence engine. |
| `src/intelligence/risk/` | Resume Risk Detection engine. |

(Consistent with the repo's implicit-namespace-package convention — no
`__init__.py`, matching every other package under `src/`.)

---

## 4. New files

### Analysis engines (business logic — no LLM, no I/O)

| File | Responsibility |
|---|---|
| `src/intelligence/common/career_utils.py` | Date parsing, tenure math, employment-gap detection, title seniority ranking, management/leadership detection, company-size tiering, domain consistency, promotion counting, measurable-achievement detection, and the shared keyword vocabularies (`OUTDATED_TECHNOLOGIES`, leadership verbs, etc.). |
| `src/intelligence/timeline/models.py` | `CareerTimelineAnalysis` dataclass (all requested fields). |
| `src/intelligence/timeline/analyzer.py` | `build_career_timeline(candidate)` — trajectory scoring, promotion velocity, stability, leadership progression, company-quality trend, narrative + strength/concern signals. |
| `src/intelligence/risk/models.py` | `RiskReport` dataclass (all requested fields). |
| `src/intelligence/risk/analyzer.py` | `build_risk_report(candidate)` — six weighted sub-risks, aggregate score/level, red flags, positive signals, and recruiter validation questions. |

### UI (presentation only)

| File | Responsibility |
|---|---|
| `src/ui/components.py` | Reusable Streamlit building blocks: `render_cards`, `render_meter`, `render_level_badge`, `render_trend` — used by both new tabs to avoid duplicated card/meter/badge code. |
| `src/ui/timeline_tab.py` | `render_timeline_tab(analysis)` — progress meters, trajectory stats, career story, strength/concern cards. |
| `src/ui/risk_tab.py` | `render_risk_tab(report)` — overall risk meter, level badge, 6-dimension breakdown, red-flag/positive-signal cards, validation questions. |

### Documentation

| File | Responsibility |
|---|---|
| `PHASE2_MILESTONE1_REPORT.md` | This report. |

---

## 5. Integration points (files extended — additive only)

| File | Change |
|---|---|
| `src/ui/helpers.py` | Added `get_career_timeline()` and `get_risk_report()` — `@st.cache_data` wrappers keyed by `candidate_id`, mirroring the existing `get_candidate_intelligence` cache pattern (Module 6). |
| `src/ui/candidate_card.py` | Computes `timeline` and `risk` via the cached wrappers inside the candidate expander and injects them into `render_profile_tabs`. |
| `src/ui/profile_tabs.py` | Reorganized into the requested **9-tab** layout, delegating the two new tabs to their renderers. All previous content preserved and redistributed (see §6). |

**`app.py` was not touched** — its size is unchanged (Module 3 requirement met).
Integration happens entirely in the UI layer.

---

## 6. Profile tab structure (9 tabs)

| # | Tab | Content | Source |
|---|---|---|---|
| 1 | 📄 Summary | AI Recruiter Summary + Professional Summary | existing (relocated) |
| 2 | 🧠 Candidate Intelligence | Intelligence metric grid, progress, strengths, areas to validate | existing (relocated) |
| 3 | 📈 Career Timeline | **NEW** — Module 1 + visuals | new |
| 4 | 🚨 Risk Analysis | **NEW** — Module 2 + visuals | new |
| 5 | 📊 Skills | Skill list + JD Gap Analysis | existing (relocated) |
| 6 | 💼 Career History | Chronological role list | existing |
| 7 | 📄 Explainability | Full explainability JSON | existing |
| 8 | 🎯 Hiring Recommendation | Intelligence-engine recommendation **and** rule-based recommendation **and** recruiter actions | existing (consolidated) |
| 9 | 🗓 Interview Plan | Placeholder + preview of recommendation focus areas | new placeholder |

"Similar Candidates" continues to render beneath the tabs. Both distinct hiring
recommendation engines (`generate_hiring_recommendation` and
`get_hiring_recommendation`) are preserved — nothing was removed.

---

## 7. Pre-existing bugs found during verification and fixed

Verification (via Streamlit `AppTest`, which executes the full render path)
surfaced three latent crashes in **pre-existing, untracked** code. Each would
crash the app the moment a candidate card rendered — they were never previously
exercised because the app had not been driven past the "Rank" click. Fixes are
surgical field/argument corrections; **no scoring weight, threshold or formula
was changed.**

| File | Bug | Fix |
|---|---|---|
| `src/scoring/explainability.py` | `get_skill_gap(candidate,)` called with the required `jd_text` argument missing (trailing-comma stub). | Pass `""` (the blank the author implied). Affects only the explainability dict's gap fields; the Skills tab still computes the real gap with the actual JD. |
| `src/intelligence/candidate/hiring_risk.py` | Read `candidate.profile.notice_period` — no such field on `Profile`. | Use `candidate.redrob_signals.notice_period_days` (the real field); `> 60` threshold and risk weights unchanged. |
| `src/intelligence/candidate/weaknesses.py` | (Fixed in Phase 1) Was a copy-paste of `strengths.py`; drafted `weaknesses()` heuristic. | Retained. |

---

## 8. Design decisions

- **Pure heuristics, no LLM** — per spec. Every signal is explainable and
  deterministic, which is essential for enterprise auditability and for caching.
- **Shared `career_utils`** — both engines depend on one implementation of date
  math, seniority ranking, company tiering, etc. This eliminates duplicated
  heuristics and gives a single place to tune vocabularies/thresholds.
- **Dataclasses for outputs** — lightweight, typed, picklable (so
  `st.cache_data` works cleanly), and independent of the existing pydantic
  engine models.
- **Dependency injection into renderers** — UI functions receive precomputed
  analyses, so they are trivially unit/AppTest-testable and never trigger heavy
  computation themselves.
- **Cache keyed by `candidate_id`** — timeline and risk each run at most once
  per candidate per session (Module 6), reusing the Phase 1 pattern.
- **Graceful degradation** — every heuristic tolerates empty/sparse data
  (no career history, no skills, unparseable dates) without raising; renderers
  show empty-state captions.
- **Thresholds centralized** — tuning constants live at the top of each analyzer
  as named module constants, not scattered magic numbers.
- **Additive UI** — the 9-tab reorganization preserves every prior element;
  the only removals were the redundant duplicates already eliminated in Phase 1.

---

## 9. Future extension points

- **Interview Plan tab (tab 9)** is a deliberate placeholder wired to the
  recommendation's focus areas — the natural home for a future structured
  interview-plan engine (`src/intelligence/interview/`).
- **`career_utils`** is the extension surface for richer signals (e.g. company
  prestige tiers from an external dataset, industry taxonomies, tenure
  seasonality).
- **Risk weights** (`_WEIGHTS` in `risk/analyzer.py`) and **timeline weights**
  (`_timeline_score`) are isolated and can be exposed as configurable policy.
- **Components** (`src/ui/components.py`) can grow into a shared design-system
  module (chips, timelines, gauges) reused across all tabs.
- Both engines are pure functions — they can be lifted into a batch/offline
  precompute job or a service API without change.

---

## 10. Known limitations

- Heuristics are keyword/threshold based; they infer signals from titles,
  descriptions, industries and company sizes, and can mis-classify unusual
  titles or sparse descriptions. Thresholds are tuned for the current dataset.
- `company_quality_trend` uses company **size** as a proxy for employer quality
  (no external prestige signal yet).
- Consulting/startup/enterprise detection relies on company-size bands and a
  small keyword list; ambiguous employers may be missed.
- `src/intelligence/candidate/career_growth.py` (pre-existing, untouched) can
  raise on candidates with **empty** career history (`max([])`). Not triggered
  by ranked top candidates in testing; flagged here rather than modified to
  respect the "do not change business logic" constraint. Recommend a one-line
  guard in a future maintenance pass.
- The Interview Plan tab is a placeholder (by design for this milestone).

---

## 11. Verification performed

- ✅ `py_compile` on all new/changed files.
- ✅ Import graph resolves; **no circular imports** (`import app` succeeds).
- ✅ Both engines run correctly on real candidate records from
  `data/raw/candidates.jsonl` (scores in range, valid levels, sensible output).
- ✅ Streamlit `AppTest` renders **all 9 profile tabs** for a real candidate
  with **no exceptions** (24 metrics, colored cards, JSON block present).
- ✅ `streamlit run app.py` boots cleanly (0 errors) with all new modules loaded.
- ✅ Recruiter search and export modules unchanged and still import correctly.
