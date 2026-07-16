"""Configuration platform (Module 5).

Named environment configuration profiles (development / testing / production /
enterprise / cloud / offline), a loader that merges a profile over shared
defaults, validation, export to ``.env`` / YAML-ish / JSON, environment
templates and self-documentation. Deterministic and offline; values are
non-secret settings only (secrets live in the security secret manager).
"""

from __future__ import annotations

import json

from pydantic import Field

from src.platform.common.models import PlatformModel
from src.platform.deployment.common.errors import ConfigurationPlatformError
from src.platform.deployment.common.models import Environment

# Shared defaults every profile inherits.
_BASE: dict[str, object] = {
    "app_name": "talentmind",
    "log_level": "INFO",
    "workers": 1,
    "cache_ttl_seconds": 300,
    "telemetry_enabled": True,
    "offline": False,
    "request_timeout_seconds": 30,
    "max_upload_mb": 25,
}

# Per-profile overrides on top of _BASE.
_PROFILES: dict[str, dict[str, object]] = {
    "development": {"log_level": "DEBUG", "workers": 1, "telemetry_enabled": False},
    "testing": {"log_level": "WARNING", "workers": 1, "cache_ttl_seconds": 60},
    "production": {"log_level": "INFO", "workers": 4, "cache_ttl_seconds": 600},
    "enterprise": {"log_level": "INFO", "workers": 8, "cache_ttl_seconds": 900,
                   "max_upload_mb": 100},
    "cloud": {"log_level": "INFO", "workers": 6, "cache_ttl_seconds": 600},
    "offline": {"log_level": "INFO", "workers": 2, "offline": True,
                "telemetry_enabled": False},
}

# Keys that must be present and their expected python types.
_SCHEMA: dict[str, type] = {
    "app_name": str,
    "log_level": str,
    "workers": int,
    "cache_ttl_seconds": int,
    "telemetry_enabled": bool,
    "offline": bool,
}
_VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}


class ConfigValidationResult(PlatformModel):
    """The result of validating a configuration mapping."""

    issues: list[str] = Field(default_factory=list)

    @property
    def ok(self) -> bool:
        """Return whether the configuration is valid."""
        return not self.issues


class ConfigurationPlatform:
    """Loads, validates, exports and documents environment config profiles."""

    def profiles(self) -> list[str]:
        """Return the names of the built-in configuration profiles."""
        return list(_PROFILES)

    def load(self, profile: str, *, overrides: dict[str, object] | None = None) -> dict[str, object]:
        """Return the merged configuration for ``profile`` (base ← profile ← overrides)."""
        if profile not in _PROFILES:
            raise ConfigurationPlatformError(f"unknown configuration profile '{profile}'")
        merged: dict[str, object] = {**_BASE, **_PROFILES[profile]}
        if overrides:
            merged.update(overrides)
        return merged

    def validate(self, config: dict[str, object]) -> ConfigValidationResult:
        """Validate a configuration mapping against the schema."""
        issues: list[str] = []
        for key, expected_type in _SCHEMA.items():
            if key not in config:
                issues.append(f"missing required key '{key}'")
                continue
            value = config[key]
            # bool is a subclass of int — guard against the common mix-up.
            if expected_type is int and isinstance(value, bool):
                issues.append(f"key '{key}' must be int, got bool")
            elif not isinstance(value, expected_type):
                issues.append(
                    f"key '{key}' must be {expected_type.__name__}, got {type(value).__name__}"
                )
        log_level = config.get("log_level")
        if isinstance(log_level, str) and log_level not in _VALID_LOG_LEVELS:
            issues.append(f"invalid log_level '{log_level}'")
        workers = config.get("workers")
        if isinstance(workers, int) and not isinstance(workers, bool) and workers < 1:
            issues.append("workers must be >= 1")
        return ConfigValidationResult(issues=issues)

    def export(self, profile: str, *, fmt: str = "env") -> str:
        """Export a profile's configuration as ``env`` / ``json`` / ``yaml``."""
        config = self.load(profile)
        fmt = fmt.lower()
        if fmt == "json":
            return json.dumps(config, indent=2, sort_keys=True)
        if fmt == "yaml":
            return "\n".join(f"{k}: {self._scalar(v)}" for k, v in sorted(config.items()))
        if fmt == "env":
            return "\n".join(
                f"TALENTMIND_{k.upper()}={self._scalar(v)}" for k, v in sorted(config.items())
            )
        raise ConfigurationPlatformError(f"unsupported export format '{fmt}'")

    def template(self, environment: Environment) -> dict[str, object]:
        """Return a config template skeleton for an environment (placeholders)."""
        base = dict(_BASE)
        base["environment"] = environment.value
        base["offline"] = environment.is_offline
        return base

    def document(self) -> str:
        """Return a Markdown table documenting every key and per-profile value."""
        keys = sorted(_BASE)
        header = "| key | " + " | ".join(_PROFILES) + " |"
        divider = "|" + "---|" * (len(_PROFILES) + 1)
        rows = [header, divider]
        for key in keys:
            cells = [str(self.load(p).get(key)) for p in _PROFILES]
            rows.append(f"| `{key}` | " + " | ".join(cells) + " |")
        return "\n".join(rows)

    @staticmethod
    def _scalar(value: object) -> str:
        if isinstance(value, bool):
            return "true" if value else "false"
        return str(value)
