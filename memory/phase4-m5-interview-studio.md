---
name: phase4-m5-interview-studio
description: TalentMind Phase 4/M5 InterviewStudioAgent — final hiring-lifecycle agent at src/ai/agents/interview_studio
metadata:
  type: project
---

Phase 4 / Milestone 5 built the **Enterprise AI Interview Studio** — the final
business agent — at `src/ai/agents/interview_studio/`, mirroring the
ExecutiveHiringReport pattern ([[phase4-m3-hiring-committee]]). Turns existing
intelligence into a complete personalized interview package (strategy, adaptive
roadmap, technical/behavioral/role-specific questions, risk validations, 10-dim
rubrics, decision matrix, feedback forms, live-assistant hooks, charts). Consumes
only cached outputs; modifies no engine. Non-obvious facts:

- **Reuses committee `gather_evidence`:** `InterviewStudioEngine.build()`
  (`report.py`) calls `src.ai.committee.committee.gather_evidence(candidate, jd,
  insights_fn, ai_runner)` for the cached resume/JD/insights + deterministic
  `InterviewPlan`, optionally runs the committee, then assembles everything. Same
  DI seams as ExecutiveReportBuilder.
- **Score-free constraint:** `InterviewStudioNarrative` (BaseAIResponse) top level
  has NO score/rating/percent/confidence_value; `readiness_label` is a qualitative
  string. Numeric package layers live in dataclasses.
- **Role paths** (`templates/`): `detect_role(*hints)` longest-alias match, but the
  `generalist` DEFAULT_ROLE is SKIPPED in the loop (fallback only) — else its
  generic "engineer" alias beats "backend". Depth auto-chosen from seniority
  (senior/leadership -> deep loop).
- **Auto-registration on import of agent.py:** AI registry (`interview_studio`) +
  composer + orchestration (RunnerAgent, capabilities `["interview_studio",
  "interview_plan","interview_generation"]`). Own prompt loader at
  `src/ai/agents/interview_studio/prompts/`.
- **Copilot (additive):** NEW `Intent.INTERVIEW_STUDIO` distinct from the existing
  `GENERATE_INTERVIEW_PLAN` (lightweight `interview` tool — left untouched).
  Patterns avoid "interview packet" (that's EXECUTIVE_REPORT's named packet — used
  "interviewer packet" instead to avoid the tie collision). `interview_studio_tools.py`
  `InterviewStudioTool` + narrator `_summarize_interview_studio` + follow-ups +
  single_intents action set.
- **UI:** `src/ui/interview_studio_tab.render_interview_studio_workspace()` wired as
  8th app.py workspace ("Interview Studio"); 11 tabs.

Tests: `pytest tests/ -p no:faulthandler` (adds test_interview_studio.py = 39,
test_interview_studio_ui.py = 2). See PHASE4_MILESTONE5_REPORT.md.
[[phase4-m1-resume-agent]] [[phase4-m2-jd-agent]]
