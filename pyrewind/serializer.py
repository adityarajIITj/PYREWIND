"""Schema-versioned JSON serialization for pyrewind traces."""

from __future__ import annotations

import json
from collections.abc import Mapping
from copy import deepcopy
from os import PathLike
from pathlib import Path

from .compat import freeze_value
from .errors import SerializationError
from .trace_model import Trace, TraceException, TraceStep

SCHEMA_VERSION = "0.1"
_SERIALIZATION_MAX_DEPTH = 64


def trace_to_dict(trace: Trace) -> dict[str, object]:
    """Convert ``trace`` to the v0.1 JSON artifact payload.

    In-memory result and raw-argument values are deliberately omitted.  Every
    locals value is passed through the safe adapter again so a caller cannot
    accidentally inject a non-JSON value after a trace was captured.
    """

    if not isinstance(trace, Trace):
        raise SerializationError("trace_to_dict expects a Trace instance")

    _validate_trace_header(trace)
    serialized_steps = [_step_to_dict(step, index) for index, step in enumerate(trace.steps)]

    exception_data: dict[str, str] | None
    if trace.exception is None:
        exception_data = None
    else:
        if not isinstance(trace.exception, TraceException):
            raise SerializationError("trace.exception must be a TraceException or None")
        exception_data = {
            "type_name": _require_string(trace.exception.type_name, "exception.type_name"),
            "message": _require_string(trace.exception.message, "exception.message"),
            "repr_text": _require_string(trace.exception.repr_text, "exception.repr_text"),
        }

    payload: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "trace_id": trace.trace_id,
        "python_version": trace.python_version,
        "platform": trace.platform,
        "started_at_ns": trace.started_at_ns,
        "ended_at_ns": trace.ended_at_ns,
        "module": trace.module,
        "qualname": trace.qualname,
        "args_repr": list(trace.args_repr),
        "kwargs_repr": dict(trace.kwargs_repr),
        "steps": serialized_steps,
        "result_repr": trace.result_repr,
        "exception": exception_data,
    }
    _ensure_encodable(payload)
    return payload


def trace_from_dict(data: Mapping[str, object]) -> Trace:
    """Build a :class:`Trace` from a validated v0.1 JSON payload."""

    if not isinstance(data, Mapping):
        raise SerializationError("trace artifact root must be a JSON object")

    schema_version = _require_string(data.get("schema_version"), "schema_version")
    if schema_version != SCHEMA_VERSION:
        raise SerializationError(
            f"unsupported trace schema version {schema_version!r}; expected {SCHEMA_VERSION!r}"
        )

    trace_id = _require_string(data.get("trace_id"), "trace_id")
    python_version = _require_string(data.get("python_version"), "python_version")
    platform = _require_string(data.get("platform"), "platform")
    started_at_ns = _require_int(data.get("started_at_ns"), "started_at_ns", minimum=0)
    ended_at_ns = _optional_int(data.get("ended_at_ns"), "ended_at_ns", minimum=0)
    if ended_at_ns is not None and ended_at_ns < started_at_ns:
        raise SerializationError("ended_at_ns cannot be earlier than started_at_ns")

    module = _require_string(data.get("module"), "module")
    qualname = _require_string(data.get("qualname"), "qualname")
    args_repr = _string_list(data.get("args_repr"), "args_repr")
    kwargs_repr = _string_mapping(data.get("kwargs_repr"), "kwargs_repr")
    steps = _steps_from_data(data.get("steps"))
    result_repr = _optional_string(data.get("result_repr"), "result_repr")
    exception = _exception_from_data(data.get("exception"))

    return Trace(
        trace_id=trace_id,
        python_version=python_version,
        platform=platform,
        started_at_ns=started_at_ns,
        ended_at_ns=ended_at_ns,
        module=module,
        qualname=qualname,
        args_repr=args_repr,
        kwargs_repr=kwargs_repr,
        steps=steps,
        result_repr=result_repr,
        # A persisted trace intentionally cannot recreate these in-memory values.
        result_value=None,
        exception=exception,
        raw_args=None,
        raw_kwargs=None,
    )


