"""Agent communication layer — message bus + typed messages (Module 5)."""

from __future__ import annotations

from src.ai.orchestration.communication.bus import MessageBus
from src.ai.orchestration.communication.messages import (
    MessageType,
    SharedMessage,
)

__all__ = ["MessageType", "SharedMessage", "MessageBus"]
