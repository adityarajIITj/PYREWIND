"""Abstract storage backends for traces.

Supports multiple storage strategies:
- MemoryStorageBackend: In-memory (current v0.1 behavior)
- FileStorageBackend: File-based with streaming
- DatabaseStorageBackend: SQLite for queryable traces
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional
from pathlib import Path
import json


class StorageBackend(ABC):
    """Abstract base class for trace storage implementations."""

    @abstractmethod
    def initialize(self) -> None:
        """Initialize the storage backend."""
        pass

    @abstractmethod
    def store_trace_metadata(self, trace_id: str, metadata: dict[str, Any]) -> None:
        """Store trace metadata."""
        pass

    @abstractmethod
    def store_step(
        self,
        trace_id: str,
        step_id: int,
        step_data: dict[str, Any],
    ) -> None:
        """Store a single trace step."""
        pass

    @abstractmethod
    def store_exception(self, trace_id: str, exception_data: dict[str, Any]) -> None:
        """Store exception information for a trace."""
        pass

    @abstractmethod
    def finalize_trace(self, trace_id: str, result_data: dict[str, Any]) -> None:
        """Finalize and close a trace for writing."""
        pass

    @abstractmethod
    def get_trace(self, trace_id: str) -> dict[str, Any] | None:
        """Retrieve a complete trace."""
        pass

    @abstractmethod
    def get_step(self, trace_id: str, step_id: int) -> dict[str, Any] | None:
        """Retrieve a single step."""
        pass

    @abstractmethod
    def list_traces(self) -> list[str]:
        """List all stored trace IDs."""
        pass

    @abstractmethod
    def delete_trace(self, trace_id: str) -> None:
        """Delete a trace and all its steps."""
        pass

    @abstractmethod
    def shutdown(self) -> None:
        """Shutdown and cleanup the backend."""
        pass


class MemoryStorageBackend(StorageBackend):
    """In-memory storage backend (current v0.1 behavior).

    Stores all traces and steps in RAM. Fast but memory-intensive for large traces.
    """

    def __init__(self) -> None:
        self._traces: dict[str, dict[str, Any]] = {}
        self._steps: dict[str, list[dict[str, Any]]] = {}

    def initialize(self) -> None:
        """Initialize the backend."""
        pass

    def store_trace_metadata(self, trace_id: str, metadata: dict[str, Any]) -> None:
        """Store trace metadata."""
        if trace_id not in self._traces:
            self._traces[trace_id] = {}
        self._traces[trace_id].update(metadata)
        if trace_id not in self._steps:
            self._steps[trace_id] = []

    def store_step(
        self,
        trace_id: str,
        step_id: int,
        step_data: dict[str, Any],
    ) -> None:
        """Store a single trace step."""
        if trace_id not in self._steps:
            self._steps[trace_id] = []

        # Ensure list is large enough
        while len(self._steps[trace_id]) <= step_id:
            self._steps[trace_id].append(None)

        self._steps[trace_id][step_id] = step_data

    def store_exception(self, trace_id: str, exception_data: dict[str, Any]) -> None:
        """Store exception information."""
        if trace_id in self._traces:
            self._traces[trace_id]["exception"] = exception_data

    def finalize_trace(self, trace_id: str, result_data: dict[str, Any]) -> None:
        """Finalize trace."""
        if trace_id in self._traces:
            self._traces[trace_id].update(result_data)
            # Add steps to trace
            self._traces[trace_id]["steps"] = [s for s in self._steps.get(trace_id, []) if s is not None]

    def get_trace(self, trace_id: str) -> dict[str, Any] | None:
        """Retrieve a complete trace."""
        return self._traces.get(trace_id)

    def get_step(self, trace_id: str, step_id: int) -> dict[str, Any] | None:
        """Retrieve a single step."""
        steps = self._steps.get(trace_id, [])
        if step_id < len(steps):
            return steps[step_id]
        return None

    def list_traces(self) -> list[str]:
        """List all stored trace IDs."""
        return list(self._traces.keys())

    def delete_trace(self, trace_id: str) -> None:
        """Delete a trace."""
        self._traces.pop(trace_id, None)
        self._steps.pop(trace_id, None)

    def shutdown(self) -> None:
        """Shutdown."""
        pass


class FileStorageBackend(StorageBackend):
    """File-based storage backend with streaming writes.

    Stores traces as JSON files with incremental step writing.
    Useful for large traces that don't fit in memory.
    """

    def __init__(self, directory: str | Path) -> None:
        self.directory = Path(directory)
        self._active_traces: dict[str, Any] = {}

    def initialize(self) -> None:
        """Create directory if needed."""
        self.directory.mkdir(parents=True, exist_ok=True)

    def _trace_file(self, trace_id: str) -> Path:
        """Get file path for a trace."""
        return self.directory / f"{trace_id}.pyrewind.json"

    def store_trace_metadata(self, trace_id: str, metadata: dict[str, Any]) -> None:
        """Initialize trace file with metadata."""
        if trace_id not in self._active_traces:
            self._active_traces[trace_id] = {
                **metadata,
                "steps": [],
            }

    def store_step(
        self,
        trace_id: str,
        step_id: int,
        step_data: dict[str, Any],
    ) -> None:
        """Append step to trace."""
        if trace_id in self._active_traces:
            # Pad steps list if needed
            while len(self._active_traces[trace_id]["steps"]) <= step_id:
                self._active_traces[trace_id]["steps"].append(None)
            self._active_traces[trace_id]["steps"][step_id] = step_data

    def store_exception(self, trace_id: str, exception_data: dict[str, Any]) -> None:
        """Store exception."""
        if trace_id in self._active_traces:
            self._active_traces[trace_id]["exception"] = exception_data

    def finalize_trace(self, trace_id: str, result_data: dict[str, Any]) -> None:
        """Write trace to disk and finalize."""
        if trace_id not in self._active_traces:
            return

        trace_data = self._active_traces.pop(trace_id)
        trace_data.update(result_data)
        # Clean up None steps
        trace_data["steps"] = [s for s in trace_data.get("steps", []) if s is not None]

        # Write to file
        trace_file = self._trace_file(trace_id)
        try:
            with open(trace_file, "w") as f:
                json.dump(trace_data, f, indent=2, default=str)
        except Exception as e:
            raise IOError(f"Failed to write trace {trace_id} to {trace_file}: {e}") from e

    def get_trace(self, trace_id: str) -> dict[str, Any] | None:
        """Load trace from disk."""
        trace_file = self._trace_file(trace_id)
        if not trace_file.exists():
            return None

        try:
            with open(trace_file, "r") as f:
                return json.load(f)
        except Exception:
            return None

    def get_step(self, trace_id: str, step_id: int) -> dict[str, Any] | None:
        """Get a single step from a trace."""
        trace = self.get_trace(trace_id)
        if trace is None:
            return None

        steps = trace.get("steps", [])
        if step_id < len(steps):
            return steps[step_id]
        return None

    def list_traces(self) -> list[str]:
        """List trace files in directory."""
        if not self.directory.exists():
            return []

        traces = []
        for file in self.directory.glob("*.pyrewind.json"):
            trace_id = file.stem.replace(".pyrewind", "")
            traces.append(trace_id)
        return traces

    def delete_trace(self, trace_id: str) -> None:
        """Delete trace file."""
        self._active_traces.pop(trace_id, None)
        trace_file = self._trace_file(trace_id)
        if trace_file.exists():
            trace_file.unlink()

    def shutdown(self) -> None:
        """Finalize any remaining traces."""
        # Finalize all active traces
        for trace_id in list(self._active_traces.keys()):
            try:
                self.finalize_trace(trace_id, {})
            except Exception:
                pass
