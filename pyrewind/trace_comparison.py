"""Enhanced trace model with metadata, filtering, and comparison utilities."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Callable, Optional
from datetime import datetime


@dataclass(slots=True)
class TraceMetadata:
    """Rich metadata for traces."""

    tags: set[str] = field(default_factory=set)
    annotations: dict[int, str] = field(default_factory=dict)  # step_id -> annotation
    context: dict[str, Any] = field(default_factory=dict)  # Custom context (test name, commit, etc)
    created_at: datetime = field(default_factory=datetime.now)
    description: str = ""

    def add_tag(self, tag: str) -> None:
        """Add a tag to the trace."""
        self.tags.add(tag)

    def remove_tag(self, tag: str) -> None:
        """Remove a tag."""
        self.tags.discard(tag)

    def has_tag(self, tag: str) -> bool:
        """Check if trace has a tag."""
        return tag in self.tags

    def annotate_step(self, step_id: int, annotation: str) -> None:
        """Add annotation to a step."""
        self.annotations[step_id] = annotation

    def get_annotation(self, step_id: int) -> str | None:
        """Get annotation for a step."""
        return self.annotations.get(step_id)


class TraceFilter:
    """Fluent builder for filtering trace steps."""

    def __init__(self, trace: Any) -> None:
        self.trace = trace
        self._predicates: list[Callable[[Any], bool]] = []

    def by_line_range(self, start: int, end: int) -> TraceFilter:
        """Filter steps by line number range."""
        self._predicates.append(lambda step: start <= step.line_no <= end)
        return self

    def by_function(self, func_name: str) -> TraceFilter:
        """Filter steps by function name."""
        self._predicates.append(lambda step: step.function == func_name)
        return self

    def by_filename(self, filename: str) -> TraceFilter:
        """Filter steps by filename."""
        self._predicates.append(lambda step: filename in step.filename)
        return self

    def by_local_name(self, var_name: str) -> TraceFilter:
        """Filter steps where a local variable is defined."""
        self._predicates.append(lambda step: var_name in step.locals_snapshot)
        return self

    def by_local_value(self, var_name: str, predicate: Callable[[Any], bool]) -> TraceFilter:
        """Filter steps where a local variable matches a predicate."""
        def check(step: Any) -> bool:
            if var_name not in step.locals_snapshot:
                return False
            return predicate(step.locals_snapshot[var_name])

        self._predicates.append(check)
        return self

    def by_time_range(self, start_ns: int, end_ns: int) -> TraceFilter:
        """Filter steps by timestamp range."""
        self._predicates.append(
            lambda step: start_ns <= step.timestamp_ns <= end_ns
        )
        return self

    def apply(self) -> list[Any]:
        """Apply all filters and return matching steps."""
        filtered = []
        for step in self.trace.steps:
            if all(pred(step) for pred in self._predicates):
                filtered.append(step)
        return filtered

    def apply_to_trace(self) -> Any:
        """Return a new trace with only filtered steps."""
        from .trace_model import Trace, TraceStep

        filtered_steps = self.apply()
        new_trace = deepcopy(self.trace)
        new_trace.steps = filtered_steps
        # Reindex step IDs
        for i, step in enumerate(new_trace.steps):
            step.step_id = i
        return new_trace


class TraceComparison:
    """Compare two traces and identify differences."""

    def __init__(self, trace1: Any, trace2: Any) -> None:
        self.trace1 = trace1
        self.trace2 = trace2

    def step_count_diff(self) -> int:
        """Difference in step counts."""
        return len(self.trace2.steps) - len(self.trace1.steps)

    def execution_time_diff_ns(self) -> int:
        """Difference in execution time (nanoseconds)."""
        time1 = (self.trace1.ended_at_ns or 0) - self.trace1.started_at_ns
        time2 = (self.trace2.ended_at_ns or 0) - self.trace2.started_at_ns
        return time2 - time1

    def result_repr_same(self) -> bool:
        """Check if results are the same."""
        return self.trace1.result_repr == self.trace2.result_repr

    def exception_diff(self) -> tuple[Any, Any]:
        """Return (exc1, exc2) - None if same."""
        exc1 = self.trace1.exception
        exc2 = self.trace2.exception
        if exc1 == exc2:
            return (None, None)
        return (exc1, exc2)

    def divergence_point(self) -> int | None:
        """Find first step where traces diverge in locals.

        Returns step index or None if traces match through both.
        """
        for i in range(min(len(self.trace1.steps), len(self.trace2.steps))):
            step1 = self.trace1.steps[i]
            step2 = self.trace2.steps[i]

            if step1.locals_snapshot != step2.locals_snapshot:
                return i

        # If one is longer, they diverge at the length point
        if len(self.trace1.steps) != len(self.trace2.steps):
            return min(len(self.trace1.steps), len(self.trace2.steps))

        return None

    def variable_changes(self, var_name: str) -> list[dict[str, Any]]:
        """Track how a variable changes differently between traces.

        Returns list of dicts with step_id, trace1_value, trace2_value.
        """
        changes = []
        for i in range(min(len(self.trace1.steps), len(self.trace2.steps))):
            step1 = self.trace1.steps[i]
            step2 = self.trace2.steps[i]

            val1 = step1.locals_snapshot.get(var_name)
            val2 = step2.locals_snapshot.get(var_name)

            if val1 != val2:
                changes.append({
                    "step_id": i,
                    "trace1_value": val1,
                    "trace2_value": val2,
                })

        return changes

    def summary(self) -> dict[str, Any]:
        """Generate a comparison summary."""
        return {
            "step_count_diff": self.step_count_diff(),
            "execution_time_diff_ns": self.execution_time_diff_ns(),
            "result_repr_same": self.result_repr_same(),
            "exception_diff": self.exception_diff(),
            "divergence_point": self.divergence_point(),
        }
