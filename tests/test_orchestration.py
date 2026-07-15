"""Tests for the Multi-Agent Orchestration Framework (Phase 3 / Milestone 3).

Exercises every orchestration module — models/graph, planner, scheduler,
registry, delegation, communication, events, state, memory, context, safety,
workflow engine, orchestrator, monitoring and simulation — entirely offline with
simulated / function agents (no dataset, no FAISS, no provider, no LLM).
"""

from __future__ import annotations

import pytest

from src.ai.orchestration.adapters import FunctionAgent
from src.ai.orchestration.communication.bus import MessageBus
from src.ai.orchestration.communication.messages import MessageType, SharedMessage
from src.ai.orchestration.context.context import SharedContext
from src.ai.orchestration.delegation.delegation import DelegationManager
from src.ai.orchestration.events.emitter import EventEmitter, TelemetryEventBridge
from src.ai.orchestration.events.events import EventType, OrchestrationEvent
from src.ai.orchestration.memory.memory import InMemoryOrchestrationMemory
from src.ai.orchestration.models import (
    AgentOutput,
    Goal,
    GraphError,
    Priority,
    Task,
    TaskGraph,
    TaskStatus,
)
from src.ai.orchestration.monitoring.monitor import WorkflowMonitor
from src.ai.orchestration.orchestrator import AgentOrchestrator
from src.ai.orchestration.planner.planner import (
    CapabilityTaskPlanner,
    PlanTemplate,
    default_plan_templates,
)
from src.ai.orchestration.registry.agent_registry import (
    AgentDescriptor,
    HealthStatus,
    OrchestrationRegistry,
)
from src.ai.orchestration.safety.guards import (
    OrchestrationSafetyError,
    OrchestrationSafetyGuard,
    SafetyLimits,
)
from src.ai.orchestration.scheduler.scheduler import SchedulePolicy, TaskScheduler
from src.ai.orchestration.simulation import SimulatedAgent, SimulationRunner
from src.ai.orchestration.state.state import WorkflowState, WorkflowStatus
from src.ai.orchestration.workflow.definition import (
    ExecutionMode,
    RetryPolicy,
    WorkflowDefinition,
    WorkflowStep,
)
from src.ai.orchestration.workflow.engine import CancellationToken, WorkflowEngine


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _agent(name, capability, *, fn=None, fail=False, health=HealthStatus.HEALTHY):
    """Build a controllable FunctionAgent for a capability."""

    def default_fn(task, context):
        if fail:
            return AgentOutput(task_id=task.id, agent=name, ok=False, error="boom")
        return AgentOutput(
            task_id=task.id, agent=name, ok=True, data={"ran": name}, summary=f"{name} ok"
        )

    descriptor = AgentDescriptor(name=name, capabilities=[capability], health=health)
    return FunctionAgent(descriptor, fn or default_fn)


def _registry(*agents):
    reg = OrchestrationRegistry()
    for a in agents:
        reg.register(a)
    return reg


# ---------------------------------------------------------------------------
# Models + TaskGraph
# ---------------------------------------------------------------------------


def test_taskgraph_topological_order_respects_dependencies():
    g = TaskGraph()
    g.add(Task(id="a", goal="", capability="c"))
    g.add(Task(id="b", goal="", capability="c", dependencies=["a"]))
    g.add(Task(id="c", goal="", capability="c", dependencies=["b"]))
    order = [t.id for t in g.topological_order()]
    assert order == ["a", "b", "c"]


def test_taskgraph_layers_group_parallel_tasks():
    g = TaskGraph()
    g.add(Task(id="root", goal="", capability="c"))
    g.add(Task(id="x", goal="", capability="c", dependencies=["root"]))
    g.add(Task(id="y", goal="", capability="c", dependencies=["root"]))
    g.add(Task(id="end", goal="", capability="c", dependencies=["x", "y"]))
    layers = [[t.id for t in layer] for layer in g.execution_layers()]
    assert layers[0] == ["root"]
    assert set(layers[1]) == {"x", "y"}
    assert layers[2] == ["end"]


