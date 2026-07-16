"""Health monitoring models (Module 6)."""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from src.platform.common.models import PlatformModel
from src.platform.runtime.common.models import HealthState


class ComponentHealth(PlatformModel):
    """The health of a single runtime component."""

    name: str
    state: HealthState = HealthState.UNKNOWN
    message: str = ""
    details: dict[str, object] = Field(default_factory=dict)
    checked_at: datetime = Field(default_factory=lambda: datetime.min)

    @property
    def healthy(self) -> bool:
        """Return whether the component is healthy."""
        return self.state == HealthState.HEALTHY


class HealthReport(PlatformModel):
    """An aggregated health report across every registered component."""

    state: HealthState = HealthState.UNKNOWN
    components: list[ComponentHealth] = Field(default_factory=list)
    checked_at: datetime = Field(default_factory=lambda: datetime.min)

    @property
    def healthy(self) -> bool:
        """Return whether the platform as a whole is healthy."""
        return self.state == HealthState.HEALTHY

    def component(self, name: str) -> ComponentHealth | None:
        """Return a named component's health (or ``None``)."""
        return next((c for c in self.components if c.name == name), None)
