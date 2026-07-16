"""Plugin system + extension registry (Module 12).

Defines the :class:`Plugin` seam, a declarative :class:`PluginManifest`, and the
:class:`ExtensionRegistry` that manages plugin lifecycle (register → enable →
disable). No plugins ship — this is the framework a future marketplace and
third-party extensions build on. :class:`Marketplace` is a catalogue stub.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from src.platform.common.errors import ConflictError, NotFoundError
from src.platform.common.models import PlatformModel
from src.platform.developer.events import EventBus
from src.platform.developer.hooks import HookRegistry
from src.platform.developer.sdk import PlatformSDK


class PluginManifest(PlatformModel):
    """Declarative metadata describing a plugin."""

    id: str
    name: str
    version: str = "0.1.0"
    description: str = ""
    author: str = ""
    hooks: list[str] = []
    events: list[str] = []
    permissions: list[str] = []


@runtime_checkable
class Plugin(Protocol):
    """A platform extension with a lifecycle."""

    manifest: PluginManifest

    def activate(self, sdk: PlatformSDK) -> None:
        """Wire the plugin's hooks/subscriptions using the SDK."""
        ...

    def deactivate(self) -> None:
        """Tear down anything the plugin set up."""
        ...


class RegisteredPlugin(PlatformModel):
    """Registry bookkeeping for a plugin (state, not the instance)."""

    manifest: PluginManifest
    enabled: bool = False


class ExtensionRegistry:
    """Register and manage the lifecycle of plugins."""

    def __init__(
        self, *, events: EventBus | None = None, hooks: HookRegistry | None = None
    ) -> None:
        self.events = events or EventBus()
        self.hooks = hooks or HookRegistry()
        self._plugins: dict[str, Plugin] = {}
        self._state: dict[str, RegisteredPlugin] = {}

    def register(self, plugin: Plugin) -> RegisteredPlugin:
        """Register a plugin (disabled until explicitly enabled)."""
        plugin_id = plugin.manifest.id
        if plugin_id in self._plugins:
            raise ConflictError(f"plugin '{plugin_id}' already registered")
        self._plugins[plugin_id] = plugin
        state = RegisteredPlugin(manifest=plugin.manifest, enabled=False)
        self._state[plugin_id] = state
        return state

    def enable(self, plugin_id: str) -> RegisteredPlugin:
        """Activate a registered plugin, handing it a scoped SDK."""
        plugin = self._require(plugin_id)
        state = self._state[plugin_id]
        if not state.enabled:
            sdk = PlatformSDK(
                events=self.events, hooks=self.hooks, plugin_id=plugin_id
            )
            plugin.activate(sdk)
            state.enabled = True
        return state

    def disable(self, plugin_id: str) -> RegisteredPlugin:
        """Deactivate an enabled plugin."""
        plugin = self._require(plugin_id)
        state = self._state[plugin_id]
        if state.enabled:
            plugin.deactivate()
            state.enabled = False
        return state

    def list(self) -> list[RegisteredPlugin]:
        """Return the registration state of all plugins."""
        return list(self._state.values())

    def _require(self, plugin_id: str) -> Plugin:
        """Return a registered plugin or raise :class:`NotFoundError`."""
        if plugin_id not in self._plugins:
            raise NotFoundError(f"plugin '{plugin_id}' not registered")
        return self._plugins[plugin_id]


class Marketplace(PlatformModel):
    """A catalogue stub of installable extensions (future marketplace)."""

    listings: list[PluginManifest] = []

    def publish(self, manifest: PluginManifest) -> None:
        """Add a manifest to the marketplace catalogue."""
        self.listings.append(manifest)

    def search(self, term: str) -> list[PluginManifest]:
        """Return catalogue entries whose name/description matches ``term``."""
        needle = term.lower()
        return [
            m
            for m in self.listings
            if needle in m.name.lower() or needle in m.description.lower()
        ]
