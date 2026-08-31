"""The low-level execution tracer used by :func:`pyrewind.rewindable`.

``sys.settrace`` is deliberately process-sensitive machinery, so this module
keeps its scope narrow: a :class:`FunctionTracer` traces one synchronous
function invocation in the calling thread and restores the caller's trace
function before returning (or re-raising an exception).
"""

from __future__ import annotations

import inspect
import platform as _platform
import sys
import time
import types
import uuid
from collections.abc import Callable
from typing import Any

from .compat import freeze_value
from .errors import UnsupportedTargetError
from .trace_model import Trace, TraceException, TraceStep


class FunctionTracer:
    """Record the execution of one ordinary Python function.

    Parameters
    ----------
    target_func:
        The function to execute.  Frames are selected by *code-object
        identity*, rather than by a name or filename, so unrelated code is
        never included in the trace.
    max_depth:
        Maximum recursive depth passed to :func:`freeze_value` while copying
        local variables for a step.
    capture_exceptions:
        Whether a final, uncaught exception should be written to the trace.

    ``run`` returns ``(result, trace)`` on success.  It intentionally
    preserves normal Python error behaviour on failure by re-raising the
    original exception; the finalized trace remains available as
    :attr:`last_trace` in that case.
    """

    def __init__(
        self,
        target_func: Callable[..., Any],
        *,
        max_depth: int = 3,
        capture_exceptions: bool = True,
    ) -> None:
        if not callable(target_func):
            raise UnsupportedTargetError("FunctionTracer requires a callable target")

        # A generator/coroutine body runs after the call expression has
        # returned.  Supporting it correctly would require a longer-lived
        # tracing lifecycle, which is intentionally outside the v0.1 scope.
        if (
            inspect.isgeneratorfunction(target_func)
            or inspect.iscoroutinefunction(target_func)
            or inspect.isasyncgenfunction(target_func)
        ):
            raise UnsupportedTargetError(
                "FunctionTracer supports synchronous, non-generator functions only"
            )

        code = getattr(target_func, "__code__", None)
        if not isinstance(code, types.CodeType):
            raise UnsupportedTargetError(
                "FunctionTracer requires a Python function with a code object"
            )
        if isinstance(max_depth, bool) or not isinstance(max_depth, int) or max_depth < 0:
            raise ValueError("max_depth must be a non-negative integer")

        self.target_func = target_func
        self.target_code = code
        self.max_depth = max_depth
        self.capture_exceptions = capture_exceptions

        # Public after each run, including after an exception is re-raised.
        self.last_trace: Trace | None = None

        # Per-invocation state.  A FunctionTracer is reusable sequentially,
        # but deliberately rejects concurrent/re-entrant use of one instance.
        self._active_trace: Trace | None = None
        self._root_frame: types.FrameType | None = None
        self._return_event_seen = False
        self._return_value: Any = None
        self._last_exception_event: tuple[Any, Any, Any] | None = None
        self._running = False

    def run(self, *args: Any, **kwargs: Any) -> tuple[Any, Trace]:
        """Execute the target and return its result plus a finalized trace.

        If the target raises, the same exception (with its traceback) is
        re-raised.  In that path, inspect ``tracer.last_trace`` to access the
        exception metadata and recorded steps.
        """

        if self._running:
            raise RuntimeError("A FunctionTracer instance cannot run re-entrantly")

        self._running = True
        trace: Trace | None = None
        previous_trace: Any = None
        trace_installed = False

        try:
            trace = self._new_trace(args, kwargs)
            self.last_trace = trace
            self._active_trace = trace
            self._root_frame = None
            self._return_event_seen = False
            self._return_value = None
            self._last_exception_event = None

            # sys.settrace is per-thread.  It does not install a trace hook
            # into other currently-running threads or their future children.
            previous_trace = sys.gettrace()
            sys.settrace(self._trace_dispatch)
            trace_installed = True

            try:
                result = self.target_func(*args, **kwargs)
            except BaseException as exc:
                # Trace "exception" events also occur for exceptions that are
                # handled inside the target.  The boundary catch is the only
                # reliable signal that this invocation ultimately failed.
                if self.capture_exceptions:
                    trace.exception = self._exception_record(exc)
                raise
            else:
                # The root return event normally supplies the same object.
                # Use the actual call result as the source of truth in case a
                # target changes its trace hook during execution.
                trace.result_value = result
                trace.result_repr = self._safe_repr(result)
                return result, trace
        finally:
            if trace is not None:
                trace.ended_at_ns = time.time_ns()

            # Restore the exact trace callback that was installed before this
            # invocation, even when target execution failed.
            if trace_installed:
                sys.settrace(previous_trace)

            self._active_trace = None
            self._root_frame = None
            self._running = False

    def _new_trace(self, args: tuple[Any, ...], kwargs: dict[str, Any]) -> Trace:
        """Build an in-memory trace with safe, serialization-ready metadata."""

        module = getattr(self.target_func, "__module__", None) or "__main__"
        qualname = getattr(self.target_func, "__qualname__", None) or self.target_code.co_name
        return Trace(
            trace_id=str(uuid.uuid4()),
            python_version=_platform.python_version(),
            platform=_platform.platform(),
            started_at_ns=time.time_ns(),
            ended_at_ns=None,
            module=module,
            qualname=qualname,
            args_repr=[self._safe_repr(value) for value in args],
            kwargs_repr={str(key): self._safe_repr(value) for key, value in kwargs.items()},
            steps=[],
            result_repr=None,
            result_value=None,
            exception=None,
            # These are intentionally in-memory only.  They enable a same-
            # process assisted replay without pretending that repr strings can
            # be faithfully reconstructed after serialization.
            raw_args=tuple(args),
            raw_kwargs=dict(kwargs),
        )

    def _trace_dispatch(
        self, frame: types.FrameType, event: str, arg: Any
    ) -> Callable[..., Any] | None:
        """Trace callback which ignores every frame except the target code."""

        if frame.f_code is not self.target_code or self._active_trace is None:
            return None

        try:
            if event == "call":
                if self._root_frame is None:
                    self._root_frame = frame
                return self._trace_dispatch

            if event == "line":
                self._record_step(frame)
            elif event == "return":
                # A propagating exception also produces a return event with
                # None.  ``run`` decides whether it was a real completed
                # return before writing result fields to the trace.
                if frame is self._root_frame and not self._return_event_seen:
                    self._return_event_seen = True
                    self._return_value = arg
            elif event == "exception" and frame is self._root_frame:
                # Keep this only as diagnostic state.  It must not become
                # Trace.exception until the invocation boundary observes that
                # the exception escaped the target.
                exception_type, exception_value, traceback = arg
                self._last_exception_event = (
                    exception_type,
                    exception_value,
                    traceback,
                )
        except BaseException:
            # Tracing must never change the target's semantics because a
            # hostile repr/local mapping/freeze operation misbehaved.  The
            # best possible behaviour is to omit that individual observation.
            pass

        return self._trace_dispatch

    def _record_step(self, frame: types.FrameType) -> None:
        trace = self._active_trace
        if trace is None:
            return

        trace.steps.append(
            TraceStep(
                step_id=len(trace.steps),
                timestamp_ns=time.time_ns(),
                filename=frame.f_code.co_filename,
                function=frame.f_code.co_name,
                line_no=frame.f_lineno,
                locals_snapshot=self._freeze_locals(frame),
            )
        )

    def _freeze_locals(self, frame: types.FrameType) -> dict[str, object]:
        """Detach a frame's locals so historical steps cannot later mutate."""

        try:
            copied_locals = dict(frame.f_locals)
        except BaseException:
            return {}

        snapshot: dict[str, object] = {}
        for name, value in copied_locals.items():
            key = str(name)
            try:
                snapshot[key] = freeze_value(value, max_depth=self.max_depth)
            except BaseException:
                snapshot[key] = {
                    "__repr__": self._safe_repr(value),
                    "__type__": type(value).__name__,
                }
        return snapshot

    @classmethod
    def _exception_record(cls, exc: BaseException) -> TraceException:
        return TraceException(
            type_name=type(exc).__name__,
            message=cls._safe_exception_message(exc),
            repr_text=cls._safe_repr(exc),
        )

    @staticmethod
    def _safe_exception_message(exc: BaseException) -> str:
        try:
            return str(exc)
        except BaseException:
            return f"<unprintable {type(exc).__name__}>"

    @staticmethod
    def _safe_repr(value: Any) -> str:
        try:
            return repr(value)
        except BaseException as exc:
            return f"<unrepresentable {type(value).__name__}: {type(exc).__name__}>"

