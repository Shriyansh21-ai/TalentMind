"""Hiring Intelligence tool for the Recruiter Copilot (Module 12).

Exposes the :class:`HiringIntelligenceEngine` to the copilot as a standard
:class:`BaseTool`. Unlike the per-candidate tools, this is **organization-level**:
it needs no candidate id — it analyzes a bounded cohort from the repository.
Selected by intent, so the copilot *automatically* answers "how healthy is our
hiring process?", "show hiring analytics", "what are our bottlenecks?", "generate
executive workforce report", "show hiring trends" and "which departments need
improvement?". It reuses existing intelligence (Module 14) and fabricates no
enterprise statistics (Module 15).
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from src.ai.core.runner import AgentRunner
from src.ai.tools.base import (
    BaseTool,
    ToolContext,
    ToolMetadata,
    ToolResult,
    ToolValidationError,
)

# Importing the engine auto-registers the agent (AI platform + orchestration).
from src.ai.agents.hiring_intelligence.analytics_engine import HiringIntelligenceEngine

_runner: Optional[AgentRunner] = None

# Bounded cohort for a copilot request (keeps the org-level analytics responsive).
_COPILOT_COHORT = 15


def _get_runner() -> AgentRunner:
    """Return a shared, lazily-created :class:`AgentRunner`."""
    global _runner
    if _runner is None:
        _runner = AgentRunner()
    return _runner


class HiringIntelligenceTool(BaseTool):
    """Generate organization-level workforce hiring intelligence (no candidate id)."""

    metadata = ToolMetadata(
        name="hiring_intelligence",
        description=(
            "Generate enterprise workforce hiring intelligence over a bounded "
            "cohort: hiring health, executive KPIs, pipeline bottlenecks, team "
            "analytics, trends, capacity, forecasts, benchmarks and optimization "
            "opportunities. Organizational intelligence only (never candidate "
            "ranking); marks unavailable metrics honestly and fabricates no "
            "enterprise statistics."
        ),
        input_fields=["limit"],
        engine="Hiring Intelligence",
    )

    def validate(self, tool_input: Dict[str, Any]) -> None:
        """No candidate id required — this is an organization-level tool."""
        return None

    def execute(self, tool_input: Dict[str, Any], context: ToolContext) -> ToolResult:
        """Analyze a bounded cohort and summarize the workforce intelligence."""
        repository = context.repository
        if repository is None:
            raise ToolValidationError("hiring_intelligence requires a candidate repository.")

        try:
            limit = int(tool_input.get("limit", _COPILOT_COHORT))
        except (TypeError, ValueError):
            limit = _COPILOT_COHORT

        engine = HiringIntelligenceEngine(insights_fn=context.insights_fn, ai_runner=_get_runner())
        report = engine.build(repository=repository, jd=context.jd, limit=limit)

        narrative = report.narrative
        health = next((k for k in report.kpis if k.name == "Hiring Health Index"), None)
        top_opts = [o for o in report.optimizations if o.priority in ("Critical", "High")]
        est_bottlenecks = [b for b in report.bottlenecks if b.register == "Estimated"]
        output = {
            "cohort_size": report.cohort_size,
            "data_available": report.data_available,
            "hiring_health": health.label if health else "n/a",
            "hiring_health_value": health.value if health else None,
            "kpis": [{"name": k.name, "label": k.label, "value": k.value, "register": k.register} for k in report.kpis],
            "distributions": {d.name: d.counts for d in report.distributions},
            "estimated_bottlenecks": [{"stage": b.stage, "severity": b.severity} for b in est_bottlenecks],
            "unavailable_trends": [t.name for t in report.trends if t.register == "Unavailable"],
            "team_metrics": [
                {"dimension": t.dimension, "group": t.group, "hiring_health": t.hiring_health}
                for t in report.team_metrics if t.register == "Observed"
            ],
            "optimizations": [
                {"area": o.area, "recommendation": o.recommendation, "priority": o.priority} for o in report.optimizations
            ],
            "forecast": [{"name": f.name, "growth": f.growth_label} for f in report.forecast],
            "executive_summary": narrative.executive_summary,
            "key_insights": list(narrative.key_insights),
            "strategic_recommendations": list(narrative.strategic_recommendations),
            "report_id": report.report_id,
        }
        return ToolResult(
            name=self.metadata.name,
            ok=True,
            output=output,
            summary=(
                f"Workforce intelligence over {report.cohort_size} candidate(s): Hiring Health "
                f"{health.label if health else 'n/a'}"
                + (f" ({health.value:.0f}/100)" if health and health.value is not None else "")
                + f". {len(top_opts)} priority optimization(s); "
                + (f"{len(est_bottlenecks)} estimated bottleneck(s). " if est_bottlenecks else "")
                + ("Trends/capacity unavailable — no analytics source connected. " if not report.data_available else "")
                + "Organizational intelligence only; no fabricated statistics."
            ),
            evidence_sources=["Hiring Intelligence"] + report.evidence_sources,
        )
