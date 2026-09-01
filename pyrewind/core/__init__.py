"""Core architecture components for pyrewind v2."""

from .event_system import Event, EventDispatcher
from .plugin import Plugin, PluginRegistry
from .storage import StorageBackend, MemoryStorageBackend
from .strategy import SerializationStrategy

__all__ = [
    "Event",
    "EventDispatcher",
    "Plugin",
    "PluginRegistry",
    "StorageBackend",
    "MemoryStorageBackend",
    "SerializationStrategy",
]
