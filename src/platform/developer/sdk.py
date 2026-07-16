"""SDK surface for extensions (Module 12).

The :class:`PlatformSDK` is the *only* surface a plugin is handed on activation.
It exposes the event bus, the hook registry and a scoped logger — deliberately
narrow, so extensions integrate through well-defined seams instead of reaching
into platform internals. Real service access will be added behind capability
checks as the developer platform matures.
"""

from __future__ import annotations

from src.platform.developer.events import EventBus
from src.platform.developer.hooks import HookRegistry


class PlatformSDK:
    """The capability surface passed to a plugin at activation time."""

    def __init__(
        self,
        *,
        events: EventBus,
        hooks: HookRegistry,
        plugin_id: str = "",
    ) -> None:
        self.events = events
        self.hooks = hooks
        self.plugin_id = plugin_id
        self._log: list[str] = []

    def log(self, message: str) -> None:
        """Record a diagnostic message (namespaced to the plugin)."""
        self._log.append(f"[{self.plugin_id}] {message}")

    @property
    def logs(self) -> list[str]:
        """Return the plugin's recorded log lines."""
        return list(self._log)
