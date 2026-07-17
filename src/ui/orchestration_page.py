"""Multi-Agent Orchestration console (Module 15 — Visualization).

A professional, self-contained Streamlit page that makes the orchestration
backbone visible: the planner's decomposition, the task graph, the agent graph
(who ran what), the execution timeline, and live workflow status.

The page is UI-only. It drives a fully offline demo orchestrator
(:func:`build_demo_orchestrator`) plus the :class:`SimulationRunner`, so it
renders and runs instantly with no dataset, provider or LLM — and AppTest stays
fast.
"""

from __future__ import annotations

import streamlit as st

from src.ai.orchestration import Goal
from src.ai.orchestration.builtin import build_demo_orchestrator
from src.ai.orchestration.simulation import SimulationRunner
from src.ui.theme import strip_emoji

_LAST_KEY = "orch_last_result"
_GOAL_KEY = "orch_goal_input"

_EXAMPLES = [
    "Analyze the subject in full across every facet",
    "Give me a quick summary answer",
    "Assess and evaluate the subject deeply",
]


def render_orchestration(*, jd: str = "") -> None:
    """Render the Multi-Agent Orchestration console."""
    st.title("Multi-Agent Orchestration")
    st.caption(
        "The orchestration backbone: a high-level goal is planned into a task "
        "graph, scheduled into parallel groups, delegated to capability-matched "
        "agents, executed, monitored and merged — no orchestration code per agent."
    )

    orchestrator = _get_orchestrator()
    _render_sidebar(orchestrator)

    goal_text = st.text_input(
        "Recruiter goal",
        key=_GOAL_KEY,
        placeholder="e.g. Analyze the subject in full across every facet",
    )
    cols = st.columns([1, 1, 1, 2])
    run = cols[0].button("Run orchestration", type="primary")
    dry = cols[1].button("Dry-run (simulate)")
    clear = cols[2].button("Clear")

    if clear:
        st.session_state.pop(_LAST_KEY, None)

    st.markdown("**Examples**")
    ex_cols = st.columns(len(_EXAMPLES))
    for i, example in enumerate(_EXAMPLES):
        if ex_cols[i].button(example, key=f"orch_ex_{i}"):
            st.session_state[_GOAL_KEY] = example
            goal_text = example
            run = True

    if (run or dry) and goal_text.strip():
        goal = Goal(description=goal_text.strip(), subject_id="demo_subject")
        if dry:
            _render_dry_run(goal)
        else:
            _run_and_store(orchestrator, goal)

    if st.session_state.get(_LAST_KEY):
        _render_result(orchestrator, st.session_state[_LAST_KEY])


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------


def _get_orchestrator():
    """Return the demo orchestrator, cached for the session."""
    if "orch_instance" not in st.session_state:
        st.session_state["orch_instance"] = build_demo_orchestrator()
    return st.session_state["orch_instance"]


def _run_and_store(orchestrator, goal: Goal) -> None:
    """Run a goal through the orchestrator and stash the result."""
    with st.spinner("Orchestrating…"):
        result = orchestrator.run(goal)
    st.session_state[_LAST_KEY] = result.workflow_id
    st.session_state["orch_result_obj"] = result


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def _render_sidebar(orchestrator) -> None:
    """Render the agent registry + capability index in the sidebar."""
    with st.sidebar:
        st.markdown("### Orchestration Registry")
        rows = orchestrator.registry.describe()
        st.caption(f"{len(rows)} agent(s) registered")
        for row in rows:
            st.markdown(f"**{row['name']}**  ·  `{row['health']}`")
            st.caption("capabilities: " + ", ".join(row["capabilities"]))

        st.markdown("**Capability index**")
        for cap, names in sorted(orchestrator.registry.capabilities().items()):
            st.caption(f"`{cap}` → {', '.join(names)}")


