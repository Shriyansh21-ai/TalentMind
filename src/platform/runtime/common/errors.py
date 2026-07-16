"""Runtime-platform exception hierarchy (Phase 6 / Milestone 3).

Extends the platform-wide :class:`~src.platform.common.errors.PlatformError`
hierarchy with errors specific to the Enterprise Runtime Platform (jobs,
workers, queues, cache, load management, resilience). Named ``Runtime*`` to
avoid colliding with the builtin :class:`RuntimeError`; no business-logic
exceptions live here — only runtime/infrastructure concerns.
"""

from __future__ import annotations

from src.platform.common.errors import PlatformError


class RuntimePlatformError(PlatformError):
    """Base class for every enterprise-runtime error."""

    code = "runtime_error"


class JobError(RuntimePlatformError):
    """Base for background-job errors."""

    code = "job_error"


class JobNotFoundError(JobError):
    """Raised when a job id cannot be found (within tenant scope)."""

    code = "job_not_found"


class JobCancelledError(JobError):
    """Raised when an operation targets a cancelled job."""

    code = "job_cancelled"


class QueueOverflowError(RuntimePlatformError):
    """Raised when a bounded queue is full and cannot accept more work."""

    code = "queue_overflow"


class WorkerError(RuntimePlatformError):
    """Raised on an invalid worker lifecycle transition or unknown worker."""

    code = "worker_error"


class TaskTimeoutError(RuntimePlatformError):
    """Raised when a task exceeds its configured timeout budget."""

    code = "task_timeout"


class CircuitOpenError(RuntimePlatformError):
    """Raised when a call is short-circuited by an open circuit breaker."""

    code = "circuit_open"


class ConcurrencyLimitError(RuntimePlatformError):
    """Raised when a concurrency/bulkhead limit would be exceeded."""

    code = "concurrency_limit_exceeded"


class ResourceLimitError(RuntimePlatformError):
    """Raised when a configured resource limit would be exceeded."""

    code = "resource_limit_exceeded"


class RuntimeValidationError(RuntimePlatformError):
    """Raised when a runtime input fails validation (Module 15)."""

    code = "runtime_validation_error"