def test_taskgraph_detects_cycle():
    g = TaskGraph()
    g.add(Task(id="a", goal="", capability="c", dependencies=["b"]))
    g.add(Task(id="b", goal="", capability="c", dependencies=["a"]))
    with pytest.raises(GraphError):
        g.validate()


def test_taskgraph_detects_unknown_dependency():
    g = TaskGraph()
    g.add(Task(id="a", goal="", capability="c", dependencies=["ghost"]))
    with pytest.raises(GraphError):
        g.validate()


def test_task_signature_is_stable_and_distinguishing():
    t1 = Task(id="1", goal="g", capability="c", payload={"x": 1})
    t2 = Task(id="2", goal="g", capability="c", payload={"x": 1})
    t3 = Task(id="3", goal="g", capability="c", payload={"x": 2})
    assert t1.signature() == t2.signature()
    assert t1.signature() != t3.signature()


# ---------------------------------------------------------------------------
# Planner
# ---------------------------------------------------------------------------


def test_planner_selects_template_by_keywords():
    planner = CapabilityTaskPlanner(default_plan_templates())
    graph = planner.plan(Goal(description="Please analyze the subject in full"))
    caps = sorted({t.capability for t in graph})
    assert "collection" in caps and "synthesis" in caps
    assert len(graph) == 4


def test_planner_falls_back_to_single_task():
    planner = CapabilityTaskPlanner([], default_capability="general")
    graph = planner.plan(Goal(description="something unmatched entirely"))
    assert len(graph) == 1
    assert next(iter(graph)).capability == "general"


def test_planner_sets_confidence_and_template_metadata():
    planner = CapabilityTaskPlanner(default_plan_templates())
    graph = planner.plan(Goal(description="analyze evaluate assess deep dive"))
    for task in graph:
        assert task.confidence > 50
        assert task.metadata.get("plan_template") == "entity_analysis"


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------


def test_scheduler_produces_priority_ordered_layers():
    g = TaskGraph()
    g.add(Task(id="lo", goal="", capability="c", priority=Priority.LOW))
    g.add(Task(id="hi", goal="", capability="c", priority=Priority.CRITICAL))
    plan = TaskScheduler().schedule(g)
    assert plan.groups[0][0].id == "hi"  # highest priority first in the group


def test_scheduler_respects_max_parallel_cap():
    g = TaskGraph()
    for i in range(5):
        g.add(Task(id=f"t{i}", goal="", capability="c"))
    plan = TaskScheduler(SchedulePolicy(max_parallel=2)).schedule(g)
    assert plan.max_width <= 2
    assert plan.total_tasks == 5


def test_scheduler_timeout_and_retry_overrides():
    sched = TaskScheduler(SchedulePolicy(default_timeout_s=9, max_retries=1))
    task = Task(id="t", goal="", capability="c", metadata={"timeout_s": 3, "max_retries": 4})
    assert sched.timeout_for(task) == 3.0
    assert sched.retries_for(task) == 4


# ---------------------------------------------------------------------------
# Registry v2
# ---------------------------------------------------------------------------


def test_registry_discovers_by_capability():
    reg = _registry(_agent("a1", "analysis"), _agent("c1", "collection"))
    found = [a.descriptor.name for a in reg.discover("analysis")]
    assert found == ["a1"]


def test_registry_excludes_unhealthy_agents():
    reg = _registry(_agent("bad", "analysis", health=HealthStatus.UNHEALTHY))
    assert reg.discover("analysis", healthy_only=True) == []
    assert len(reg.discover("analysis", healthy_only=False)) == 1


def test_registry_capability_index_and_health_update():
    reg = _registry(_agent("a1", "analysis"))
    assert reg.capabilities() == {"analysis": ["a1"]}
    reg.set_health("a1", HealthStatus.DEGRADED)
    assert reg.get("a1").descriptor.health == HealthStatus.DEGRADED


# ---------------------------------------------------------------------------
# Delegation
# ---------------------------------------------------------------------------


