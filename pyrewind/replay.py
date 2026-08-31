"""Assisted rerun support for traces created by :mod:`pyrewind`."""

from __future__ import annotations

import importlib
import inspect
from collections.abc import Callable
from typing import Any, cast

from .decorator import rewindable
from .errors import ReplayResolutionError
from .trace_model import Trace


class ReplaySession:
    """Configure an assisted rerun of a recorded trace.

    ``from_step`` is deliberately metadata-only in v0.1: it records the user's
    selected checkpoint but still re-executes the target from the beginning.
    """

    def __init__(self, trace: Trace) -> None:
        self.trace = trace
        self.selected_step: int | None = None

    def from_step(self, step_id: int) -> ReplaySession:
        """Select a checkpoint for UI/metadata purposes and return this session."""
        if not isinstance(step_id, int):
            raise TypeError("step_id must be an integer")
        # Validate an existing checkpoint early; the selection itself has no
        # execution effect until a future pyrewind version.
        self.trace.at(step_id)
        self.selected_step = step_id
        return self

    def run(self, *args: Any, **arg_overrides: Any) -> tuple[Any, Trace]:
        """Run the target again, optionally patching captured argument values.

        A live trace defaults to its process-local original arguments.  A trace
        loaded from disk has no raw arguments by design, so callers must supply
        a complete invocation (typically keyword arguments) themselves.
        """
        target = self._resolve_target()
        call_args, call_kwargs = self._build_call(target, args, arg_overrides)
        target_any = cast(Any, target)
        runner = getattr(target_any, "run", None)
        if callable(runner):
            return runner(*call_args, **call_kwargs)
        rebound = cast(Any, rewindable(target))
        return rebound.run(*call_args, **call_kwargs)

    def _resolve_target(self) -> Callable[..., Any]:
        live_target = getattr(self.trace, "_callable", None)
        if callable(live_target):
            return live_target

        if not self.trace.module:
            raise ReplayResolutionError("trace does not contain a module name")
        try:
            current: Any = importlib.import_module(self.trace.module)
        except Exception as exc:  # import errors must retain context for users
            raise ReplayResolutionError(
                f"could not import traced module {self.trace.module!r}"
            ) from exc

        for part in self.trace.qualname.split("."):
            if part == "<locals>":
                raise ReplayResolutionError(
                    "cannot resolve a locally defined function from a persisted trace"
                )
            try:
                current = getattr(current, part)
            except AttributeError as exc:
                raise ReplayResolutionError(
                    f"could not resolve {self.trace.qualname!r} in {self.trace.module!r}"
                ) from exc

        if not callable(current):
            raise ReplayResolutionError(
                f"resolved object for {self.trace.qualname!r} is not callable"
            )
        return current

    def _build_call(
        self,
        target: Callable[..., Any],
        supplied_args: tuple[Any, ...],
        overrides: dict[str, Any],
    ) -> tuple[tuple[Any, ...], dict[str, Any]]:
        """Merge named overrides into a process-local original invocation."""
        # Explicit positional input always describes a new invocation.  This is
        # also the escape hatch for positional-only functions in persisted traces.
        if supplied_args:
            return supplied_args, dict(overrides)

        raw_args = getattr(self.trace, "_raw_args", None)
        raw_kwargs = getattr(self.trace, "_raw_kwargs", None)
        if raw_args is None or raw_kwargs is None:
            return (), dict(overrides)

        # `target` can be a decorated wrapper; inspect.signature follows its
        # __wrapped__ chain and exposes the original parameter names.
        signature = inspect.signature(target)
        try:
            bound = signature.bind_partial(*raw_args, **raw_kwargs)
        except TypeError as exc:
            raise ReplayResolutionError(
                "captured arguments no longer match the resolved function signature"
            ) from exc

        parameters = signature.parameters
        keyword_bucket = next(
            (
                parameter.name
                for parameter in parameters.values()
                if parameter.kind is inspect.Parameter.VAR_KEYWORD
            ),
            None,
        )
        for name, value in overrides.items():
            parameter = parameters.get(name)
            if parameter is not None and parameter.kind is not inspect.Parameter.VAR_KEYWORD:
                bound.arguments[name] = value
            elif keyword_bucket is not None:
                extras = dict(bound.arguments.get(keyword_bucket, {}))
                extras[name] = value
                bound.arguments[keyword_bucket] = extras
            else:
                # Preserve normal Python's helpful unexpected-keyword error.
                return tuple(raw_args), {**dict(raw_kwargs), **overrides}
        return tuple(bound.args), dict(bound.kwargs)


def replay(trace: Trace) -> ReplaySession:
    """Return a replay session for ``trace``."""
    if not isinstance(trace, Trace):
        raise TypeError("replay() expects a Trace instance")
    return ReplaySession(trace)
