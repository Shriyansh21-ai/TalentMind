"""Tool abstraction for the AI Platform.

Every deterministic engine is exposed to AI agents (starting with the Recruiter
Copilot) as a :class:`BaseTool`. A tool has typed metadata, validates its input,
and returns a standardized :class:`ToolResult`. Tools never *reimplement* an
engine — they call the existing deterministic function and package the output.

The engines are reached through a :class:`CandidateRepository` (dependency
injection) so the tools — and everything above them — are testable without the
production dataset or the FAISS index.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from src.models.candidates import Candidate
from src.insights.builder import build_insights
from src.insights.models import CandidateInsights


class ToolError(Exception):
    """Base class for tool-layer errors."""


class ToolValidationError(ToolError):
    """Raised when a tool receives invalid input."""


class CandidateRepository(ABC):
    """Dependency-injected access to the candidate pool + semantic search.

    Concrete implementations wire this to the loaded dataset + FAISS in the app,
    or to synthetic candidates in tests. Tools depend only on this interface.
    """

    @abstractmethod
    def get(self, candidate_id: str) -> Optional[Candidate]:
        """Return a candidate by id, or ``None`` if unknown."""

    @abstractmethod
    def search(self, query: str, top_k: int = 5) -> List[tuple]:
        """Return ``[(candidate, score), ...]`` for a free-text/semantic query."""

    @abstractmethod
    def sample(self, limit: int = 200) -> List[Candidate]:
        """Return up to ``limit`` candidates (for aggregate/dashboard tools)."""


@dataclass
class ToolContext:
    """Execution context passed to every tool.

    Attributes:
        repository: The candidate repository (DI seam to the engines/data).
        jd: The current job-description text (used by JD-dependent engines).
        insights_fn: Function building a :class:`CandidateInsights` bundle; the UI
            passes a cached version so the intelligence engines run once per
            candidate per session (reuses the platform's caches — Module 12).
        extra: Free-form additional context.
    """

    repository: CandidateRepository
    jd: str = ""
    insights_fn: Callable[[Candidate, str], CandidateInsights] = None  # type: ignore[assignment]
    extra: Dict[str, Any] = field(default_factory=dict)

    def build_insights(self, candidate: Candidate) -> CandidateInsights:
        """Build (or fetch cached) insights for ``candidate`` under the current JD."""
        fn = self.insights_fn or (lambda c, jd: build_insights(c, jd))
        return fn(candidate, self.jd)


@dataclass
class ToolMetadata:
    """Static description of a tool.

    Attributes:
        name: Unique tool key (used by the registry, planner and telemetry).
        description: One-line description for planning / display.
        input_fields: Human-readable expected input fields.
        engine: The deterministic engine this tool exposes.
    """

    name: str
    description: str
    input_fields: List[str] = field(default_factory=list)
    engine: str = ""


@dataclass
class ToolResult:
    """Standardized result of running a tool.

    Attributes:
        name: Tool name.
        ok: Whether execution succeeded.
        output: Structured, JSON-serializable output (never raw resumes/JSON dumps).
        summary: One-line human summary of what happened.
        evidence_sources: The deterministic engine(s) that produced the output.
        confidence: 0-100 confidence in the tool's output.
        latency_ms: Wall-clock execution time.
        error: Error message when ``ok`` is False.
    """

    name: str
    ok: bool = True
    output: Dict[str, Any] = field(default_factory=dict)
    summary: str = ""
    evidence_sources: List[str] = field(default_factory=list)
    confidence: float = 100.0
    latency_ms: float = 0.0
    error: Optional[str] = None

    def to_summary_dict(self) -> Dict[str, Any]:
        """Return a compact dict for UI tool-visibility cards / telemetry."""
        return {
            "name": self.name,
            "ok": self.ok,
            "summary": self.summary,
            "evidence_sources": list(self.evidence_sources),
            "confidence": self.confidence,
            "latency_ms": round(self.latency_ms, 2),
            "error": self.error,
        }


class BaseTool(ABC):
    """Abstract tool. Subclasses set :attr:`metadata` and implement :meth:`execute`."""

    metadata: ToolMetadata

    def validate(self, tool_input: Dict[str, Any]) -> None:
        """Validate ``tool_input`` before execution (override as needed).

        Raises:
            ToolValidationError: If the input is invalid.
        """

    @abstractmethod
    def execute(self, tool_input: Dict[str, Any], context: ToolContext) -> ToolResult:
        """Run the underlying engine and return a :class:`ToolResult`."""

    def run(self, tool_input: Dict[str, Any], context: ToolContext) -> ToolResult:
        """Validate + execute with timing and uniform error handling."""
        start = time.perf_counter()
        try:
            self.validate(tool_input or {})
            result = self.execute(tool_input or {}, context)
        except ToolError as exc:
            result = ToolResult(name=self.metadata.name, ok=False, error=str(exc))
        except Exception as exc:  # normalize unexpected engine errors
            result = ToolResult(
                name=self.metadata.name,
                ok=False,
                error=f"{type(exc).__name__}: {exc}",
            )
        result.name = self.metadata.name
        result.latency_ms = (time.perf_counter() - start) * 1000.0
        return result