def test_delegation_chooses_and_runs_agent():
    reg = _registry(_agent("a1", "analysis"))
    mgr = DelegationManager(reg)
    out = mgr.delegate(Task(id="t", goal="g", capability="analysis"), SharedContext())
    assert out.ok and out.agent == "a1"


def test_delegation_no_candidate_returns_failed_output():
    mgr = DelegationManager(OrchestrationRegistry())
    out = mgr.delegate(Task(id="t", goal="g", capability="missing"), SharedContext())
    assert not out.ok and "No healthy agent" in out.error


def test_delegation_falls_back_to_next_candidate():
    reg = _registry(
        _agent("bad", "analysis", fail=True),
        _agent("good", "analysis"),
    )
    mgr = DelegationManager(reg)
    # 'bad' advertises 1 capability like 'good'; force order by health/name — both
    # healthy, tie broken by name → 'bad' first, then falls back to 'good'.
    out = mgr.delegate(
        Task(id="t", goal="g", capability="analysis"), SharedContext(), max_retries=0
    )
    assert out.ok and out.agent == "good"


def test_delegation_dedupes_identical_work():
    reg = _registry(_agent("a1", "analysis"))
    safety = OrchestrationSafetyGuard()
    mgr = DelegationManager(reg, safety=safety)
    ctx = SharedContext()
    task = Task(id="t", goal="g", capability="analysis")
    first = mgr.delegate(task, ctx)
    ctx.record_output(task.id, first.data)
    second = mgr.delegate(
        Task(id="t2", goal="g", capability="analysis"), ctx
    )
    assert second.agent == "(deduplicated)"


# ---------------------------------------------------------------------------
# Communication
# ---------------------------------------------------------------------------


def test_message_bus_delivers_to_type_and_wildcard():
    bus = MessageBus()
    seen = []
    bus.subscribe(MessageType.TASK_REQUEST, lambda m: seen.append(("typed", m.id)))
    bus.subscribe("*", lambda m: seen.append(("wild", m.id)))
    bus.emit(MessageType.TASK_REQUEST, sender="x", payload={})
    kinds = {k for k, _ in seen}
    assert kinds == {"typed", "wild"}


def test_message_bus_swallows_handler_errors():
    bus = MessageBus()

    def boom(_m):
        raise ValueError("nope")

    bus.subscribe("*", boom)
    bus.emit(MessageType.STATUS_UPDATE, sender="x", payload={})
    assert bus.delivery_errors == 1
    assert len(bus.history()) == 1


# ---------------------------------------------------------------------------
# Events + telemetry bridge
# ---------------------------------------------------------------------------


def test_event_emitter_dispatches_and_records_history():
    emitter = EventEmitter()
    got = []
    emitter.on(EventType.TASK_COMPLETED, lambda e: got.append(e))
    emitter.emit(OrchestrationEvent(type=EventType.TASK_COMPLETED, workflow_id="w"))
    assert len(got) == 1
    assert len(emitter.history()) == 1


def test_telemetry_bridge_forwards_events(tmp_path):
    from src.ai.telemetry.logger import TelemetryLogger

    logger = TelemetryLogger(directory=str(tmp_path))
    emitter = EventEmitter()
    TelemetryEventBridge(logger).attach(emitter)
    emitter.emit(OrchestrationEvent(type=EventType.WORKFLOW_STARTED, workflow_id="w"))
    assert len(logger.recent()) == 1


# ---------------------------------------------------------------------------
# State + memory + context
# ---------------------------------------------------------------------------


def test_workflow_state_snapshot_tracks_completion():
    state = WorkflowState(workflow_id="w")
    ts = state.task("t1", "analysis")
    ts.mark_running("a1")
    ts.mark_finished(AgentOutput(task_id="t1", agent="a1", ok=True))
    snap = state.snapshot()
    assert snap.completed_task_ids == ["t1"]
    assert snap.status == WorkflowStatus.PENDING


def test_memory_scopes_roundtrip():
    mem = InMemoryOrchestrationMemory()
    mem.remember("w", "k", 1)
    mem.share("s", "k", 2)
    mem.note("t", "hello")
    mem.append("w", {"e": 1})
    assert mem.recall("w", "k") == 1
    assert mem.read("s", "k") == 2
    assert mem.notes("t") == ["hello"]
    assert mem.trace("w") == [{"e": 1}]


