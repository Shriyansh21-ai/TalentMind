"""Cache-key construction for AI responses.

The key deliberately includes every dimension that can change an answer so a
cached response is never served for a different candidate, job, prompt version,
provider or model.
"""

from __future__ import annotations

import hashlib


def _digest(value: str) -> str:
    """Return a short, stable hex digest of ``value``."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def build_cache_key(
    *,
    agent: str,
    agent_version: str,
    prompt_version: str,
    provider: str,
    model: str,
    subject_id: str,
    scope: str,
) -> str:
    """Build a deterministic composite cache key.

    Args:
        agent: Agent name.
        agent_version: Agent version.
        prompt_version: Prompt-template version.
        provider: Provider key.
        model: Model id.
        subject_id: Primary entity (e.g. ``candidate_id``).
        scope: Secondary dimension (e.g. the job description — hashed here).

    Returns:
        A filesystem-safe cache key string.
    """
    scope_digest = _digest(scope or "")
    raw = "|".join(
        [agent, agent_version, prompt_version, provider, model, subject_id, scope_digest]
    )
    return f"{agent}.{subject_id}.{_digest(raw)}"
