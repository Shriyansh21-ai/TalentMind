"""Module 1 — Background Job Platform.

A deterministic, clock-driven job framework: definitions & handlers
(:class:`JobRegistry`), a bounded priority queue (:class:`JobQueue`), a
:class:`JobScheduler`, and the :class:`JobManager` control plane handling submit,
dispatch, retry, recovery, dependencies, cancellation, status and history. No
Celery — framework only.
"""

from __future__ import annotations

from src.platform.runtime.jobs.manager import JobManager
from src.platform.runtime.jobs.models import (
    Job,
    JobDefinition,
    JobHistoryEntry,
    JobPriority,
    JobStatus,
)
from src.platform.runtime.jobs.queue import JobQueue
from src.platform.runtime.jobs.registry import JobHandler, JobRegistry
from src.platform.runtime.jobs.scheduler import JobScheduler

__all__ = [
    "JobStatus",
    "JobPriority",
    "JobDefinition",
    "Job",
    "JobHistoryEntry",
    "JobRegistry",
    "JobHandler",
    "JobQueue",
    "JobScheduler",
    "JobManager",
]