def test_shared_context_condition_and_dependency_outputs():
    ctx = SharedContext()
    ctx.set("go", True)
    assert ctx.truthy("go")
    ctx.jd = "python"
    assert ctx.truthy("jd")
    ctx.record_output("dep", {"value": 42})
    task = Task(id="t", goal="", capability="c", dependencies=["dep"])
    assert ctx.dependency_outputs(task) == {"dep": {"value": 42}}


# ---------------------------------------------------------------------------
# Safety
# ---------------------------------------------------------------------------


def test_safety_rejects_cycles_and_oversized_graphs():
    guard = OrchestrationSafetyGuard(SafetyLimits(max_graph_size=1))
    g = TaskGraph()
    g.add(Task(id="a", goal="", capability="c"))
    g.add(Task(id="b", goal="", capability="c"))
    with pytest.raises(OrchestrationSafetyError):
        guard.validate_graph(g)


def test_safety_execution_ceiling_prevents_infinite_loops():
    guard = OrchestrationSafetyGuard(SafetyLimits(max_total_executions=2))
    task = Task(id="t", goal="", capability="c")
    guard.before_execution(task)
    guard.before_execution(task)
    with pytest.raises(OrchestrationSafetyError):
        guard.before_execution(task)


def test_safety_dedup_signature_ledger():
    guard = OrchestrationSafetyGuard()
    task = Task(id="t", goal="g", capability="c")
    assert guard.register_execution(task) is True
    assert guard.register_execution(task) is False


# ---------------------------------------------------------------------------
# Workflow engine
# ---------------------------------------------------------------------------


def _linear_def(mode=ExecutionMode.AUTO, **retry):
    return WorkflowDefinition(
        name="t",
        mode=mode,
        retry=RetryPolicy(**retry) if retry else RetryPolicy(),
        steps=[
            WorkflowStep(id="s1", capability="collection", goal="collect"),
            WorkflowStep(id="s2", capability="analysis", goal="analyse", depends_on=["s1"]),
        ],
    )


def test_engine_runs_workflow_to_completion():
    reg = _registry(_agent("c", "collection"), _agent("a", "analysis"))
    engine = WorkflowEngine(registry=reg)
    result = engine.run_definition(_linear_def())
    assert result.status == WorkflowStatus.COMPLETED
    assert set(result.outputs) == {"s1", "s2"}


def test_engine_degrades_to_partial_on_required_failure():
    reg = _registry(_agent("c", "collection"), _agent("a", "analysis", fail=True))
    engine = WorkflowEngine(registry=reg)
    result = engine.run_definition(_linear_def(continue_on_failure=True))
    assert result.status == WorkflowStatus.PARTIAL
    assert not result.outputs["s2"].ok


def test_engine_aborts_when_continue_on_failure_false():
    reg = _registry(_agent("c", "collection"), _agent("a", "analysis", fail=True))
    engine = WorkflowEngine(registry=reg)
    result = engine.run_definition(_linear_def(continue_on_failure=False))
    assert result.status == WorkflowStatus.FAILED


def test_engine_fallback_capability_recovers_failure():
    reg = _registry(
        _agent("primary", "analysis", fail=True),
        _agent("backup", "backup_analysis"),
    )
    engine = WorkflowEngine(registry=reg)
    definition = WorkflowDefinition(
        name="fb",
        retry=RetryPolicy(fallback_capability="backup_analysis", continue_on_failure=True),
        steps=[WorkflowStep(id="s1", capability="analysis", goal="analyse")],
    )
    result = engine.run_definition(definition)
    assert result.outputs["s1"].ok
    assert "fallback" in result.outputs["s1"].summary


def test_engine_conditional_step_is_skipped():
    reg = _registry(_agent("c", "collection"), _agent("a", "analysis"))
    engine = WorkflowEngine(registry=reg)
    definition = WorkflowDefinition(
        name="cond",
        steps=[
            WorkflowStep(id="s1", capability="collection", goal="c"),
            WorkflowStep(id="s2", capability="analysis", goal="a", condition="do_extra"),
        ],
    )
    result = engine.run_definition(definition)  # 'do_extra' not set → skipped
    assert result.state.tasks["s2"].status == TaskStatus.SKIPPED
    assert "s2" not in result.outputs


