---
name: phase2-m2-workspace
description: TalentMind Phase 2/M2 enterprise workspace — architecture, test command, and the shared-insights + bounded-cohort patterns
metadata:
  type: project
---

Phase 2 / Milestone 2 added the **Enterprise Hiring Workspace** to TalentMind by
*extending only* (no protected engine was modified). Key non-obvious facts:

- **Shared insights foundation:** `src/insights/build_insights(candidate, jd)`
  composes the existing intelligence/timeline/risk/gap/explanation/summary/
  recommendation engines into one `CandidateInsights` bundle. The UI wraps it as
  `get_insights` (cached in `src/ui/helpers.py`). All new surfaces
  (comparison, talent_pool, interview, dashboard, filtering) and the candidate
  cards consume this ONE computation — never re-invoke the engines directly.
- **Bounded cohort:** engine-backed dashboard/segmentation/filtering run over the
  top `ANALYTICS_COHORT = 40` ranked candidates (`src/ui/workspace.py`), not the
  full ~100k dataset. Field-only charts use the full pool.
- **Pipeline has its OWN store** (`data/pipeline_state.json` via
  `src/pipeline/store.py`); the legacy `src/recruiter/pipeline.py` action store is
  left untouched — both coexist to guarantee zero regression.
- **Lazy FAISS import:** `src/ui/filters_panel.py` imports `recruiter_search`
  INSIDE `_semantic_gate`, not at module top, so the workspace never forces torch
  to load unless a semantic query is run. This also avoids the faiss/torch OpenMP
  segfault in test harnesses — see [[faiss-torch-import-order]].

**Run tests:** `./venv/Scripts/python.exe -m pytest tests/ -p no:faulthandler`
(38 tests). `-p no:faulthandler` hides a benign faiss/torch OpenMP traceback
printed at interpreter shutdown on Windows; exit code is still 0. `pytest` and
`plotly` were installed into the venv for this milestone.