def to_file(trace: Trace, path: str | PathLike[str]) -> None:
    """Write ``trace`` to ``path`` as human-readable, strict JSON."""

    payload = trace_to_dict(trace)
    try:
        target = Path(path)
    except TypeError as exc:
        raise SerializationError("path must be a string or path-like value") from exc

    try:
        with target.open("w", encoding="utf-8", newline="\n") as stream:
            json.dump(
                payload,
                stream,
                ensure_ascii=True,
                indent=2,
                sort_keys=True,
                allow_nan=False,
            )
            stream.write("\n")
    except (OSError, TypeError, ValueError) as exc:
        raise SerializationError(f"could not write trace artifact {target!s}: {exc}") from exc


def from_file(path: str | PathLike[str]) -> Trace:
    """Load a schema-versioned trace artifact from ``path``."""

    try:
        source = Path(path)
    except TypeError as exc:
        raise SerializationError("path must be a string or path-like value") from exc

    try:
        with source.open("r", encoding="utf-8") as stream:
            data = json.load(stream)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SerializationError(f"could not read trace artifact {source!s}: {exc}") from exc

    try:
        return trace_from_dict(data)
    except SerializationError:
        raise
    except (TypeError, ValueError) as exc:  # defensive normalization of malformed data
        raise SerializationError(f"invalid trace artifact {source!s}: {exc}") from exc


def _validate_trace_header(trace: Trace) -> None:
    _require_string(trace.trace_id, "trace.trace_id")
    _require_string(trace.python_version, "trace.python_version")
    _require_string(trace.platform, "trace.platform")
    started_at_ns = _require_int(trace.started_at_ns, "trace.started_at_ns", minimum=0)
    ended_at_ns = _optional_int(trace.ended_at_ns, "trace.ended_at_ns", minimum=0)
    if ended_at_ns is not None and ended_at_ns < started_at_ns:
        raise SerializationError("trace.ended_at_ns cannot be earlier than trace.started_at_ns")
    _require_string(trace.module, "trace.module")
    _require_string(trace.qualname, "trace.qualname")
    _string_list(trace.args_repr, "trace.args_repr")
    _string_mapping(trace.kwargs_repr, "trace.kwargs_repr")
    if not isinstance(trace.steps, list):
        raise SerializationError("trace.steps must be a list")
    _optional_string(trace.result_repr, "trace.result_repr")


def _step_to_dict(step: TraceStep, expected_step_id: int) -> dict[str, object]:
    if not isinstance(step, TraceStep):
        raise SerializationError("trace.steps must contain TraceStep instances")
    step_id = _require_int(step.step_id, "step.step_id", minimum=0)
    if step_id != expected_step_id:
        raise SerializationError(
            "trace step ids must be contiguous and zero-based "
            f"(expected {expected_step_id}, got {step_id})"
        )
    timestamp_ns = _require_int(step.timestamp_ns, "step.timestamp_ns", minimum=0)
    filename = _require_string(step.filename, "step.filename")
    function = _require_string(step.function, "step.function")
    line_no = _require_int(step.line_no, "step.line_no", minimum=0)
    if not isinstance(step.locals_snapshot, Mapping):
        raise SerializationError("step.locals_snapshot must be a mapping")
    if not all(isinstance(key, str) for key in step.locals_snapshot):
        raise SerializationError("step.locals_snapshot keys must be strings")

    return {
        "step_id": step_id,
        "timestamp_ns": timestamp_ns,
        "filename": filename,
        "function": function,
        "line_no": line_no,
        "locals_snapshot": freeze_value(
            dict(step.locals_snapshot), max_depth=_SERIALIZATION_MAX_DEPTH
        ),
    }


