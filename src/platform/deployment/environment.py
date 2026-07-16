"""Environment detection (Module 1).

Resolves the active :class:`Environment` from an environment-variable mapping
(``TALENTMIND_ENV``), defaulting to DEVELOPMENT. The env mapping is injectable
so detection is fully deterministic and testable — it never reads the real
process environment unless asked to.
"""

from __future__ import annotations

import os

from src.platform.deployment.common.models import Environment

ENV_VAR = "TALENTMIND_ENV"
_ALIASES = {
    "dev": Environment.DEVELOPMENT,
    "develop": Environment.DEVELOPMENT,
    "test": Environment.TESTING,
    "stage": Environment.STAGING,
    "prod": Environment.PRODUCTION,
    "airgap": Environment.AIR_GAPPED,
    "offline": Environment.OFFLINE_ENTERPRISE,
}


class EnvironmentDetector:
    """Detects the active deployment environment deterministically."""

    def __init__(self, env: dict[str, str] | None = None) -> None:
        # Default to a *copy* of the real environment; tests pass an explicit map.
        self._env = dict(env) if env is not None else dict(os.environ)

    def detect(self) -> Environment:
        """Return the resolved environment (default DEVELOPMENT)."""
        raw = (self._env.get(ENV_VAR) or "").strip().lower()
        if not raw:
            return Environment.DEVELOPMENT
        if raw in _ALIASES:
            return _ALIASES[raw]
        try:
            return Environment(raw)
        except ValueError:
            return Environment.DEVELOPMENT

    def is_production(self) -> bool:
        """Return whether the active environment is PRODUCTION."""
        return self.detect() == Environment.PRODUCTION

    def is_offline(self) -> bool:
        """Return whether the active environment is offline by design."""
        return self.detect().is_offline

    def describe(self) -> dict[str, object]:
        """Return a small, non-secret description of the detected environment."""
        env = self.detect()
        return {
            "environment": env.value,
            "production_like": env.is_production_like,
            "offline": env.is_offline,
            "source": ENV_VAR if self._env.get(ENV_VAR) else "default",
        }