def test_engine_cancellation_before_run():
    reg = _registry(_agent("c", "collection"))
    engine = WorkflowEngine(registry=reg)
    token = CancellationToken()
    token.cancel()
    result = engine.run_definition(_linear_def(), cancellation=token)
    assert result.status == WorkflowStatus.CANCELLED


def test_engine_sequential_mode_chains_tasks():
    definition = _linear_def(mode=ExecutionMode.SEQUENTIAL)
    graph = definition.build_graph()
    layers = graph.execution_layers()
    assert all(len(layer) == 1 for layer in layers)  # strictly one-at-a-time


# ---------------------------------------------------------------------------
# Orchestrator (end-to-end)
# ---------------------------------------------------------------------------


def test_orchestrator_runs_goal_end_to_end():
    reg = _registry(
        _agent("c", "collection"),
        _agent("a", "analysis"),
        _agent("s", "synthesis"),
    )
    orch = AgentOrchestrator(
        registry=reg,
        planner=CapabilityTaskPlanner(default_plan_templates()),
        engine=WorkflowEngine(registry=reg),
        telemetry_bridge=False,
    )
    result = orch.run(Goal(description="analyze the subject in full"))
    assert result.ok
    assert result.task_count == 4
    assert result.graph is not None
    assert result.answer


def test_orchestrator_plan_only_does_not_execute():
    orch = AgentOrchestrator(telemetry_bridge=False)
    graph = orch.plan_only(Goal(description="quick summary"))
    assert len(graph) >= 1


# ---------------------------------------------------------------------------
# Monitoring
# ---------------------------------------------------------------------------


def test_monitor_tracks_success_rate_and_log():
    reg = _registry(_agent("c", "collection"), _agent("a", "analysis"))
    engine = WorkflowEngine(registry=reg)
    monitor = WorkflowMonitor()
    monitor.attach(engine.events)
    result = engine.run_definition(_linear_def())
    summary = monitor.summary()
    assert summary["tasks_completed"] == 2
    assert summary["success_rate"] == 100.0
    assert monitor.visual_log(result.workflow_id)


# ---------------------------------------------------------------------------
# Simulation (Module 14)
# ---------------------------------------------------------------------------


def test_simulation_dry_run_autoprovisions_and_executes():
    sim = SimulationRunner()
    report = sim.dry_run(Goal(description="analyze the subject in full"))
    assert report.result.status == WorkflowStatus.COMPLETED
    assert report.layers[0] == ["collect"]
    assert set(report.missing_capabilities) >= {"collection", "analysis", "synthesis"}


def test_simulation_failed_agent_degrades_run():
    sim = SimulationRunner()
    sim.register(SimulatedAgent("collection"))
    sim.register(SimulatedAgent("analysis", fail=True))
    sim.register(SimulatedAgent("synthesis"))
    report = sim.dry_run(
        Goal(description="analyze the subject in full"), autoprovision=False
    )
    assert report.result.status == WorkflowStatus.PARTIAL


def test_future_agent_plugs_in_without_orchestration_change():
    """A brand-new capability + agent is discovered and run with zero framework edits."""
    reg = _registry(_agent("novel", "brand_new_capability"))
    planner = CapabilityTaskPlanner(
        [
            PlanTemplate(
                name="novel_flow",
                keywords=[("novel", 5)],
                definition=WorkflowDefinition(
                    name="novel_flow",
                    steps=[WorkflowStep(id="only", capability="brand_new_capability", goal="do it")],
                ),
            )
        ]
    )
    orch = AgentOrchestrator(
        registry=reg, planner=planner, engine=WorkflowEngine(registry=reg), telemetry_bridge=False
    )
    result = orch.run(Goal(description="run the novel flow"))
    assert result.ok
    assert result.outputs["only"].agent == "novel"
