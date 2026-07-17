"""Job queue (Module 1).

A bounded, priority-ordered, tenant-safe job queue. Ordering is deterministic:
highest :class:`JobPriority` first, ties broken by insertion order (a monotonic
sequence), so there is no wall-clock or hash ordering. The queue is bounded —
enqueueing beyond ``capacity`` raises :class:`QueueOverflowError` (Module 7 —
queue overflow handling). Dequeues can be filtered to a single tenant so a
worker only ever pulls work it is entitled to (Module 15).
"""

from __future__ import annotations

from src.platform.runtime.common.errors import QueueOverflowError
from src.platform.runtime.jobs.models import Job, JobPriority


class JobQueue:
    """A bounded, priority-ordered, tenant-aware FIFO-within-priority queue."""

    def __init__(self, *, capacity: int = 10_000) -> None:
        self._capacity = capacity
        self._sequence = 0
        # Each entry: (priority_value, sequence, job_id, tenant_id)
        self._entries: list[tuple[int, int, str, str]] = []

    def __len__(self) -> int:
        return len(self._entries)

    @property
    def capacity(self) -> int:
        """Return the maximum number of queued jobs."""
        return self._capacity

    @property
    def is_full(self) -> bool:
        """Return whether the queue is at capacity."""
        return len(self._entries) >= self._capacity

    def enqueue(self, job: Job) -> None:
        """Add a job to the queue, or raise :class:`QueueOverflowError`."""
        if self.is_full:
            raise QueueOverflowError(f"job queue full (capacity={self._capacity})")
        self._sequence += 1
        priority = int(job.priority)
        self._entries.append((priority, self._sequence, job.id, job.tenant_id))
        # Keep highest priority first; stable within priority by sequence.
        self._entries.sort(key=lambda e: (-e[0], e[1]))

    def dequeue(self, *, tenant_id: str | None = None) -> str | None:
        """Pop the next job id (optionally restricted to one tenant)."""
        for index, (_prio, _seq, job_id, owner) in enumerate(self._entries):
            if tenant_id is not None and owner != tenant_id:
                continue
            del self._entries[index]
            return job_id
        return None

    def peek(self, *, tenant_id: str | None = None) -> str | None:
        """Return the next job id without removing it."""
        for _prio, _seq, job_id, owner in self._entries:
            if tenant_id is not None and owner != tenant_id:
                continue
            return job_id
        return None

    def remove(self, job_id: str) -> bool:
        """Remove a specific job id from the queue (e.g. on cancellation)."""
        for index, (_p, _s, jid, _o) in enumerate(self._entries):
            if jid == job_id:
                del self._entries[index]
                return True
        return False

    def size(self, *, tenant_id: str | None = None) -> int:
        """Return the queue depth (optionally for a single tenant)."""
        if tenant_id is None:
            return len(self._entries)
        return sum(1 for e in self._entries if e[3] == tenant_id)

    def depth_by_priority(self) -> dict[str, int]:
        """Return the queue depth broken down by priority name."""
        counts: dict[str, int] = {}
        for prio, _s, _j, _o in self._entries:
            name = JobPriority(prio).name
            counts[name] = counts.get(name, 0) + 1
        return counts
