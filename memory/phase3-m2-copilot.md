---
name: phase3-m2-copilot
description: TalentMind Phase 3/M2 AI Recruiter Copilot — tool layer + copilot core on the AI Platform
metadata:
  type: project
---

Phase 3 / Milestone 2 built the **AI Recruiter Copilot** — the first application
on the AI Platform ([[phase3-m1-ai-platform]]). Non-obvious facts:

- **Tool layer at `src/ai/tools/`** wraps each deterministic engine 1:1 as a
  `BaseTool` (12 built-ins in `builtin.py`, auto-registered into the default
  `registry`). Tools reach data/engines through a `CandidateRepository` DI seam
  (`InMemoryCandidateRepository`) — the UI wires it to the loaded pool + FAISS
  (`search_fn=recruiter_search`); tests use synthetic candidates + keyword search.
  `ToolContext.insights_fn` = the UI's cached `get_insights`, so tools reuse the
  engine caches.
- **Copilot core at `src/ai/copilot/`** is UI-independent: `IntentClassifier`
  (weighted keyword pattern registry — NO if-else chains), `CopilotPlanner`
  (`tool_selector.py` maps intent→minimal tools; resolves candidate/comparison
  from `ConversationState`), `ToolRunner`, then the `RecruiterCopilotAgent`
  narrates ONLY structured tool outputs → `CopilotResponse` (score-free).
  `response_builder` adds deterministic 3 follow-ups + actions. `controller.py`
  `RecruiterCopilot.ask(session, message, jd)` is the entry point.
- **UI:** `src/ui/copilot_page.render_copilot(repository_factory, insights_fn, jd)`.
  Wired via a sidebar radio in `app.py` ("Recruiter Console" | "AI Recruiter
  Copilot"); repository built lazily on first message so the page renders instantly
  and AppTest never loads the 487MB dataset.
- **Actions** integrate with existing modules: `move_to_shortlist` calls the
  pipeline engine; navigational actions become in-conversation follow-ups.

Tests: `pytest tests/ -p no:faulthandler` → 82 passing (adds test_copilot.py,
test_copilot_ui.py). See PHASE3_MILESTONE2_REPORT.md. Extend by adding a `BaseTool`
+ `tool_selector` entry, or a `BaseAgent`; the copilot discovers them by name.