def _render_result(orchestrator, workflow_id: str) -> None:
    """Render the full result of the most recent run."""
    result = st.session_state.get("orch_result_obj")
    if result is None:
        return

    st.divider()
    status = result.status.value
    st.subheader(f"Workflow `{result.workflow_id}` — {status}")

    m = orchestrator.monitor.summary()
    cols = st.columns(4)
    cols[0].metric("Tasks", result.task_count)
    cols[1].metric("Succeeded", m.get("tasks_completed", 0))
    cols[2].metric("Failed", m.get("tasks_failed", 0))
    cols[3].metric("Latency", f"{result.latency_ms:.0f} ms")

    # Unified merged answer.
    st.markdown("#### Unified response")
    st.markdown(result.answer)
    if result.evidence_sources:
        st.caption("Evidence: " + ", ".join(result.evidence_sources))
    if result.warnings:
        for warning in result.warnings:
            st.warning(warning)

    tab_plan, tab_graph, tab_agents, tab_timeline = st.tabs(
        ["Plan", "Task graph", "Agent graph", "Timeline"]
    )

    with tab_plan:
        _render_plan(result)
    with tab_graph:
        _render_task_graph(result)
    with tab_agents:
        _render_agent_graph(orchestrator, result)
    with tab_timeline:
        _render_timeline(orchestrator, result.workflow_id)


def _render_plan(result) -> None:
    """Render the planned tasks as a table."""
    st.markdown("**Planner output** — each row is one composable task.")
    rows = []
    for tid, output in result.outputs.items():
        ts = result.state.tasks.get(tid) if result.state else None
        rows.append(
            {
                "task": tid,
                "agent": output.agent,
                "status": ts.status.value if ts else ("ok" if output.ok else "failed"),
                "latency_ms": round(output.latency_ms, 2),
                "summary": output.summary or output.error or "",
            }
        )
    if rows:
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.info("No tasks executed.")


def _render_task_graph(result) -> None:
    """Render the task dependency graph (Graphviz, with a text fallback)."""
    if result.graph is None:
        st.info("No graph available.")
        return
    status_of = (
        {tid: ts.status.value for tid, ts in result.state.tasks.items()} if result.state else {}
    )
    dot = ["digraph G {", " rankdir=LR; node [shape=box style=rounded];"]
    for task in result.graph:
        color = {
            "completed": "#1a7f37",
            "failed": "#cf222e",
            "skipped": "#9a6700",
        }.get(status_of.get(task.id, ""), "#57606a")
        label = f"{task.id}\\n({task.capability})"
        dot.append(f' "{task.id}" [label="{label}" color="{color}"];')
    for task in result.graph:
        for dep in task.dependencies:
            dot.append(f' "{dep}" -> "{task.id}";')
    dot.append("}")
    try:
        st.graphviz_chart("\n".join(dot))
    except Exception:
        st.code("\n".join(dot), language="dot")


def _render_agent_graph(orchestrator, result) -> None:
    """Render which agent handled each task + per-agent metrics."""
    st.markdown("**Task → agent delegation**")
    rows = [{"task": tid, "agent": out.agent, "ok": out.ok} for tid, out in result.outputs.items()]
    st.dataframe(rows, use_container_width=True, hide_index=True)

    st.markdown("**Per-agent metrics**")
    agents = orchestrator.monitor.summary().get("agents", {})
    if agents:
        st.dataframe(
            [{"agent": name, **stats} for name, stats in agents.items()],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No agent metrics yet.")


def _render_timeline(orchestrator, workflow_id: str) -> None:
    """Render the visual workflow log (event stream)."""
    log = orchestrator.monitor.visual_log(workflow_id)
    if not log:
        st.info("No events recorded.")
        return
    st.code("\n".join(strip_emoji(line) for line in log), language="text")


def _render_dry_run(goal: Goal) -> None:
    """Render a simulation dry-run (planner validation, no execution side effects)."""
    sim = SimulationRunner()
    report = sim.dry_run(goal)
    st.divider()
    st.subheader("Dry-run (simulated agents)")
    st.caption(
        "Plan validated + executed against deterministic stand-ins — no LLM, no "
        "providers. This is exactly what the unit tests exercise."
    )
    st.markdown("**Execution layers (parallel groups)**")
    for i, layer in enumerate(report.layers):
        st.markdown(f"- Group {i}: " + ", ".join(f"`{t}`" for t in layer))
    if report.missing_capabilities:
        st.caption("Auto-provisioned capabilities: " + ", ".join(report.missing_capabilities))
    if report.result:
        st.markdown("**Simulated unified response**")
        st.markdown(report.result.answer)
