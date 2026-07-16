"""Module 10 — Enterprise Event Bus.

Publish/subscribe with topics, wildcard routing, strict ordering, an append-only
replay log and a dead-letter queue. Synchronous and in-memory, with a
:class:`MessageBroker` seam a future Kafka/RabbitMQ backend binds to.
"""

from __future__ import annotations

from src.platform.integrations.events.bus import (
    EnterpriseEventBus,
    EventHandler,
    MessageBroker,
    topic_matches,
)
from src.platform.integrations.events.models import (
    DeadLetterEntry,
    EnterpriseEvent,
    EventType,
    Subscription,
)

__all__ = [
    "EventType",
    "EnterpriseEvent",
    "DeadLetterEntry",
    "Subscription",
    "EnterpriseEventBus",
    "MessageBroker",
    "EventHandler",
    "topic_matches",
]
