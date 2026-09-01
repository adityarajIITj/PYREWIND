"""Record, inspect, serialize, and assist with replaying Python function executions."""

from .decorator import rewindable
from .replay import ReplaySession, replay as replay_legacy
from .replay_builder import replay, FluentReplayBuilder
from .trace_model import StepView, Trace, TraceException, TraceStep

# v2 additions
from .async_tracer import AsyncFunctionTracer
from .trace_comparison import TraceFilter, TraceComparison, TraceMetadata
from .analysis import TraceInspector
from .trace import AdvancedTraceFilter, TraceSlice
from .metadata import TraceTagger

__all__ = [
    # v0.1 stable API
    "ReplaySession",
    "StepView",
    "Trace",
    "TraceException",
    "TraceStep",
    "rewindable",
    # v2 fluent replay (replaces old replay)
    "replay",
    "FluentReplayBuilder",
    # v2 new API - Core
    "AsyncFunctionTracer",
    "TraceFilter",
    "TraceComparison",
    "TraceMetadata",
    # v2 new API - Analysis
    "TraceInspector",
    "AdvancedTraceFilter",
    "TraceSlice",
    "TraceTagger",
]

__version__ = "0.2.0a0"
