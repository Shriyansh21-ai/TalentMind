"""Agent identity metadata.

Every agent declares an :class:`AgentMetadata`. It is used by the registry, the
cache key, telemetry and the UI so an agent's identity is defined in exactly one
place.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass(frozen=True)
class AgentMetadata:
    """Static identity of an agent.

    Attributes:
        name: Unique agent key (e.g. ``"hiring_analyst"``).
        version: Semantic-ish agent version; participates in the cache key so a
            new agent version never serves stale cached analyses.
        title: Human-friendly display name.
        description: One-line description of what the agent does.
        prompt_id: Prompt-template id the agent renders.
        prompt_version: Prompt-template version (participates in the cache key).
        tags: Free-form capability tags for discovery / filtering.
    """

    name: str
    version: str
    title: str
    description: str
    prompt_id: str
    prompt_version: str
    tags: List[str] = field(default_factory=list)
