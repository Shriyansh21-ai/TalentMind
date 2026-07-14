"""Service facade for the HiringAnalystAgent.

The UI depends only on this module — never on the runner, providers, cache or
agent internals. It owns a process-wide :class:`AgentRunner` singleton and turns
domain objects (insights + interview plan + JD) into a standardized
:class:`AgentResult`.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Dict, List

from src.ai.config.settings import AISettings
from src.ai.core.agent_config import AgentConfig
from src.ai.core.response import AgentResult
from src.ai.core.runner import AgentRunner
from src.ai.providers.factory import available_providers
from src.ai.telemetry.logger import get_default_logger

# Importing the agent module registers the agent + its deterministic composer.
from src.ai.agents.hiring_analyst import HiringAnalystInput, hiring_analyst_agent

from src.insights.models import CandidateInsights
from src.interview.models import InterviewPlan


@lru_cache(maxsize=1)
def get_runner() -> AgentRunner:
    """Return the process-wide :class:`AgentRunner` (built from env settings)."""
    return AgentRunner()


def analyze_candidate(
    insights: CandidateInsights,
    interview_plan: InterviewPlan,
    jd: str = "",
    *,
    force_refresh: bool = False,
) -> AgentResult:
    """Run the HiringAnalystAgent for one candidate and return the result.

    Args:
        insights: The candidate's shared insight bundle.
        interview_plan: The candidate's deterministic interview plan.
        jd: Raw job-description text.
        force_refresh: Bypass the cache and recompute.

    Returns:
        A standardized :class:`AgentResult` whose ``data`` is a ``HiringAnalysis``
        (or ``status == FAILED`` with an error message).
    """
    payload = HiringAnalystInput(
        insights=insights, interview_plan=interview_plan, jd=jd
    )
    config = AgentConfig(force_refresh=force_refresh)
    return get_runner().run(hiring_analyst_agent, payload, config)


def peek_cached_analysis(
    insights: CandidateInsights,
    interview_plan: InterviewPlan,
    jd: str = "",
) -> AgentResult | None:
    """Return a previously-cached analysis without calling any provider.

    Lets the UI show an existing analysis instantly on tab open while keeping
    generation strictly on-demand.
    """
    payload = HiringAnalystInput(
        insights=insights, interview_plan=interview_plan, jd=jd
    )
    return get_runner().peek(hiring_analyst_agent, payload)


def get_platform_status() -> Dict[str, Any]:
    """Return a snapshot of AI-platform configuration + provider health."""
    settings = AISettings.from_env()
    return {
        "provider": settings.provider,
        "model": settings.model,
        "cache_enabled": settings.cache_enabled,
        "strict": settings.strict,
        "providers_available": available_providers(settings),
    }


def recent_telemetry(limit: int = 25) -> List[Dict[str, Any]]:
    """Return recent AI telemetry events as plain dicts (newest last)."""
    settings = AISettings.from_env()
    logger = get_default_logger(settings.telemetry_dir)
    return [event.to_dict() for event in logger.recent(limit)]
