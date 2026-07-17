# TalentMind — Multi-Agent System

Two cooperating subsystems make TalentMind "multi-agent":

1. **Orchestration** (`src/ai/orchestration/`) — a general, domain-free framework that compiles a
   goal into a task DAG and executes it with capability routing, parallel layers, retries, and
   fallback.
2. **AI Hiring Committee** (`src/ai/committee/`) — the flagship application of that framework: 7
   independent reviewers reaching an evidence-weighted consensus.

Neither subsystem contains hiring business logic — they coordinate agents that wrap the
deterministic engines. See [`AI_PLATFORM.md`](AI_PLATFORM.md) for the single-agent runtime and
[`ENTERPRISE_AGENTS.md`](ENTERPRISE_AGENTS.md) for each agent.

---

## 1. Orchestration framework — `src/ai/orchestration/`

Design contract (from the package docstring): *future milestones should only need to create new
agents; no orchestration code should need modification.*

### Model — `models.py`

- `Goal(description, subject_id, constraints, metadata)`
- `Task(id, goal, capability, priority, dependencies, expected_output, confidence, payload,
  optional, condition, metadata)` — `capability` is an opaque string (e.g. `collection`,
  `analysis`, `synthesis`).
- `AgentOutput(task_id, agent, ok, data, summary, confidence, evidence_sources, latency_ms, error)`
- `TaskGraph` — a DAG with `validate`, `topological_order` (Kahn), and `execution_layers`
  (parallelizable layers). `Priority`, `TaskStatus` enums.

### Planner — `planner/planner.py`

`TaskPlanner(ABC)` is the seam for a future LLM planner. The shipped
`CapabilityTaskPlanner` is **deterministic and template-driven**: `PlanTemplate` keyword-scores
the goal text, and the winning `WorkflowDefinition` compiles to a `TaskGraph` (or a single-task
default). `default_plan_templates()` provides generic `entity_analysis` and `quick_answer`
examples.

### Orchestrator — `orchestrator/orchestrator.py`

`AgentOrchestrator.run(goal)`: **plan → `WorkflowEngine.run` → merge**. `_merge` is pure
aggregation — it prefers a `synthesis` output as headline, otherwise concatenates per-task
summaries; it performs no domain interpretation. Returns `OrchestrationResult` (answer, outputs,
task_count, evidence_sources, warnings, latency, workflow_id, state, graph). `plan_only(goal)`
introspects the plan without executing.

### Workflow engine — `workflow/engine.py`

`WorkflowEngine` executes a `TaskGraph`/`WorkflowDefinition` with injected collaborators (registry,
`DelegationManager`, `TaskScheduler`, `OrchestrationSafetyGuard`, `EventEmitter`, `MessageBus`,
`OrchestrationMemory`). It supports sequential / parallel (per schedule group) / conditional
(`task.condition` resolved against `SharedContext`) execution, dependency gating, config-driven
retry + capability fallback, and cooperative cancellation (`CancellationToken`).

### Delegation & routing — `delegation/delegation.py`

`DelegationManager` selects and runs the agent. The default `CapabilityRoutingStrategy` prefers
**healthy → more specialised (fewer capabilities) → least loaded → name**. Identical work is
de-duplicated via the safety guard's signature ledger; failures fall back to the next candidate;
expected failures never raise (they return `AgentOutput(ok=False)`).

### Registry & adapters

- `registry/agent_registry.py` — `OrchestrationRegistry` (thread-safe, capability-indexed) +
  global `orchestration_registry`. `OrchestrationAgent(ABC)` declares an `AgentDescriptor`
  (name, version, capabilities, dependencies, tool_requirements, tags, health, max_concurrency).
- `adapters.py` — the plug-in bridges: `FunctionAgent` (wrap a callable), `ToolAgent` (wrap a
  `BaseTool`), `RunnerAgent` (wrap a `BaseAgent` and run it through `AgentRunner`). **Every
  concrete business agent joins orchestration via `RunnerAgent`.**

### Supporting subpackages

`communication/` (`MessageBus`), `context/` (`SharedContext`), `events/` (`EventEmitter`,
`TelemetryEventBridge`), `memory/` (`OrchestrationMemory`), `monitoring/` (`WorkflowMonitor`),
`scheduler/` (`TaskScheduler`, `SchedulePolicy`), `safety/` (`OrchestrationSafetyGuard` — cycle /
size / duplicate / health guards), `simulation/` (dry-run, no LLM), `state/` (`WorkflowState`).

### Execution flow

