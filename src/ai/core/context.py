"""Request-scoped agent execution context.

An :class:`AgentContext` is created by the runner for each invocation and passed
through the agent lifecycle. It carries everything an agent needs to do its work
without reaching into globals: the typed input, the resolved settings, a memory
handle and a place for cross-cutting scratch data. This is the dependency-
injection seam of the platform.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.ai.config.settings import AISettings


@dataclass
class AgentContext:
    """Everything an agent needs for a single run.

    Attributes:
        request_id: Stable id for this invocation (telemetry correlation).
        agent_name: Name of the agent being run.
        payload: The agent's typed input object (agent-specific).
        settings: Resolved platform settings for this run.
        memory: Optional memory handle (framework-agnostic).
        subject_id: Primary entity id for cache/telemetry (e.g. candidate id).
        scope: Secondary cache/telemetry dimension (e.g. hashed JD).
        metadata: Free-form scratch data shared across lifecycle stages.
    """

    request_id: str
    agent_name: str
    payload: Any
    settings: AISettings
    memory: Any | None = None
    subject_id: str = "global"
    scope: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
