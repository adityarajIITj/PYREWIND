"""The :func:`rewindable` decorator and its traced execution entry point."""

from __future__ import annotations

import sys
from collections.abc import Callable
from functools import wraps
from pathlib import Path
from typing import Any, ParamSpec, TypeVar, cast

if __package__ in {None, ""}:
    package_root = Path(__file__).resolve().parent.parent
    if str(package_root) not in sys.path:
        sys.path.insert(0, str(package_root))

    from pyrewind.errors import UnsupportedTargetError
    from pyrewind.tracer import FunctionTracer
else:
    from .errors import UnsupportedTargetError
    from .tracer import FunctionTracer

P = ParamSpec("P")
R = TypeVar("R")


def rewindable(
    func: Callable[P, R] | None = None,
    *,
    max_depth: int = 3,
    capture_exceptions: bool = True,
) -> Callable[[Callable[P, R]], Callable[P, R]] | Callable[P, R]:
    """Make a function capable of producing a :class:`~pyrewind.Trace`.

    Ordinary calls retain normal Python behavior.  Calling ``function.run(*args,
    **kwargs)`` executes the underlying function under a trace and returns
    ``(result, trace)``.  If it raises, the original exception is re-raised and
    the finalized trace is available as ``function.last_trace``.

    Args:
        func: Function to decorate, or ``None`` when used with options.
        max_depth: Maximum nested-container depth retained in local snapshots.
        capture_exceptions: Whether uncaught target exceptions are recorded.
    """
    if max_depth < 0:
        raise ValueError("max_depth must be non-negative")

    def decorate(target: Callable[P, R]) -> Callable[P, R]:
        if not callable(target) or not hasattr(target, "__code__"):
            raise UnsupportedTargetError(
                "rewindable only supports Python functions with a code object"
            )

        @wraps(target)
        def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
            return target(*args, **kwargs)

        def run(*args: P.args, **kwargs: P.kwargs) -> tuple[R, Any]:
            tracer = FunctionTracer(
                target,
                max_depth=max_depth,
                capture_exceptions=capture_exceptions,
            )
            try:
                result, trace = tracer.run(*args, **kwargs)
            except BaseException:
                # The tracer finalizes before propagating, so failures remain
                # inspectable without changing ordinary exception semantics.
                failed_trace = tracer.last_trace
                if failed_trace is None:
                    raise RuntimeError("FunctionTracer failed to produce a trace") from None
                _attach_in_memory_call(failed_trace, target, args, kwargs)
                wrapped_any = cast(Any, wrapped)
                wrapped_any.last_trace = failed_trace
                raise
            _attach_in_memory_call(trace, target, args, kwargs)
            wrapped_any = cast(Any, wrapped)
            wrapped_any.last_trace = trace
            return result, trace

        # These attributes deliberately live on the public wrapper.  They are
        # useful to replay a live trace and to inspect a trace after an error.
        wrapped_any = cast(Any, wrapped)
        wrapped_any.run = run
        wrapped_any.last_trace = None
        wrapped_any.__pyrewind_original__ = target
        wrapped_any.__pyrewind_max_depth__ = max_depth
        wrapped_any.__pyrewind_capture_exceptions__ = capture_exceptions
        return cast(Callable[P, R], wrapped_any)

    if func is None:
        return decorate
    return decorate(func)


def _attach_in_memory_call(
    trace: Any,
    target: Callable[..., Any],
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> None:
    """Attach process-local replay information without affecting JSON artifacts."""
    # Kept as private attributes so serialization can remain deterministic and
    # never unexpectedly persist user objects or secrets.
    trace._raw_args = tuple(args)
    trace._raw_kwargs = dict(kwargs)
    trace._callable = target