```
Goal ─▶ CapabilityTaskPlanner ─▶ TaskGraph (DAG)
                                    │
                     WorkflowEngine.execution_layers()
                                    │
        layer 0  ── DelegationManager ─▶ route ─▶ RunnerAgent ─▶ AgentRunner
        layer 1  ── (depends on layer 0; parallel within the layer)
                                    │
                          AgentOrchestrator._merge ─▶ OrchestrationResult
```

---

## 2. AI Hiring Committee — `src/ai/committee/`

The committee consumes **only already-computed structured outputs** — it re-runs no engine, and
every underlying analysis is cached. Importing the package auto-registers the chair with the AI
Platform and the committee with the orchestration registry.

### Lifecycle — `committee.py::HiringCommitteeEngine`

1. `gather_evidence(candidate, jd, ...)` → `EvidenceBundle` (candidate overview + resume analysis
   + JD analysis + intelligence / timeline / risk / recommendation / interview plan + skill gap +
   `available_sources`).
2. **Parallel independent reviews** via the moderator / `WorkflowEngine`.
3. Discussion round.
4. **Evidence-weighted consensus.**
5. Conflict resolution.
6. Confidence metrics.
7. Executive **chair decision** (AI Platform, deterministic-composer fallback).
8. Memory write.

It emits warnings when there is no JD or fewer than 5 evidence sources.

### The panel — `members.py::build_panel()`

Seven reviewers, each a **pure function of `(bundle, mode)`** reading one evidence slice:

| Reviewer | Evidence slice |
|---|---|
| Resume Expert | resume analysis |
| JD Expert | JD analysis |
| Technical Hiring Manager | intelligence (technical) |
| Risk Officer | risk report |
| Career Growth Specialist | timeline |
| Interview Lead | interview plan |
| Hiring Analyst | recommendation / overview |

No member re-runs an engine, no member sees another's opinion, and every strength/concern names
its source. Missing evidence → `_abstain()`.

### Voting & consensus

- `voting.py` — stance map `NO_HIRE −2 … STRONG_HIRE +3`; `weight_of = (confidence/100) ×
  evidence_coverage × role/mode multiplier`. **Evidence-weighted, never a majority vote.** Modes
  (`balanced` / `optimistic` / `conservative`) apply a deterministic stance bias (±0.25).
- `consensus.py` — weighted stance + agreement ratio + dispersion → `ConsensusLevel`
  (STRONG / MODERATE / SPLIT / NONE). *"Three thinly-supported agreements do not manufacture a
  strong consensus."*
- `conflict_resolution.py` — material conflicts only when the stance gap ≥ 2.0; explains root
  cause, missing evidence, and resolution strategy. Conflicts are never invented.

### Chair — `chair.py::CommitteeChairAgent`

A concrete `BaseAgent` (name `committee_chair`) whose output schema `CommitteeDecision` is
score-free at the top level (`recommendation` is a label). The composer `compose_committee_decision`
narrates the consensus — *the recommendation comes from the evidence-weighted consensus; the chair
justifies it, it does not re-decide by fiat.*

### Schemas — `schemas.py`

Enums `Recommendation`, `ConsensusLevel`, `CommitteeMode`; dataclasses `MemberOpinion`,
`Consensus`, `Conflict`, `DiscussionRound`, `ConfidenceMetrics`; `CommitteeDecision`
(`BaseAIResponse`) and `CommitteeReport` (the final artefact).

---

## 3. Recruiter Copilot — `src/ai/copilot/` + `src/ai/tools/`

`RecruiterCopilot.ask(session_id, message, jd)` runs: **classify intent → plan → run tools →
narrate → build turn → record**. It never bypasses a deterministic engine — every fact in a reply
originates from a tool that wrapped an existing engine.

- `planner.py::IntentClassifier` — data-driven weighted keyword patterns across ~25 intents
  (including HIRING_COMMITTEE, INTERVIEW_STUDIO, EXECUTIVE_REPORT, COMPENSATION_GOVERNANCE,
  PAY_EQUITY, HIRING_COMPLIANCE, HIRING_AUDIT, HIRING_INTELLIGENCE). `CopilotPlanner` selects a
  minimal tool set with contextual reference resolution.
- `src/ai/tools/` — `BaseTool` wraps an existing engine via a `CandidateRepository` (DI); tools
  never reimplement logic. `ToolRegistry` + `ToolRunner` (never raise). `InMemoryCandidateRepository`
  provides FAISS or keyword-fallback search.

The narration agent is `RecruiterCopilotAgent` (`src/ai/agents/recruiter_copilot.py`), which
receives **only** structured tool outputs (never raw resumes) and produces the score-free
`CopilotResponse`.
