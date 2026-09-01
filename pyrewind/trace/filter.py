"""Advanced filtering and slicing for traces."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable
from pyrewind.trace_model import Trace, TraceStep


class AdvancedTraceFilter:
    """Advanced filtering with chainable predicates."""

    def __init__(self, trace: Trace) -> None:
        self.trace = trace
        self._predicates: list[Callable[[TraceStep], bool]] = []

    def by_line_range(self, start: int, end: int) -> AdvancedTraceFilter:
        """Filter by line number range."""
        self._predicates.append(lambda s: start <= s.line_no <= end)
        return self

    def by_function(self, *names: str) -> AdvancedTraceFilter:
        """Filter by function name (accepts multiple)."""
        self._predicates.append(lambda s: s.function in names)
        return self

    def by_filename(self, *patterns: str) -> AdvancedTraceFilter:
        """Filter by filename patterns."""
        self._predicates.append(lambda s: any(p in s.filename for p in patterns))
        return self

    def by_local_name(self, *var_names: str) -> AdvancedTraceFilter:
        """Filter steps where any of these locals are defined."""
        self._predicates.append(
            lambda s: any(v in s.locals_snapshot for v in var_names)
        )
        return self

    def by_local_value_type(self, var_name: str, type_: type) -> AdvancedTraceFilter:
        """Filter steps where a variable has a specific type."""
        def check(s: TraceStep) -> bool:
            val = s.locals_snapshot.get(var_name)
            return isinstance(val, type_)

        self._predicates.append(check)
        return self

    def by_local_value_match(
        self, var_name: str, predicate: Callable[[Any], bool]
    ) -> AdvancedTraceFilter:
        """Filter steps where a variable matches a custom predicate."""
        def check(s: TraceStep) -> bool:
            if var_name not in s.locals_snapshot:
                return False
            try:
                return predicate(s.locals_snapshot[var_name])
            except Exception:
                return False

        self._predicates.append(check)
        return self

    def by_step_range(self, start_id: int, end_id: int) -> AdvancedTraceFilter:
        """Filter by step ID range."""
        self._predicates.append(lambda s: start_id <= s.step_id <= end_id)
        return self

    def by_time_range(self, start_ns: int, end_ns: int) -> AdvancedTraceFilter:
        """Filter by timestamp range."""
        self._predicates.append(lambda s: start_ns <= s.timestamp_ns <= end_ns)
        return self

    def by_custom(self, predicate: Callable[[TraceStep], bool]) -> AdvancedTraceFilter:
        """Add a custom filter predicate."""
        self._predicates.append(predicate)
        return self

    def apply(self) -> list[TraceStep]:
        """Apply all filters and return matching steps."""
        if not self._predicates:
            return self.trace.steps

        filtered = []
        for step in self.trace.steps:
            if all(pred(step) for pred in self._predicates):
                filtered.append(step)
        return filtered

    def apply_to_trace(self) -> Trace:
        """Return a new trace with only filtered steps."""
        filtered_steps = self.apply()
        new_trace = deepcopy(self.trace)
        new_trace.steps = filtered_steps

        # Reindex step IDs
        for i, step in enumerate(new_trace.steps):
            step.step_id = i

        return new_trace

    def count(self) -> int:
        """Count matching steps without creating a list."""
        return sum(1 for step in self.trace.steps if all(p(step) for p in self._predicates))


class TraceSlice:
    """Slice and combine traces in various ways."""

    @staticmethod
    def first_n_steps(trace: Trace, n: int) -> Trace:
        """Return a trace with only the first N steps."""
        new_trace = deepcopy(trace)
        new_trace.steps = new_trace.steps[:n]
        return new_trace

    @staticmethod
    def last_n_steps(trace: Trace, n: int) -> Trace:
        """Return a trace with only the last N steps."""
        new_trace = deepcopy(trace)
        new_trace.steps = new_trace.steps[-n:]

        # Reindex
        for i, step in enumerate(new_trace.steps):
            step.step_id = i

        return new_trace

    @staticmethod
    def slice_range(trace: Trace, start: int, end: int) -> Trace:
        """Return a trace slice from start to end step IDs."""
        new_trace = deepcopy(trace)
        new_trace.steps = [s for s in new_trace.steps if start <= s.step_id < end]

        # Reindex
        for i, step in enumerate(new_trace.steps):
            step.step_id = i

        return new_trace

    @staticmethod
    def merge_traces(traces: list[Trace]) -> Trace:
        """Merge multiple traces into one.

        Steps are concatenated with reindexed step IDs.
        Metadata from the first trace is preserved.
        """
        if not traces:
            raise ValueError("Cannot merge empty trace list")

        merged = deepcopy(traces[0])
        merged.steps = []

        step_id = 0
        for trace in traces:
            for step in trace.steps:
                new_step = deepcopy(step)
                new_step.step_id = step_id
                merged.steps.append(new_step)
                step_id += 1

        return merged

    @staticmethod
    def sample_steps(trace: Trace, interval: int) -> Trace:
        """Sample every Nth step from a trace.

        Useful for reducing large traces.
        """
        new_trace = deepcopy(trace)
        sampled = [s for i, s in enumerate(new_trace.steps) if i % interval == 0]

        # Reindex
        for i, step in enumerate(sampled):
            step.step_id = i

        new_trace.steps = sampled
        return new_trace
