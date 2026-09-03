"""Automated anomaly detection engine for PyRewind execution traces."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from pyrewind.trace_model import Trace, TraceStep


class AnomalyType(str, Enum):
    """Classification of detected execution anomalies."""

    NONE_TRANSITION = "NONE_TRANSITION"
    NAN_OR_INF = "NAN_OR_INF"
    RUNAWAY_COLLECTION = "RUNAWAY_COLLECTION"
    EXECUTION_SPIKE = "EXECUTION_SPIKE"
    RAPID_MUTATION = "RAPID_MUTATION"
    DEAD_STORE = "DEAD_STORE"


class AnomalySeverity(str, Enum):
    """Severity rating for detected anomalies."""

    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


@dataclass(slots=True)
class Anomaly:
    """A detected anomaly during execution trace inspection."""

    anomaly_type: AnomalyType
    severity: AnomalySeverity
    step_id: int
    line_no: int
    variable_name: Optional[str]
    message: str
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "anomaly_type": self.anomaly_type.value,
            "severity": self.severity.value,
            "step_id": self.step_id,
            "line_no": self.line_no,
            "variable_name": self.variable_name,
            "message": self.message,
            "details": self.details,
        }


class AnomalyDetector:
    """Scans execution traces for algorithmic flaws, memory spikes, and arithmetic corruption."""

    def __init__(
        self,
        collection_growth_threshold: int = 50,
        spike_multiplier_threshold: float = 4.0,
    ) -> None:
        self.collection_growth_threshold = collection_growth_threshold
        self.spike_multiplier_threshold = spike_multiplier_threshold

    def detect_all(self, trace: Trace) -> List[Anomaly]:
        """Run all anomaly detection analyzers on the given trace."""
        anomalies: List[Anomaly] = []

        if not trace.steps:
            return anomalies

        anomalies.extend(self._detect_none_transitions(trace))
        anomalies.extend(self._detect_nan_or_inf(trace))
        anomalies.extend(self._detect_runaway_collections(trace))
        anomalies.extend(self._detect_execution_spikes(trace))
        anomalies.extend(self._detect_rapid_mutations(trace))

        anomalies.sort(key=lambda a: a.step_id)
        return anomalies

    def _detect_none_transitions(self, trace: Trace) -> List[Anomaly]:
        """Detect variables that transition from a valid value to None."""
        anomalies: List[Anomaly] = []
        last_values: Dict[str, Any] = {}

        for step in trace.steps:
            for var_name, val in step.locals_snapshot.items():
                if var_name.startswith("__"):
                    continue

                if var_name in last_values:
                    prev_val = last_values[var_name]
                    if prev_val is not None and val is None:
                        anomalies.append(
                            Anomaly(
                                anomaly_type=AnomalyType.NONE_TRANSITION,
                                severity=AnomalySeverity.WARNING,
                                step_id=step.step_id,
                                line_no=step.line_no,
                                variable_name=var_name,
                                message=f"Variable '{var_name}' transitioned from {type(prev_val).__name__} ({repr(prev_val)[:30]}) to None.",
                                details={"previous_value": repr(prev_val), "new_value": "None"},
                            )
                        )
                last_values[var_name] = val

        return anomalies

    def _detect_nan_or_inf(self, trace: Trace) -> List[Anomaly]:
        """Detect floating-point corruption (NaN or Infinity)."""
        anomalies: List[Anomaly] = []
        flagged_vars: Set[str] = set()

        for step in trace.steps:
            for var_name, val in step.locals_snapshot.items():
                is_nan = False
                is_inf = False

                if isinstance(val, float):
                    if math.isnan(val):
                        is_nan = True
                    elif math.isinf(val):
                        is_inf = True
                elif isinstance(val, dict) and "__repr__" in val:
                    r_text = val["__repr__"].lower()
                    if "nan" in r_text:
                        is_nan = True
                    elif "inf" in r_text:
                        is_inf = True
                elif isinstance(val, str):
                    r_text = val.lower()
                    if r_text == "nan":
                        is_nan = True
                    elif r_text in ("inf", "-inf", "infinity"):
                        is_inf = True

                if is_nan and var_name not in flagged_vars:
                    flagged_vars.add(var_name)
                    anomalies.append(
                        Anomaly(
                            anomaly_type=AnomalyType.NAN_OR_INF,
                            severity=AnomalySeverity.CRITICAL,
                            step_id=step.step_id,
                            line_no=step.line_no,
                            variable_name=var_name,
                            message=f"Variable '{var_name}' evaluated to NaN (Not a Number).",
                            details={"value": "NaN"},
                        )
                    )
                elif is_inf and var_name not in flagged_vars:
                    flagged_vars.add(var_name)
                    anomalies.append(
                        Anomaly(
                            anomaly_type=AnomalyType.NAN_OR_INF,
                            severity=AnomalySeverity.CRITICAL,
                            step_id=step.step_id,
                            line_no=step.line_no,
                            variable_name=var_name,
                            message=f"Variable '{var_name}' overflowed to Infinity.",
                            details={"value": "Inf"},
                        )
                    )

        return anomalies

    def _detect_runaway_collections(self, trace: Trace) -> List[Anomaly]:
        """Detect collections (lists, dicts, sets) that grow rapidly inside loops."""
        anomalies: List[Anomaly] = []
        initial_sizes: Dict[str, int] = {}
        last_sizes: Dict[str, int] = {}
        reported_vars: Set[str] = set()

        for step in trace.steps:
            for var_name, val in step.locals_snapshot.items():
                size = None
                if isinstance(val, (list, dict, set, tuple)):
                    size = len(val)
                elif isinstance(val, dict) and "__repr__" in val and "list" in val.get("__type__", "").lower():
                    # Attempt string list length inference if truncated
                    pass

                if size is not None:
                    if var_name not in initial_sizes:
                        initial_sizes[var_name] = size
                        last_sizes[var_name] = size
                    else:
                        growth = size - initial_sizes[var_name]
                        if growth >= self.collection_growth_threshold and var_name not in reported_vars:
                            reported_vars.add(var_name)
                            anomalies.append(
                                Anomaly(
                                    anomaly_type=AnomalyType.RUNAWAY_COLLECTION,
                                    severity=AnomalySeverity.WARNING,
                                    step_id=step.step_id,
                                    line_no=step.line_no,
                                    variable_name=var_name,
                                    message=f"Collection '{var_name}' grew rapidly to {size} items (+{growth} elements).",
                                    details={"initial_size": initial_sizes[var_name], "current_size": size},
                                )
                            )
                        last_sizes[var_name] = size

        return anomalies

    def _detect_execution_spikes(self, trace: Trace) -> List[Anomaly]:
        """Detect execution steps that take disproportionately long compared to the mean."""
        anomalies: List[Anomaly] = []
        if len(trace.steps) < 3:
            return anomalies

        durations: List[int] = []
        for i in range(len(trace.steps) - 1):
            d = max(0, trace.steps[i + 1].timestamp_ns - trace.steps[i].timestamp_ns)
            durations.append(d)

        if not durations or sum(durations) == 0:
            return anomalies

        mean_duration = sum(durations) / len(durations)
        if mean_duration == 0:
            return anomalies

        for i, d in enumerate(durations):
            if d > mean_duration * self.spike_multiplier_threshold and (d / 1_000_000) > 1.0:
                step = trace.steps[i]
                duration_ms = d / 1_000_000
                anomalies.append(
                    Anomaly(
                        anomaly_type=AnomalyType.EXECUTION_SPIKE,
                        severity=AnomalySeverity.INFO,
                        step_id=step.step_id,
                        line_no=step.line_no,
                        variable_name=None,
                        message=f"Step #{step.step_id} duration ({duration_ms:.2f}ms) is {d / mean_duration:.1f}x slower than average.",
                        details={"duration_ms": duration_ms, "mean_ms": mean_duration / 1_000_000},
                    )
                )

        return anomalies

    def _detect_rapid_mutations(self, trace: Trace) -> List[Anomaly]:
        """Detect variables mutated an unusually high number of times in tight loops."""
        anomalies: List[Anomaly] = []
        mutation_counts: Dict[str, int] = {}
        last_val_repr: Dict[str, str] = {}

        for step in trace.steps:
            for var_name, val in step.locals_snapshot.items():
                v_repr = repr(val)
                if var_name in last_val_repr and last_val_repr[var_name] != v_repr:
                    mutation_counts[var_name] = mutation_counts.get(var_name, 0) + 1
                last_val_repr[var_name] = v_repr

        total_steps = len(trace.steps)
        if total_steps >= 20:
            for var, count in mutation_counts.items():
                if count >= total_steps * 0.7:
                    anomalies.append(
                        Anomaly(
                            anomaly_type=AnomalyType.RAPID_MUTATION,
                            severity=AnomalySeverity.INFO,
                            step_id=0,
                            line_no=trace.steps[0].line_no,
                            variable_name=var,
                            message=f"Variable '{var}' experienced {count} rapid mutations across {total_steps} steps.",
                            details={"mutation_count": count, "total_steps": total_steps},
                        )
                    )

        return anomalies