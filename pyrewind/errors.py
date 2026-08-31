"""Exception hierarchy used by :mod:`pyrewind`.

Keeping library-specific failures under one base class lets callers distinguish
trace/replay failures from exceptions raised by the function being traced.
"""

from __future__ import annotations


class PyRewindError(Exception):
    """Base class for errors raised by pyrewind itself."""


class ReplayResolutionError(PyRewindError):
    """Raised when a callable recorded in a trace can no longer be resolved."""


class SerializationError(PyRewindError):
    """Raised when a trace cannot be serialized or a trace artifact is invalid."""


class UnsupportedTargetError(PyRewindError):
    """Raised when a callable cannot be traced by the v0.1 tracing engine."""

