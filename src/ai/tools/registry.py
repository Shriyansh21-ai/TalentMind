"""Tool registry + runner.

The registry is a service locator so agents/planners discover tools by name
without importing concrete tool classes — the seam that lets future tools "plug
in easily". The runner executes a set of tools against a shared context.
"""

from __future__ import annotations

from typing import Dict, List

from src.ai.tools.base import BaseTool, ToolContext, ToolResult


class ToolRegistry:
    """In-process registry mapping tool name -> tool instance."""

    def __init__(self) -> None:
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> BaseTool:
        """Register ``tool`` under its metadata name (last registration wins)."""
        self._tools[tool.metadata.name] = tool
        return tool

    def get(self, name: str) -> BaseTool:
        """Return the tool registered under ``name``.

        Raises:
            KeyError: If no such tool is registered.
        """
        if name not in self._tools:
            raise KeyError(f"No tool registered under {name!r}.")
        return self._tools[name]

    def has(self, name: str) -> bool:
        """Return ``True`` iff ``name`` is registered."""
        return name in self._tools

    def names(self) -> List[str]:
        """Return all registered tool names (sorted)."""
        return sorted(self._tools.keys())

    def describe(self) -> Dict[str, str]:
        """Return ``{name: description}`` for every registered tool."""
        return {name: tool.metadata.description for name, tool in self._tools.items()}


class ToolRunner:
    """Executes tools from a registry against a :class:`ToolContext`."""

    def __init__(self, registry: "ToolRegistry") -> None:
        self.registry = registry

    def run(self, name: str, tool_input: dict, context: ToolContext) -> ToolResult:
        """Run a single tool by name (unknown tool -> failed :class:`ToolResult`)."""
        if not self.registry.has(name):
            return ToolResult(name=name, ok=False, error=f"Unknown tool {name!r}")
        return self.registry.get(name).run(tool_input, context)

    def run_many(
        self,
        plan: List[tuple],
        context: ToolContext,
    ) -> List[ToolResult]:
        """Run an ordered ``[(name, input), ...]`` plan and collect results.

        Execution never raises: a failing tool yields a failed :class:`ToolResult`
        so the copilot can still reason over whatever succeeded.
        """
        results: List[ToolResult] = []
        for name, tool_input in plan:
            results.append(self.run(name, tool_input or {}, context))
        return results


# Process-wide default registry. Tool modules register into it at import time.
registry = ToolRegistry()
