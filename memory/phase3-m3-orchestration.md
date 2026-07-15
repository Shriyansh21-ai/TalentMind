---
name: phase3-m3-orchestration
description: TalentMind Phase 3/M3 Multi-Agent Orchestration Framework at src/ai/orchestration
metadata:
  type: project
---

Phase 3 / Milestone 3 built the **Multi-Agent Orchestration Framework** at
`src/ai/orchestration/` on top of the AI Platform ([[phase3-m1-ai-platform]]).
Goal: future milestones only *create agents* — no orchestration code changes.
Non-obvious facts:

- **14 independent subpackages**: `orchestrator/` (AgentOrchestrator, entry
  point `run(Goal)->OrchestrationResult`), `planner/` (CapabilityTaskPlanner,
  template+keyword driven, offline), `workflow/` (WorkflowDefinition = config,
  WorkflowEngine executes), `delegation/`, `communication/` (MessageBus +
  SharedMessage), `context/` (SharedContext), `registry/` (OrchestrationRegistry
  v2, capability+health discovery, `orchestration_registry` global), `scheduler/`
  (parallel groups), `memory/` (4 scopes + LongTerm interface only — NO vector
  yet), `events/` (feeds telemetry via TelemetryEventBridge → existing
  TelemetryLogger), `state/`, `safety/`, `monitoring/`, `simulation/`.
- **Zero hiring logic in the package.** A `Task` names an opaque `capability`
  string; agents hold all domain knowledge. Shared vocabulary lives in
  `models.py` (Goal, Task, TaskGraph, AgentOutput, Priority, TaskStatus).
- **Future agents plug in via `adapters.py`**: `RunnerAgent` (wraps a BaseAgent
  through AgentRunner — reuses caches/telemetry), `ToolAgent` (wraps a BaseTool),
  `FunctionAgent` (plain callable). Then `orchestration_registry.register(...)`.
  Verified by `test_future_agent_plugs_in_without_orchestration_change`.
- **`builtin.py`** has generic demo agents (collection/analysis/synthesis, NOT
  business) + `build_demo_orchestrator()`; used by the UI and AppTest offline.
- **UI:** `src/ui/orchestration_page.render_orchestration()`, wired as 3rd
  workspace radio in `app.py` ("Multi-Agent Orchestration"), fully offline/lazy.
- **Tests:** `pytest tests/ -p no:faulthandler` → 126 passing (adds
  test_orchestration.py = 41 offline unit tests in ~0.4s, test_orchestration_ui.py
  = 3 AppTests using `AppTest.from_string` to avoid app.py's slow model load).
  See PHASE3_MILESTONE3_REPORT.md.
