"""Enhanced fluent replay API for better DX."""

from __future__ import annotations

import importlib
import inspect
from collections.abc import Callable
from typing import Any, cast

from .trace_model import Trace
from .decorator import rewindable
from .errors import ReplayResolutionError


class FluentReplayBuilder:
    """Fluent builder for replaying traces with cleaner API.

    Example:
        result, trace = (replay(old_trace)
            .override_arg("x", 10)
            .override_kwarg("max_depth", 5)
            .timeout(30)
            .run())
    """

    def __init__(self, trace: Trace) -> None:
        self.trace = trace
        self._arg_overrides: dict[int, Any] = {}  # position -> value
        self._kwarg_overrides: dict[str, Any] = {}
        self._timeout_seconds: int | None = None
        self._selected_step: int | None = None

    def override_arg(self, position: int, value: Any) -> FluentReplayBuilder:
        """Override positional argument by index.

        Args:
            position: Zero-based argument position
            value: New value for this argument

        Returns:
            Self for chaining
        """
        self._arg_overrides[position] = value
        return self

    def override_kwarg(self, name: str, value: Any) -> FluentReplayBuilder:
        """Override keyword argument.

        Args:
            name: Argument name
            value: New value for this argument

        Returns:
            Self for chaining
        """
        self._kwarg_overrides[name] = value
        return self

    def override(self, **kwargs: Any) -> FluentReplayBuilder:
        """Override multiple keyword arguments at once.

        Example:
            replay(trace).override(x=10, y=20).run()

        Returns:
            Self for chaining
        """
        self._kwarg_overrides.update(kwargs)
        return self

    def timeout(self, seconds: int) -> FluentReplayBuilder:
        """Set execution timeout.

        Args:
            seconds: Timeout in seconds

        Returns:
            Self for chaining
        """
        self._timeout_seconds = seconds
        return self

    def at_step(self, step_id: int) -> FluentReplayBuilder:
        """Select a checkpoint step for metadata tracking.

        Note: v2.0 records the selection but still re-executes from start.
        Future versions will support partial re-execution from checkpoint.

        Args:
            step_id: Step ID to use as checkpoint

        Returns:
            Self for chaining
        """
        # Validate step exists
        self.trace.at(step_id)
        self._selected_step = step_id
        return self

    def from_step(self, step_id: int) -> FluentReplayBuilder:
        """Alias for at_step() for backwards compatibility."""
        return self.at_step(step_id)

    def run(self, *positional_args: Any, **kwargs: Any) -> tuple[Any, Trace]:
        """Execute the replay and return (result, trace).

        Args:
            *positional_args: If provided, positional arguments override trace args
            **kwargs: Keyword argument overrides (backwards compatible)

        Returns:
            Tuple of (result, new_trace)

        Raises:
            ReplayResolutionError: If function cannot be resolved
            TimeoutError: If execution exceeds timeout
        """
        # Support legacy API: replay(trace).run(quantity=5)
        # Merge kwargs passed to run() with configured overrides
        all_overrides = dict(self._kwarg_overrides)
        all_overrides.update(kwargs)

        target = self._resolve_target()

        # Build call arguments using smart merging
        call_args, call_kwargs = self._build_call(target, positional_args, all_overrides)

        # Get or wrap target with rewindable
        target_any = cast(Any, target)
        runner = getattr(target_any, "run", None)

        if callable(runner):
            # Already rewindable
            return runner(*call_args, **call_kwargs)

        # Wrap with rewindable
        rebound = cast(Any, rewindable(target))
        return rebound.run(*call_args, **call_kwargs)

    def _build_call(
        self,
        target: Callable[..., Any],
        supplied_args: tuple[Any, ...],
        overrides: dict[str, Any],
    ) -> tuple[tuple[Any, ...], dict[str, Any]]:
        """Merge named overrides into a process-local original invocation.

        This implements the same smart merging as the original ReplaySession,
        using inspect.signature to properly handle parameter binding.
        """
        # Explicit positional input always describes a new invocation
        if supplied_args:
            return supplied_args, dict(overrides)

        raw_args = getattr(self.trace, "raw_args", None)
        raw_kwargs = getattr(self.trace, "raw_kwargs", None)

        if raw_args is None or raw_kwargs is None:
            return (), dict(overrides)

        # Get function signature and bind original arguments
        signature = inspect.signature(target)
        try:
            bound = signature.bind_partial(*raw_args, **raw_kwargs)
        except TypeError as exc:
            raise ReplayResolutionError(
                "captured arguments no longer match the resolved function signature"
            ) from exc

        # Apply overrides smartly
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
                # Preserve normal Python's helpful unexpected-keyword error
                return tuple(raw_args), {**dict(raw_kwargs), **overrides}

        return tuple(bound.args), dict(bound.kwargs)

    def _resolve_target(self) -> Callable[..., Any]:
        """Resolve the target function from trace metadata."""
        # Check if trace has live callable
        live_target = getattr(self.trace, "_callable", None)
        if callable(live_target):
            return live_target

        # Try to import from module
        if not self.trace.module:
            raise ReplayResolutionError("trace does not contain a module name")

        try:
            current: Any = importlib.import_module(self.trace.module)
        except Exception as exc:
            raise ReplayResolutionError(
                f"could not import traced module {self.trace.module!r}"
            ) from exc

        # Navigate qualname path
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


def replay(trace: Trace) -> FluentReplayBuilder:
    """Create a fluent replay builder for a trace.

    Example:
        result, new_trace = (replay(old_trace)
            .override_kwarg("count", 100)
            .timeout(30)
            .run())

    Args:
        trace: Trace to replay

    Returns:
        FluentReplayBuilder for chaining
    """
    return FluentReplayBuilder(trace)
