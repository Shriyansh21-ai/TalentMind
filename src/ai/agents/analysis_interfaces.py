"""Cross-agent extension points (Module 15).

`ResumeAnalystAgent` and `JDAnalystAgent` are fully independent — neither imports
the other, and this module contains **no comparison logic**. It only *prepares*
the seam a future agent (e.g. a Fit / Match / Gap agent) will use to consume both
analyses without any redesign.

Two prepared extension points:

1. :class:`AnalysisProvider` — the structural contract both analyses already
   satisfy (a validated :class:`BaseAIResponse` with an ``evidence`` list and a
   ``confidence_note``). A future consumer can type against this.
2. :class:`CombinedAnalysisInputs` — a typed container a future orchestration
   task would carry, pairing a resume analysis with a JD analysis. The
   orchestration capabilities are already distinct (``"resume_analysis"`` and
   ``"jd_analysis"``), so a future FitAgent is just a new
   :class:`~src.ai.orchestration.registry.agent_registry.OrchestrationAgent`
   depending on both — no orchestration change required.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Optional, Protocol, runtime_checkable


@runtime_checkable
class AnalysisProvider(Protocol):
    """The shape any agent analysis exposes for downstream consumption.

    Both :class:`~src.ai.agents.resume.schemas.ResumeAnalysis` and
    :class:`~src.ai.agents.jd.schemas.JDAnalysis` satisfy this structurally.
    """

    executive_summary: str
    confidence_note: str
    evidence: List[str]

    def to_dict(self) -> dict:  # provided by BaseAIResponse
        """Return a plain dict of the analysis."""
        ...


# Capability names used by the orchestration registry — the stable routing keys a
# future cross-agent consumer would depend on.
RESUME_ANALYSIS_CAPABILITY = "resume_analysis"
JD_ANALYSIS_CAPABILITY = "jd_analysis"


@dataclass
class CombinedAnalysisInputs:
    """A prepared container pairing the two independent analyses (Module 15).

    Intentionally logic-free: it is the *input contract* a future Fit/Match/Gap
    agent would accept. This milestone does not compute anything from it.
    """

    resume_analysis: Optional[Any] = None  # ResumeAnalysis
    jd_analysis: Optional[Any] = None       # JDAnalysis

    @property
    def ready(self) -> bool:
        """Return whether both analyses are present (a future consumer's guard)."""
        return self.resume_analysis is not None and self.jd_analysis is not None
