"""Adapters — the plug-in bridges for future agents.

This is the concrete answer to *"future agents should require almost no
orchestration changes."* A future milestone builds a domain agent however it
likes — a plain function, an existing :class:`~src.ai.tools.base.BaseTool`, or a
full :class:`~src.ai.core.base_agent.BaseAgent` run through the
:class:`~src.ai.core.runner.AgentRunner` — and wraps it in one of these adapters
to expose it as an :class:`OrchestrationAgent`. The orchestrator, planner,
scheduler, delegation and engine never change.

Adapters are the *only* place the framework touches the rest of the platform, and
they do so through the existing public seams (tool registry, agent runner).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from src.ai.orchestration.context.context import SharedContext
from src.ai.orchestration.models import AgentOutput, Task
from src.ai.orchestration.registry.agent_registry import (
    AgentDescriptor,
    OrchestrationAgent,
)

ExecuteFn = Callable[[Task, SharedContext], AgentOutput]


class FunctionAgent(OrchestrationAgent):
    """Wraps a plain ``(task, context) -> AgentOutput`` callable as an agent.

    The lightest possible way to contribute an agent — ideal for glue steps,
    tests and the simulation harness.
    """

    def __init__(self, descriptor: AgentDescriptor, fn: ExecuteFn) -> None:
        """Bind a descriptor + the execution callable."""
        self.descriptor = descriptor
        self._fn = fn

    def execute(self, task: Task, context: SharedContext) -> AgentOutput:
        """Delegate to the wrapped callable, normalising the task id."""
        output = self._fn(task, context)
        output.task_id = task.id
        output.agent = self.descriptor.name
        return output


class ToolAgent(OrchestrationAgent):
    """Adapts an existing :class:`~src.ai.tools.base.BaseTool` as an agent.

    The task payload becomes the tool input; the tool runs against a
    :class:`~src.ai.tools.base.ToolContext` produced by an injected factory (so
    the framework never imports the dataset/FAISS). Purely generic — it works for
    *any* current or future tool.
    """

    def __init__(
        self,
        tool: Any,
        *,
        capabilities: list[str],
        context_factory: Callable[[SharedContext], Any],
        name: str | None = None,
    ) -> None:
        """Wrap ``tool`` (a ``BaseTool``); ``context_factory`` builds its ToolContext."""
        self.tool = tool
        self._context_factory = context_factory
        self.descriptor = AgentDescriptor(
            name=name or f"tool:{tool.metadata.name}",
            capabilities=list(capabilities),
            description=tool.metadata.description,
            tool_requirements=[tool.metadata.name],
            tags=["tool-adapter"],
        )

    def execute(self, task: Task, context: SharedContext) -> AgentOutput:
        """Run the wrapped tool and map its :class:`ToolResult` to an output."""
        tool_context = self._context_factory(context)
        result = self.tool.run(task.payload, tool_context)
        return AgentOutput(
            task_id=task.id,
            agent=self.descriptor.name,
            ok=result.ok,
            data=result.output,
            summary=result.summary,
            confidence=result.confidence,
            evidence_sources=list(result.evidence_sources),
            latency_ms=result.latency_ms,
            error=result.error,
        )


class RunnerAgent(OrchestrationAgent):
    """Adapts a :class:`~src.ai.core.base_agent.BaseAgent` (via the AgentRunner).

    A ``payload_builder`` turns the task + shared context into the typed payload
    the underlying agent expects, keeping all hiring specifics inside the agent.
    The runner handles providers, caching, retries, safety and telemetry — this
    adapter just maps the :class:`~src.ai.core.response.AgentResult` to an
    :class:`AgentOutput`.
    """

    def __init__(
        self,
        base_agent: Any,
        *,
        capabilities: list[str],
        payload_builder: Callable[[Task, SharedContext], Any],
        runner: Any = None,
        name: str | None = None,
    ) -> None:
        """Wrap ``base_agent``; ``payload_builder`` produces its typed payload."""
        self.base_agent = base_agent
        self._payload_builder = payload_builder
        self._runner = runner
        meta = base_agent.metadata
        self.descriptor = AgentDescriptor(
            name=name or meta.name,
            version=meta.version,
            capabilities=list(capabilities),
            description=meta.description,
            tags=list(meta.tags),
        )

    def _get_runner(self):
        """Lazily construct the shared :class:`AgentRunner` (avoids import cost)."""
        if self._runner is None:
            from src.ai.core.runner import AgentRunner

            self._runner = AgentRunner()
        return self._runner

    def execute(self, task: Task, context: SharedContext) -> AgentOutput:
        """Build the payload, run the base agent, and map the result."""
        payload = self._payload_builder(task, context)
        result = self._get_runner().run(self.base_agent, payload)
        data = result.data.to_dict() if getattr(result, "data", None) else {}
        return AgentOutput(
            task_id=task.id,
            agent=self.descriptor.name,
            ok=result.ok,
            data=data,
            summary=f"{self.descriptor.name} → {result.status.value}",
            evidence_sources=[result.provider],
            latency_ms=result.latency_ms,
            error=result.error,
        )
