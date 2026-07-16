"""Performance benchmark framework (Module 9).

Runs callables and records **real** timing statistics (via
:func:`time.perf_counter`) across benchmark categories (cold/warm start, memory,
CPU, AI latency, cache, search, multi-agent, throughput). Optional system
metrics come from :mod:`psutil` when present. No synthetic inflation — every
number is measured; reports summarise min/avg/max/p95 and throughput.
"""

from __future__ import annotations

import time
from enum import Enum
from typing import Callable

from pydantic import Field

from src.platform.common.models import PlatformModel
from src.platform.deployment.common.errors import BenchmarkError

try:  # optional — system metrics are best-effort.
    import psutil as _psutil  # type: ignore
except Exception:  # pragma: no cover
    _psutil = None


class BenchmarkCategory(str, Enum):
    """The category a benchmark measures."""

    COLD_START = "cold_start"
    WARM_START = "warm_start"
    MEMORY = "memory"
    CPU = "cpu"
    AI_LATENCY = "ai_latency"
    CACHE = "cache"
    SEARCH = "search"
    MULTI_AGENT = "multi_agent"
    THROUGHPUT = "throughput"


class BenchmarkResult(PlatformModel):
    """Measured statistics for one benchmark."""

    name: str
    category: BenchmarkCategory
    iterations: int = 0
    min_ms: float = 0.0
    max_ms: float = 0.0
    avg_ms: float = 0.0
    p95_ms: float = 0.0
    ops_per_second: float = 0.0

    @property
    def total_ms(self) -> float:
        """Return the total measured time in milliseconds."""
        return self.avg_ms * self.iterations


class BenchmarkReport(PlatformModel):
    """A collection of benchmark results plus optional system snapshot."""

    results: list[BenchmarkResult] = Field(default_factory=list)
    system: dict[str, object] = Field(default_factory=dict)

    def by_category(self, category: BenchmarkCategory) -> list[BenchmarkResult]:
        """Return results in a given category."""
        return [r for r in self.results if r.category == category]


class BenchmarkRunner:
    """Measures callables and aggregates honest performance statistics."""

    def __init__(self) -> None:
        self._results: list[BenchmarkResult] = []

    def run(
        self,
        name: str,
        category: BenchmarkCategory,
        fn: Callable[[], object],
        *,
        iterations: int = 100,
        warmup: int = 0,
    ) -> BenchmarkResult:
        """Run ``fn`` ``iterations`` times and record real timing statistics."""
        if iterations < 1:
            raise BenchmarkError("iterations must be >= 1")
        for _ in range(max(0, warmup)):
            fn()
        samples: list[float] = []
        for _ in range(iterations):
            start = time.perf_counter()
            fn()
            samples.append((time.perf_counter() - start) * 1000.0)
        samples.sort()
        total_ms = sum(samples)
        avg = total_ms / iterations
        p95_index = min(len(samples) - 1, int(round(0.95 * (len(samples) - 1))))
        result = BenchmarkResult(
            name=name, category=category, iterations=iterations,
            min_ms=samples[0], max_ms=samples[-1], avg_ms=avg,
            p95_ms=samples[p95_index],
            ops_per_second=(1000.0 / avg) if avg > 0 else 0.0,
        )
        self._results.append(result)
        return result

    def results(self) -> list[BenchmarkResult]:
        """Return every recorded result."""
        return list(self._results)

    def system_snapshot(self) -> dict[str, object]:
        """Return a best-effort system snapshot (empty if psutil is absent)."""
        if _psutil is None:
            return {"available": False}
        try:
            vm = _psutil.virtual_memory()
            return {
                "available": True,
                "cpu_percent": _psutil.cpu_percent(interval=None),
                "memory_percent": vm.percent,
                "memory_used_mb": round(vm.used / (1024 * 1024), 1),
            }
        except Exception:  # pragma: no cover
            return {"available": False}

    def report(self) -> BenchmarkReport:
        """Return a report of all results plus a system snapshot."""
        return BenchmarkReport(results=self.results(), system=self.system_snapshot())
