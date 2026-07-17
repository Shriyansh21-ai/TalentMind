"""Runtime event framework (Module 12).

A thin, typed façade over the Milestone 2 :class:`EnterpriseEventBus` that
publishes runtime lifecycle events (job / worker / queue / cache / health /
performance / failure / recovery / metrics) onto ``runtime.*`` topics. It reuses
the existing bus verbatim — the same ordering, replay and dead-letter guarantees
apply to runtime events — rather than introducing a second event system.
"""

from __future__ import annotations

from enum import Enum

from src.platform.common.clock import Clock, SystemClock
from src.platform.integrations.events.bus import EnterpriseEventBus
from src.platform.integrations.events.models import EnterpriseEvent, EventType


class RuntimeEventType(str, Enum):
    """The families of runtime event, mapped to ``runtime.<family>.*`` topics."""

    JOB = "job"
    WORKER = "worker"
    QUEUE = "queue"
    CACHE = "cache"
    HEALTH = "health"
    PERFORMANCE = "performance"
    FAILURE = "failure"
    RECOVERY = "recovery"
    METRICS = "metrics"


class RuntimeEventPublisher:
    """Publishes typed runtime events onto the shared enterprise event bus."""

    TOPIC_PREFIX = "runtime"

    def __init__(
        self,
        bus: EnterpriseEventBus | None = None,
        *,
        clock: Clock | None = None,
    ) -> None:
        self._clock = clock or SystemClock()
        self.bus = bus or EnterpriseEventBus(clock=self._clock)

    def publish(
        self,
        family: RuntimeEventType,
        action: str,
        *,
        payload: dict[str, object] | None = None,
        tenant_id: str | None = None,
    ) -> EnterpriseEvent:
        """Publish ``runtime.<family>.<action>`` onto the bus."""
        topic = f"{self.TOPIC_PREFIX}.{family.value}.{action}"
        return self.bus.publish(
            topic,
            payload=payload or {},
            event_type=EventType.SYSTEM,
            tenant_id=tenant_id,
            name=action,
        )

    # -- typed convenience helpers -----------------------------------------

    def job(self, action: str, **payload: object) -> EnterpriseEvent:
        """Publish a ``runtime.job.<action>`` event."""
        tenant_id = payload.pop("tenant_id", None)  # type: ignore[assignment]
        return self.publish(
            RuntimeEventType.JOB,
            action,
            payload=payload,
            tenant_id=tenant_id,  # type: ignore[arg-type]
        )

    def worker(self, action: str, **payload: object) -> EnterpriseEvent:
        """Publish a ``runtime.worker.<action>`` event."""
        return self.publish(RuntimeEventType.WORKER, action, payload=payload)

    def queue(self, action: str, **payload: object) -> EnterpriseEvent:
        """Publish a ``runtime.queue.<action>`` event."""
        return self.publish(RuntimeEventType.QUEUE, action, payload=payload)

    def failure(self, action: str, **payload: object) -> EnterpriseEvent:
        """Publish a ``runtime.failure.<action>`` event."""
        return self.publish(RuntimeEventType.FAILURE, action, payload=payload)

    def recovery(self, action: str, **payload: object) -> EnterpriseEvent:
        """Publish a ``runtime.recovery.<action>`` event."""
        return self.publish(RuntimeEventType.RECOVERY, action, payload=payload)

    def history(self, *, tenant_id: str | None = None) -> list[EnterpriseEvent]:
        """Return runtime events from the bus log (optionally by tenant)."""
        return [
            e
            for e in self.bus.history(tenant_id=tenant_id)
            if e.topic.startswith(self.TOPIC_PREFIX + ".")
        ]
