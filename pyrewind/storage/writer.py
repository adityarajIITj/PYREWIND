"""Streaming trace writer for efficient handling of large traces."""

from __future__ import annotations

import json
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Optional

from .formats import TraceFormat, JSONTraceFormat


class TraceWriter(ABC):
    """Abstract base for trace writers."""

    @abstractmethod
    def write_metadata(self, metadata: dict[str, Any]) -> None:
        """Write trace metadata."""
        pass

    @abstractmethod
    def write_step(self, step: dict[str, Any]) -> None:
        """Write a single step."""
        pass

    @abstractmethod
    def write_exception(self, exception: dict[str, Any]) -> None:
        """Write exception information."""
        pass

    @abstractmethod
    def finalize(self, result_data: dict[str, Any]) -> None:
        """Finalize the trace."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Close the writer."""
        pass


class StreamingTraceWriter(TraceWriter):
    """Writes trace steps incrementally with buffering and sampling.

    Features:
    - Buffered writes to reduce I/O
    - Optional step sampling for long traces
    - Multiple format support
    - Configurable buffer size
    """

    def __init__(
        self,
        output_path: str | Path,
        format: TraceFormat | None = None,
        buffer_size: int = 100,
        sample_interval: int | None = None,
    ) -> None:
        """Initialize streaming writer.

        Args:
            output_path: Path to write trace file
            format: TraceFormat instance (default: JSONTraceFormat)
            buffer_size: Number of steps to buffer before writing
            sample_interval: Record every Nth step (None = all steps)
        """
        self.output_path = Path(output_path)
        self.format = format or JSONTraceFormat()
        self.buffer_size = buffer_size
        self.sample_interval = sample_interval

        self._metadata: dict[str, Any] = {}
        self._steps: list[dict[str, Any]] = []
        self._exception: dict[str, Any] | None = None
        self._result_data: dict[str, Any] | None = None
        self._step_counter = 0
        self._closed = False

    def write_metadata(self, metadata: dict[str, Any]) -> None:
        """Write trace metadata."""
        if self._closed:
            raise ValueError("Writer is closed")
        self._metadata.update(metadata)

    def write_step(self, step: dict[str, Any]) -> None:
        """Write a single step (buffered)."""
        if self._closed:
            raise ValueError("Writer is closed")

        # Apply sampling if configured
        if self.sample_interval is not None:
            if self._step_counter % self.sample_interval != 0:
                self._step_counter += 1
                return

        self._steps.append(step)
        self._step_counter += 1

        # Flush if buffer is full
        if len(self._steps) >= self.buffer_size:
            self._flush_steps()

    def write_exception(self, exception: dict[str, Any]) -> None:
        """Write exception information."""
        if self._closed:
            raise ValueError("Writer is closed")
        self._exception = exception

    def finalize(self, result_data: dict[str, Any]) -> None:
        """Finalize and flush the trace."""
        if self._closed:
            raise ValueError("Writer is closed")

        self._result_data = result_data

        # Flush remaining steps
        self._flush_steps()

        # Build complete trace
        trace_data: dict[str, Any] = {}
        trace_data.update(self._metadata)

        if self._exception is not None:
            trace_data["exception"] = self._exception

        if self._result_data is not None:
            trace_data.update(self._result_data)

        # Write to file
        try:
            data_bytes = self.format.serialize(trace_data)
            self.output_path.write_bytes(data_bytes)
        except Exception as e:
            raise IOError(f"Failed to write trace: {e}") from e

    def _flush_steps(self) -> None:
        """Flush buffered steps to metadata."""
        if "steps" not in self._metadata:
            self._metadata["steps"] = []
        self._metadata["steps"].extend(self._steps)
        self._steps.clear()

    def close(self) -> None:
        """Close the writer."""
        self._closed = True
        self._steps.clear()


class FileTraceWriter(TraceWriter):
    """Simple non-streaming file writer."""

    def __init__(
        self,
        output_path: str | Path,
        format: TraceFormat | None = None,
    ) -> None:
        self.output_path = Path(output_path)
        self.format = format or JSONTraceFormat()
        self._data: dict[str, Any] = {"steps": []}
        self._closed = False

    def write_metadata(self, metadata: dict[str, Any]) -> None:
        if self._closed:
            raise ValueError("Writer is closed")
        self._data.update(metadata)

    def write_step(self, step: dict[str, Any]) -> None:
        if self._closed:
            raise ValueError("Writer is closed")
        self._data["steps"].append(step)

    def write_exception(self, exception: dict[str, Any]) -> None:
        if self._closed:
            raise ValueError("Writer is closed")
        self._data["exception"] = exception

    def finalize(self, result_data: dict[str, Any]) -> None:
        if self._closed:
            raise ValueError("Writer is closed")
        self._data.update(result_data)

        try:
            data_bytes = self.format.serialize(self._data)
            self.output_path.write_bytes(data_bytes)
        except Exception as e:
            raise IOError(f"Failed to write trace: {e}") from e

    def close(self) -> None:
        self._closed = True
        self._data.clear()