def _steps_from_data(value: object) -> list[TraceStep]:
    if not isinstance(value, list):
        raise SerializationError("steps must be a list")

    steps: list[TraceStep] = []
    for expected_step_id, raw_step in enumerate(value):
        if not isinstance(raw_step, Mapping):
            raise SerializationError(f"steps[{expected_step_id}] must be an object")
        step_id = _require_int(
            raw_step.get("step_id"), f"steps[{expected_step_id}].step_id", minimum=0
        )
        if step_id != expected_step_id:
            raise SerializationError(
                "trace step ids must be contiguous and zero-based "
                f"(expected {expected_step_id}, got {step_id})"
            )
        timestamp_ns = _require_int(
            raw_step.get("timestamp_ns"), f"steps[{expected_step_id}].timestamp_ns", minimum=0
        )
        filename = _require_string(raw_step.get("filename"), f"steps[{expected_step_id}].filename")
        function = _require_string(raw_step.get("function"), f"steps[{expected_step_id}].function")
        line_no = _require_int(
            raw_step.get("line_no"), f"steps[{expected_step_id}].line_no", minimum=0
        )
        locals_snapshot = raw_step.get("locals_snapshot")
        if not isinstance(locals_snapshot, Mapping):
            raise SerializationError(f"steps[{expected_step_id}].locals_snapshot must be an object")
        if not all(isinstance(key, str) for key in locals_snapshot):
            raise SerializationError(
                f"steps[{expected_step_id}].locals_snapshot keys must be strings"
            )
        _validate_json_value(locals_snapshot, f"steps[{expected_step_id}].locals_snapshot")
        steps.append(
            TraceStep(
                step_id=step_id,
                timestamp_ns=timestamp_ns,
                filename=filename,
                function=function,
                line_no=line_no,
                locals_snapshot=deepcopy(dict(locals_snapshot)),
            )
        )
    return steps


def _exception_from_data(value: object) -> TraceException | None:
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise SerializationError("exception must be an object or null")
    return TraceException(
        type_name=_require_string(value.get("type_name"), "exception.type_name"),
        message=_require_string(value.get("message"), "exception.message"),
        repr_text=_require_string(value.get("repr_text"), "exception.repr_text"),
    )


def _require_string(value: object, name: str) -> str:
    if not isinstance(value, str):
        raise SerializationError(f"{name} must be a string")
    return value


def _optional_string(value: object, name: str) -> str | None:
    if value is None:
        return None
    return _require_string(value, name)


def _require_int(value: object, name: str, *, minimum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise SerializationError(f"{name} must be an integer")
    if minimum is not None and value < minimum:
        raise SerializationError(f"{name} must be greater than or equal to {minimum}")
    return value


def _optional_int(value: object, name: str, *, minimum: int | None = None) -> int | None:
    if value is None:
        return None
    return _require_int(value, name, minimum=minimum)


def _string_list(value: object, name: str) -> list[str]:
    if not isinstance(value, list):
        raise SerializationError(f"{name} must be a list of strings")
    result: list[str] = []
    for index, item in enumerate(value):
        result.append(_require_string(item, f"{name}[{index}]"))
    return result


def _string_mapping(value: object, name: str) -> dict[str, str]:
    if not isinstance(value, Mapping):
        raise SerializationError(f"{name} must be an object mapping strings to strings")
    result: dict[str, str] = {}
    for key, item in value.items():
        if not isinstance(key, str):
            raise SerializationError(f"{name} keys must be strings")
        result[key] = _require_string(item, f"{name}[{key!r}]")
    return result


def _validate_json_value(value: object, name: str, *, depth: int = 0) -> None:
    """Ensure deserialized locals contain only strict JSON-compatible values."""

    if depth > _SERIALIZATION_MAX_DEPTH:
        raise SerializationError(f"{name} exceeds the maximum supported nesting depth")
    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, float):
        if math_isfinite(value):
            return
        raise SerializationError(f"{name} contains a non-finite number")
    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_json_value(item, f"{name}[{index}]", depth=depth + 1)
        return
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str):
                raise SerializationError(f"{name} contains a non-string object key")
            _validate_json_value(item, f"{name}[{key!r}]", depth=depth + 1)
        return
    raise SerializationError(f"{name} contains a non-JSON value of type {type(value).__name__}")


def math_isfinite(value: float) -> bool:
    """Avoid importing a broad dependency just for a strict JSON validation check."""

    # ``float('nan') != float('nan')`` and infinities compare outside finite bounds.
    return value == value and value not in (float("inf"), float("-inf"))


def _ensure_encodable(payload: dict[str, object]) -> None:
    try:
        json.dumps(payload, ensure_ascii=True, allow_nan=False)
    except (TypeError, ValueError, OverflowError) as exc:
        raise SerializationError(f"trace cannot be encoded as strict JSON: {exc}") from exc
