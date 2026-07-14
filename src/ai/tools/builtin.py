"""Registration of the built-in tools.

Importing this module registers every deterministic-engine tool into the default
:data:`registry`. Future tools are added simply by registering them here (or from
their own module), and the copilot discovers them automatically.
"""

from __future__ import annotations

from src.ai.tools.registry import ToolRegistry, registry
from src.ai.tools.search_tools import (
    CandidateSearchTool,
    FAISSSearchTool,
    SkillGapTool,
)
from src.ai.tools.intelligence_tools import (
    CandidateIntelligenceTool,
    ExplainabilityTool,
    InterviewTool,
    RecommendationTool,
    RiskTool,
    TimelineTool,
)
from src.ai.tools.workspace_tools import (
    ComparisonTool,
    DashboardTool,
    PipelineTool,
)

_BUILTIN_TOOLS = [
    FAISSSearchTool,
    CandidateSearchTool,
    SkillGapTool,
    CandidateIntelligenceTool,
    TimelineTool,
    RiskTool,
    RecommendationTool,
    InterviewTool,
    ExplainabilityTool,
    ComparisonTool,
    PipelineTool,
    DashboardTool,
]


def register_builtin_tools(target: ToolRegistry = registry) -> ToolRegistry:
    """Register all built-in tools into ``target`` (idempotent) and return it."""
    for tool_cls in _BUILTIN_TOOLS:
        target.register(tool_cls())
    return target


# Populate the default registry on import.
register_builtin_tools(registry)
