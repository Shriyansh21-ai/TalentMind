"""Module 3 — Task Execution Engine.

Sequential, parallel, batch, chunk, priority and rate-controlled task execution,
each task run through the shared resilience pipeline (retry + timeout) with
cooperative cancellation and structured execution reports.
"""

from __future__ import annotations

from src.platform.runtime.execution.engine import TaskExecutionEngine
from src.platform.runtime.execution.models import (
    ExecutionReport,
    ExecutionStatus,
    Task,
    TaskContext,
    TaskPriority,
    TaskResult,
)

__all__ = [
    "Task",
    "TaskContext",
    "TaskResult",
    "TaskPriority",
    "ExecutionStatus",
    "ExecutionReport",
    "TaskExecutionEngine",
]
