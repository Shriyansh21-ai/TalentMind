"""Context builder — assembles an :class:`AgentContext` for a run.

Small factory that centralizes request-id generation and context wiring so the
runner and future multi-turn agents build context the same way. Kept separate
from the runner to honour single-responsibility and to give future milestones a
seam for injecting memory-derived history.
"""

from __future__ import annotations

import uuid
from typing import Any

from src.ai.config.settings import AISettings
from src.ai.core.context import AgentContext
from src.ai.memory.base import BaseMemory


class ContextBuilder:
    """Builds request-scoped :class:`AgentContext` objects."""

    def __init__(self, memory: BaseMemory | None = None) -> None:
        """Optionally bind a memory backend to inject into every context."""
        self.memory = memory

    def build(
        self,
        *,
        agent_name: str,
        payload: Any,
        settings: AISettings,
        subject_id: str = "global",
        scope: str = "",
    ) -> AgentContext:
        """Create a fresh :class:`AgentContext` with a unique request id.

        Args:
            agent_name: The agent being run.
            payload: The agent's typed input.
            settings: Resolved platform settings.
            subject_id: Primary entity id (cache/telemetry dimension).
            scope: Secondary dimension (e.g. job description).

        Returns:
            A populated :class:`AgentContext`.
        """
        return AgentContext(
            request_id=uuid.uuid4().hex[:12],
            agent_name=agent_name,
            payload=payload,
            settings=settings,
            memory=self.memory,
            subject_id=subject_id,
            scope=scope,
        )
