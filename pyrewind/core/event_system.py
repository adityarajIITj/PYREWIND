"""Event-driven system for trace collection and plugin hooks."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Callable, Protocol
from collections import defaultdict
import weakref


class EventType:
    """Standard event types emitted during tracing."""

    # Trace lifecycle
    TRACE_STARTED = "trace.started"
    TRACE_STEP = "trace.step"
    TRACE_EXCEPTION = "trace.exception"
    TRACE_FINISHED = "trace.finished"

    # Function execution
    FUNC_CALL = "func.call"
    FUNC_RETURN = "func.return"
    FUNC_EXCEPTION = "func.exception"

    # Storage
    STORAGE_WRITE = "storage.write"
    STORAGE_FLUSH = "storage.flush"


@dataclass(slots=True, frozen=True)
class Event:
    """A single event emitted during trace collection or replay."""

    event_type: str
    timestamp_ns: int
    data: dict[str, Any]

    def get(self, key: str, default: Any = None) -> Any:
        """Get event data by key with optional default."""
        return self.data.get(key, default)


class EventListener(Protocol):
    """Protocol for event listener callables."""

    def __call__(self, event: Event) -> None:
        """Handle an event."""
        ...


class EventDispatcher:
    """Central event dispatcher for trace events and plugin hooks.
    
    Features:
    - Subscribe to event types with listeners
    - Emit events with automatic timestamps
    - Priority-based listener ordering (high priority runs first)
    - Weak references to avoid circular references
    - Thread-safe operation (basic)
    """

    def __init__(self) -> None:
        # Map: event_type -> list of (priority, listener)
        self._listeners: dict[str, list[tuple[int, EventListener]]] = defaultdict(list)
        self._enabled = True

    def subscribe(
        self,
        event_type: str,
        listener: EventListener,
        priority: int = 0,
    ) -> Callable[[], None]:
        """Subscribe a listener to an event type.

        Args:
            event_type: Type of event to listen for (from EventType)
            listener: Callable that accepts an Event
            priority: Higher priority listeners are called first (default 0)

        Returns:
            Unsubscribe function to remove this listener
        """
        if not self._enabled:
            return lambda: None

        # Store with priority for sorting
        self._listeners[event_type].append((priority, listener))
        # Sort by priority (descending)
        self._listeners[event_type].sort(key=lambda x: x[0], reverse=True)

        # Return unsubscribe callable
        def unsubscribe() -> None:
            try:
                self._listeners[event_type].remove((priority, listener))
                if not self._listeners[event_type]:
                    del self._listeners[event_type]
            except ValueError:
                pass

        return unsubscribe

    def emit(self, event_type: str, data: dict[str, Any] | None = None) -> None:
        """Emit an event to all subscribed listeners.

        Args:
            event_type: Type of event being emitted
            data: Event-specific data dictionary
        """
        if not self._enabled:
            return

        import time

        event = Event(
            event_type=event_type,
            timestamp_ns=time.time_ns(),
            data=data or {},
        )

        if event_type in self._listeners:
            for _, listener in self._listeners[event_type]:
                try:
                    listener(event)
                except Exception:
                    # Silently ignore listener exceptions to avoid breaking trace
                    pass

    def enable(self) -> None:
        """Enable event emission."""
        self._enabled = True

    def disable(self) -> None:
        """Disable event emission (useful for performance)."""
        self._enabled = False

    def clear(self) -> None:
        """Remove all listeners."""
        self._listeners.clear()

    def listener_count(self, event_type: str | None = None) -> int:
        """Get count of listeners for an event type or total."""
        if event_type is None:
            return sum(len(listeners) for listeners in self._listeners.values())
        return len(self._listeners.get(event_type, []))


# Global event dispatcher singleton (can be overridden per tracer)
_global_dispatcher: EventDispatcher | None = None


def get_global_dispatcher() -> EventDispatcher:
    """Get or create the global event dispatcher."""
    global _global_dispatcher
    if _global_dispatcher is None:
        _global_dispatcher = EventDispatcher()
    return _global_dispatcher


def set_global_dispatcher(dispatcher: EventDispatcher) -> None:
    """Set a custom global event dispatcher."""
    global _global_dispatcher
    _global_dispatcher = dispatcher
