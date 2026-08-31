"""In-memory data model for a pyrewind execution trace."""

from __future__ import annotations

import platform as _platform
import sys
import time
from copy import deepcopy
from dataclasses import dataclass, field
from typing import ClassVar
from uuid import uuid4


@dataclass(slots=True)
class TraceStep:
    """One source-line observation recorded for the traced function."""

    step_id: int
    timestamp_ns: int
    filename: str
    function: str
    line_no: int
    locals_snapshot: dict[str, object]


@dataclass(slots=True)
class TraceException:
    """Serializable details of an exception observed during execution."""

    type_name: str
    message: str
    repr_text: str


@dataclass(slots=True)
class StepView:
    """Small read-oriented wrapper around a :class:`TraceStep`."""

    _step: TraceStep

    def locals(self) -> dict[str, object]:
        """Return an independent copy of this step's locals snapshot."""

        return deepcopy(self._step.locals_snapshot)

    def line_no(self) -> int:
        """Return the source line recorded for this step."""

        return self._step.line_no

    def function(self) -> str:
        """Return the recorded function name."""

        return self._step.function

    def filename(self) -> str:
        """Return the source filename recorded for this step."""

        return self._step.filename


def _default_python_version() -> str:
    return sys.version


def _default_platform() -> str:
    return _platform.platform()


@dataclass(slots=True)
class Trace:
    """The complete in-memory record of one call to a rewindable function.

    ``result_value``, ``raw_args``, and ``raw_kwargs`` are intentionally
    in-memory conveniences.  They are never included in a JSON trace artifact;
    serialized traces retain only safe representations and replay metadata.
    """

    trace_id: str = field(default_factory=lambda: str(uuid4()))
    python_version: str = field(default_factory=_default_python_version)
    platform: str = field(default_factory=_default_platform)
    started_at_ns: int = field(default_factory=time.time_ns)
    ended_at_ns: int | None = None
    module: str = ""
    qualname: str = ""
    args_repr: list[str] = field(default_factory=list)
    kwargs_repr: dict[str, str] = field(default_factory=dict)
    steps: list[TraceStep] = field(default_factory=list)
    result_repr: str | None = None
    result_value: object | None = field(default=None, repr=False)
    exception: TraceException | None = None
    raw_args: tuple[object, ...] | None = field(default=None, repr=False, compare=False)
    raw_kwargs: dict[str, object] | None = field(default=None, repr=False, compare=False)
    # The decorator/replay pair use these private process-local hooks.  They
    # are declared explicitly because this compact model uses slots; none is
    # serialized.
    _callable: object | None = field(default=None, init=False, repr=False, compare=False)

    SCHEMA_VERSION: ClassVar[str] = "0.1"

    @property
    def result(self) -> object | None:
        """Return the actual result when this trace is still in memory."""

        return self.result_value

    @property
    def _raw_args(self) -> tuple[object, ...] | None:
        """Backward-compatible private alias for process-local replay data."""

        return self.raw_args

    @_raw_args.setter
    def _raw_args(self, value: tuple[object, ...] | None) -> None:
        self.raw_args = value

    @property
    def _raw_kwargs(self) -> dict[str, object] | None:
        """Backward-compatible private alias for process-local replay data."""

        return self.raw_kwargs

    @_raw_kwargs.setter
    def _raw_kwargs(self, value: dict[str, object] | None) -> None:
        self.raw_kwargs = value

    @property
    def metadata(self) -> dict[str, object]:
        """Return a copy of the identifying and runtime metadata fields."""

        return {
            "trace_id": self.trace_id,
            "python_version": self.python_version,
            "platform": self.platform,
            "started_at_ns": self.started_at_ns,
            "ended_at_ns": self.ended_at_ns,
            "module": self.module,
            "qualname": self.qualname,
        }

    def at(self, step: int) -> StepView:
        """Return the view for zero-based ``step`` id.

        Step IDs are intentionally used rather than list offsets so callers do
        not accidentally receive a different step from malformed/filtered data.
        """

        for trace_step in self.steps:
            if trace_step.step_id == step:
                return StepView(trace_step)
        raise IndexError(f"Trace has no step with id {step}")

    def to_file(self, path: str) -> None:
        """Write this trace as a schema-versioned JSON artifact."""

        # Delayed import keeps trace_model <-> serializer free of import cycles.
        from .serializer import to_file

        to_file(self, path)

    @classmethod
    def from_file(cls, path: str) -> Trace:
        """Load a trace artifact written by :meth:`to_file`."""

        # Delayed import keeps trace_model <-> serializer free of import cycles.
        from .serializer import from_file

        trace = from_file(path)
        if not isinstance(trace, cls):  # defensive if a custom serializer is patched in
            raise TypeError("serialized artifact did not produce a Trace")
        return trace
