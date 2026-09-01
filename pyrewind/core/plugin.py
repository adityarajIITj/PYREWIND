"""Plugin system for extensibility in pyrewind."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from .event_system import EventDispatcher, Event


class Plugin(ABC):
    """Base class for all pyrewind plugins.

    Plugins can hook into the trace collection process, storage, analysis, and export.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique plugin name."""
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        """Plugin version."""
        pass

    def initialize(self, config: dict[str, Any] | None = None) -> None:
        """Initialize the plugin with optional configuration.

        Args:
            config: Plugin-specific configuration dictionary
        """
        pass

    def on_trace_started(self, trace_id: str, func_name: str) -> None:
        """Called when a trace starts."""
        pass

    def on_trace_step(
        self, trace_id: str, step_id: int, filename: str, line_no: int, locals_dict: dict[str, Any]
    ) -> None:
        """Called for each recorded step in the trace."""
        pass

    def on_trace_finished(
        self, trace_id: str, duration_ns: int, exception: Exception | None = None
    ) -> None:
        """Called when a trace finishes."""
        pass

    def on_event(self, event: Event) -> None:
        """Called for any event emitted by the event dispatcher."""
        pass

    def shutdown(self) -> None:
        """Called when the plugin is being unloaded."""
        pass


class PluginRegistry:
    """Manages plugin registration, discovery, and lifecycle.

    Features:
    - Register and unregister plugins
    - Enable/disable plugins per-instance
    - Plugin dependency resolution
    - Event hook integration
    """

    def __init__(self, dispatcher: EventDispatcher | None = None) -> None:
        self._plugins: Dict[str, Plugin] = {}
        self._enabled: Dict[str, bool] = {}
        self._dispatcher = dispatcher

    def register(
        self,
        plugin: Plugin,
        enabled: bool = True,
        config: dict[str, Any] | None = None,
    ) -> None:
        """Register a plugin.

        Args:
            plugin: Plugin instance to register
            enabled: Whether the plugin starts enabled
            config: Optional plugin configuration
        """
        if plugin.name in self._plugins:
            raise ValueError(f"Plugin {plugin.name!r} is already registered")

        try:
            plugin.initialize(config)
        except Exception as e:
            raise RuntimeError(f"Failed to initialize plugin {plugin.name!r}: {e}") from e

        self._plugins[plugin.name] = plugin
        self._enabled[plugin.name] = enabled

        # Subscribe to events if dispatcher is available
        if self._dispatcher is not None:
            self._dispatcher.subscribe(None, plugin.on_event)

    def unregister(self, name: str) -> None:
        """Unregister and shutdown a plugin.

        Args:
            name: Name of the plugin to unregister
        """
        if name not in self._plugins:
            raise ValueError(f"Plugin {name!r} is not registered")

        plugin = self._plugins.pop(name)
        del self._enabled[name]

        try:
            plugin.shutdown()
        except Exception:
            pass  # Ignore shutdown errors

    def get(self, name: str) -> Plugin | None:
        """Get a registered plugin by name."""
        return self._plugins.get(name)

    def list_plugins(self, enabled_only: bool = False) -> list[str]:
        """List registered plugin names.

        Args:
            enabled_only: If True, only return enabled plugins

        Returns:
            List of plugin names
        """
        if enabled_only:
            return [name for name, enabled in self._enabled.items() if enabled]
        return list(self._plugins.keys())

    def is_enabled(self, name: str) -> bool:
        """Check if a plugin is enabled."""
        return self._enabled.get(name, False)

    def enable(self, name: str) -> None:
        """Enable a plugin."""
        if name not in self._plugins:
            raise ValueError(f"Plugin {name!r} is not registered")
        self._enabled[name] = True

    def disable(self, name: str) -> None:
        """Disable a plugin."""
        if name not in self._plugins:
            raise ValueError(f"Plugin {name!r} is not registered")
        self._enabled[name] = False

    def notify_trace_started(self, trace_id: str, func_name: str) -> None:
        """Notify all enabled plugins that a trace started."""
        for name, plugin in self._plugins.items():
            if self._enabled[name]:
                try:
                    plugin.on_trace_started(trace_id, func_name)
                except Exception:
                    pass  # Ignore plugin errors

    def notify_trace_step(
        self,
        trace_id: str,
        step_id: int,
        filename: str,
        line_no: int,
        locals_dict: dict[str, Any],
    ) -> None:
        """Notify all enabled plugins of a trace step."""
        for name, plugin in self._plugins.items():
            if self._enabled[name]:
                try:
                    plugin.on_trace_step(trace_id, step_id, filename, line_no, locals_dict)
                except Exception:
                    pass  # Ignore plugin errors

    def notify_trace_finished(
        self, trace_id: str, duration_ns: int, exception: Exception | None = None
    ) -> None:
        """Notify all enabled plugins that a trace finished."""
        for name, plugin in self._plugins.items():
            if self._enabled[name]:
                try:
                    plugin.on_trace_finished(trace_id, duration_ns, exception)
                except Exception:
                    pass  # Ignore plugin errors

    def shutdown_all(self) -> None:
        """Shutdown all plugins."""
        for plugin in list(self._plugins.values()):
            try:
                plugin.shutdown()
            except Exception:
                pass
