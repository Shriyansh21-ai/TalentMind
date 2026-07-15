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
from src.ai.tools.resume_tools import ResumeAnalysisTool
from src.ai.tools.jd_tools import JDAnalysisTool
from src.ai.tools.committee_tools import HiringCommitteeTool
from src.ai.tools.executive_report_tools import ExecutiveReportTool
from src.ai.tools.interview_studio_tools import InterviewStudioTool
from src.ai.tools.compensation_tools import CompensationGovernanceTool
from src.ai.tools.pay_equity_tools import PayEquityTool
from src.ai.tools.compliance_tools import HiringComplianceTool
from src.ai.tools.audit_tools import HiringAuditTool
from src.ai.tools.hiring_intelligence_tools import HiringIntelligenceTool

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
    ResumeAnalysisTool,
    JDAnalysisTool,
    HiringCommitteeTool,
    ExecutiveReportTool,
    InterviewStudioTool,
    CompensationGovernanceTool,
    PayEquityTool,
    HiringComplianceTool,
    HiringAuditTool,
    HiringIntelligenceTool,
]


def register_builtin_tools(target: ToolRegistry = registry) -> ToolRegistry:
    """Register all built-in tools into ``target`` (idempotent) and return it."""
    for tool_cls in _BUILTIN_TOOLS:
        target.register(tool_cls())
    return target


# Populate the default registry on import.
register_builtin_tools(registry)
