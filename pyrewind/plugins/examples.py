"""Example plugins for PyRewind."""

from __future__ import annotations

from typing import Any
from pyrewind.core import Plugin


class TimingAnalyzerPlugin(Plugin):
    """Plugin that tracks timing information during tracing."""

    @property
    def name(self) -> str:
        return "timing_analyzer"

    @property
    def version(self) -> str:
        return "1.0.0"

    def initialize(self, config: dict[str, Any] | None = None) -> None:
        """Initialize timing analyzer."""
        self.step_times: dict[int, int] = {}
        self.slowest_steps: list[tuple[int, int]] = []

    def on_trace_step(
        self, trace_id: str, step_id: int, filename: str, line_no: int, locals_dict: dict[str, Any]
    ) -> None:
        """Record step timing."""
        import time

        self.step_times[step_id] = time.time_ns()

    def on_trace_finished(
        self, trace_id: str, duration_ns: int, exception: Exception | None = None
    ) -> None:
        """Analyze timing data."""
        if len(self.step_times) < 2:
            return

        times = sorted(self.step_times.items())
        deltas = []

        for i in range(1, len(times)):
            step_id, current_time = times[i]
            prev_time = times[i - 1][1]
            delta = current_time - prev_time
            deltas.append((step_id, delta))

        # Find top 5 slowest
        self.slowest_steps = sorted(deltas, key=lambda x: x[1], reverse=True)[:5]

    def shutdown(self) -> None:
        """Cleanup."""
        self.step_times.clear()


class ExceptionDebuggerPlugin(Plugin):
    """Plugin that provides detailed exception debugging."""

    @property
    def name(self) -> str:
        return "exception_debugger"

    @property
    def version(self) -> str:
        return "1.0.0"

    def initialize(self, config: dict[str, Any] | None = None) -> None:
        """Initialize exception debugger."""
        self.exceptions: list[dict[str, Any]] = []
        self.last_locals: dict[str, Any] | None = None

    def on_trace_step(
        self, trace_id: str, step_id: int, filename: str, line_no: int, locals_dict: dict[str, Any]
    ) -> None:
        """Track locals before exception."""
        self.last_locals = dict(locals_dict)

    def on_trace_finished(
        self, trace_id: str, duration_ns: int, exception: Exception | None = None
    ) -> None:
        """Log exception details."""
        if exception is not None:
            self.exceptions.append({
                "trace_id": trace_id,
                "type": type(exception).__name__,
                "message": str(exception),
                "last_locals": self.last_locals,
                "duration_ns": duration_ns,
            })

    def shutdown(self) -> None:
        """Cleanup."""
        self.exceptions.clear()


class MemoryAnalyzerPlugin(Plugin):
    """Plugin that tracks memory-related variables."""

    @property
    def name(self) -> str:
        return "memory_analyzer"

    @property
    def version(self) -> str:
        return "1.0.0"

    def initialize(self, config: dict[str, Any] | None = None) -> None:
        """Initialize memory analyzer."""
        self.variable_sizes: dict[str, int] = {}
        self.step_count = 0

    def on_trace_step(
        self, trace_id: str, step_id: int, filename: str, line_no: int, locals_dict: dict[str, Any]
    ) -> None:
        """Analyze variable sizes."""
        import sys

        self.step_count += 1

        for var_name, value in locals_dict.items():
            try:
                size = sys.getsizeof(value)
                if var_name not in self.variable_sizes or size > self.variable_sizes[var_name]:
                    self.variable_sizes[var_name] = size
            except Exception:
                pass

    def on_trace_finished(
        self, trace_id: str, duration_ns: int, exception: Exception | None = None
    ) -> None:
        """Log memory statistics."""
        total_size = sum(self.variable_sizes.values())
        print(f"Memory stats: {len(self.variable_sizes)} variables, {total_size} bytes total")

    def shutdown(self) -> None:
        """Cleanup."""
        self.variable_sizes.clear()
