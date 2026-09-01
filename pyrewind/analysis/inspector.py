"""Trace analysis and inspection tools."""

from __future__ import annotations

import statistics
from typing import Any, Optional, Callable
from collections import defaultdict
from pyrewind.trace_model import Trace, TraceStep


class TraceInspector:
    """Query and analyze trace data efficiently.

    Features:
    - Search steps by various criteria
    - Generate execution statistics
    - Analyze variable changes
    - Build call graphs
    """

    def __init__(self, trace: Trace) -> None:
        self.trace = trace

    def steps_at_line(self, line_no: int) -> list[TraceStep]:
        """Get all steps at a specific line number."""
        return [s for s in self.trace.steps if s.line_no == line_no]

    def steps_in_function(self, func_name: str) -> list[TraceStep]:
        """Get all steps in a specific function."""
        return [s for s in self.trace.steps if s.function == func_name]

    def steps_with_local(self, var_name: str) -> list[TraceStep]:
        """Get all steps where a local variable is defined."""
        return [s for s in self.trace.steps if var_name in s.locals_snapshot]

    def steps_where_changed(self, var_name: str) -> list[TraceStep]:
        """Get steps where a variable changed from previous step."""
        changed_steps = []
        prev_value = object()  # Sentinel

        for step in self.trace.steps:
            current_value = step.locals_snapshot.get(var_name, object())
            if current_value != prev_value:
                changed_steps.append(step)
            prev_value = current_value

        return changed_steps

    def execution_time_ns(self) -> int:
        """Total execution time in nanoseconds."""
        if self.trace.ended_at_ns is None:
            return 0
        return self.trace.ended_at_ns - self.trace.started_at_ns

    def execution_time_ms(self) -> float:
        """Total execution time in milliseconds."""
        return self.execution_time_ns() / 1_000_000

    def average_time_per_step_us(self) -> float:
        """Average time per step in microseconds."""
        if not self.trace.steps:
            return 0
        return self.execution_time_ns() / len(self.trace.steps) / 1_000

    def step_timestamps_us(self) -> list[float]:
        """Get all step timestamps relative to start (in microseconds)."""
        if not self.trace.steps:
            return []

        start = self.trace.started_at_ns
        return [(s.timestamp_ns - start) / 1_000 for s in self.trace.steps]

    def time_between_steps_us(self) -> list[float]:
        """Calculate time between consecutive steps (in microseconds)."""
        if len(self.trace.steps) < 2:
            return []

        times = []
        for i in range(1, len(self.trace.steps)):
            delta = (
                self.trace.steps[i].timestamp_ns
                - self.trace.steps[i - 1].timestamp_ns
            ) / 1_000
            times.append(delta)

        return times

    def timing_statistics(self) -> dict[str, float]:
        """Generate timing statistics."""
        times = self.time_between_steps_us()

        if not times:
            return {
                "total_us": 0,
                "min_us": 0,
                "max_us": 0,
                "mean_us": 0,
                "median_us": 0,
            }

        return {
            "total_us": self.execution_time_ns() / 1_000,
            "min_us": min(times),
            "max_us": max(times),
            "mean_us": statistics.mean(times),
            "median_us": statistics.median(times),
            "stdev_us": statistics.stdev(times) if len(times) > 1 else 0,
        }

    def variable_values_at_step(self, var_name: str) -> list[tuple[int, Any]]:
        """Get all values of a variable across steps.

        Returns:
            List of (step_id, value) tuples
        """
        values = []
        for step in self.trace.steps:
            if var_name in step.locals_snapshot:
                values.append((step.step_id, step.locals_snapshot[var_name]))
        return values

    def variable_history(self, var_name: str) -> dict[str, Any]:
        """Get comprehensive history of a variable."""
        values = self.variable_values_at_step(var_name)

        if not values:
            return {"found": False, "values": []}

        return {
            "found": True,
            "values": values,
            "first_step": values[0][0],
            "last_step": values[-1][0],
            "changes": len(values) - 1,
        }

    def local_variables_summary(self) -> dict[str, dict[str, Any]]:
        """Summarize all local variables and their ranges.

        Returns:
            Dict of {var_name: {first_step, last_step, changes}}
        """
        all_vars: dict[str, list[int]] = defaultdict(list)

        for step in self.trace.steps:
            for var_name in step.locals_snapshot.keys():
                all_vars[var_name].append(step.step_id)

        summary = {}
        for var_name, step_ids in all_vars.items():
            summary[var_name] = {
                "first_step": step_ids[0],
                "last_step": step_ids[-1],
                "steps_present": len(step_ids),
            }

        return summary

    def hotspots(self) -> list[tuple[int, float]]:
        """Find steps with longest execution time before next step.

        Returns:
            List of (step_id, time_us) sorted by time descending
        """
        times = self.time_between_steps_us()

        if not times:
            return []

        # Pair step_id with time
        hotspots = [
            (self.trace.steps[i].step_id, times[i])
            for i in range(len(times))
        ]

        # Sort by time descending
        return sorted(hotspots, key=lambda x: x[1], reverse=True)[:10]

    def summary(self) -> dict[str, Any]:
        """Generate comprehensive trace summary."""
        return {
            "total_steps": len(self.trace.steps),
            "execution_time_ms": self.execution_time_ms(),
            "avg_time_per_step_us": self.average_time_per_step_us(),
            "has_exception": self.trace.exception is not None,
            "variables": self.local_variables_summary(),
            "timing": self.timing_statistics(),
        }
