"""Asynchronous function tracing support for pyrewind v2."""

from __future__ import annotations

import asyncio
import inspect
import sys
import time
import types
from typing import Any, Callable, TypeVar, cast

from .trace_model import Trace, TraceException, TraceStep
from .compat import freeze_value
from .errors import UnsupportedTargetError

R = TypeVar("R")


class AsyncFunctionTracer:
    """Trace asynchronous functions (async def, coroutines).

    Similar to FunctionTracer but handles async/await semantics properly.
    Traces the entire coroutine lifecycle including awaits.
    """

    def __init__(
        self,
        target_func: Callable[..., Any],
        *,
        max_depth: int = 3,
        capture_exceptions: bool = True,
    ) -> None:
        if not callable(target_func):
            raise UnsupportedTargetError("AsyncFunctionTracer requires a callable target")

        code = getattr(target_func, "__code__", None)
        if not isinstance(code, types.CodeType):
            raise UnsupportedTargetError(
                "AsyncFunctionTracer requires a Python function with a code object"
            )

        if not inspect.iscoroutinefunction(target_func):
            raise UnsupportedTargetError(
                "AsyncFunctionTracer only supports async def functions"
            )

        if isinstance(max_depth, bool) or not isinstance(max_depth, int) or max_depth < 0:
            raise ValueError("max_depth must be a non-negative integer")

        self.target_func = target_func
        self.target_code = code
        self.max_depth = max_depth
        self.capture_exceptions = capture_exceptions

        self.last_trace: Trace | None = None

        # Per-invocation state
        self._active_trace: Trace | None = None
        self._root_frame: types.FrameType | None = None
        self._return_event_seen = False
        self._return_value: Any = None
        self._running = False

    async def run(self, *args: Any, **kwargs: Any) -> tuple[Any, Trace]:
        """Execute the async target and return its result plus a finalized trace.

        If the target raises, the same exception (with its traceback) is
        re-raised. In that path, inspect ``tracer.last_trace`` to access the
        exception metadata and recorded steps.
        """

        if self._running:
            raise RuntimeError("AsyncFunctionTracer instance cannot run re-entrantly")

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

            # Install trace hook for async execution
            previous_trace = sys.gettrace()
            sys.settrace(self._trace_dispatch)
            trace_installed = True

            try:
                result = await self.target_func(*args, **kwargs)
            except BaseException as exc:
                if self.capture_exceptions:
                    trace.exception = self._exception_record(exc)
                raise
            else:
                trace.result_value = result
                trace.result_repr = self._safe_repr(result)
                return result, trace
        finally:
            if trace is not None:
                trace.ended_at_ns = time.time_ns()

            if trace_installed:
                sys.settrace(previous_trace)

            self._active_trace = None
            self._root_frame = None
            self._running = False

    def _new_trace(
        self, args: tuple[Any, ...], kwargs: dict[str, Any]
    ) -> Trace:
        """Create a new trace object with metadata."""
        trace = Trace(
            module=getattr(self.target_func, "__module__", ""),
            qualname=getattr(self.target_func, "__qualname__", ""),
            args_repr=[self._safe_repr(a) for a in args],
            kwargs_repr={k: self._safe_repr(v) for k, v in kwargs.items()},
        )
        return trace

    def _trace_dispatch(
        self,
        frame: types.FrameType,
        event: str,
        arg: Any,
    ) -> Callable[[types.FrameType, str, Any], Any] | None:
        """Trace dispatch hook for sys.settrace."""

        if self._active_trace is None:
            return None

        if frame.f_code is not self.target_code:
            return None

        if event == "line":
            if self._root_frame is None:
                self._root_frame = frame

            trace = self._active_trace
            step_id = len(trace.steps)

            locals_snapshot = freeze_value(dict(frame.f_locals), max_depth=self.max_depth)

            step = TraceStep(
                step_id=step_id,
                timestamp_ns=time.time_ns(),
                filename=frame.f_code.co_filename,
                function=frame.f_code.co_name,
                line_no=frame.f_lineno,
                locals_snapshot=locals_snapshot,
            )
            trace.steps.append(step)

        elif event == "return":
            self._return_event_seen = True
            self._return_value = arg

        elif event == "exception":
            pass  # Handled at boundary

        return self._trace_dispatch

    def _safe_repr(self, obj: Any) -> str:
        """Get safe string representation of an object."""
        try:
            return repr(obj)
        except Exception:
            return f"<{type(obj).__name__} object>"

    def _exception_record(self, exc: BaseException) -> TraceException:
        """Create an exception record."""
        return TraceException(
            type_name=type(exc).__name__,
            message=str(exc),
            repr_text=repr(exc),
        )
