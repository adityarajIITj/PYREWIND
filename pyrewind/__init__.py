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

# v3 additions: Terminal TUI and Diagnostics Engine
from .diagnostics import (
    Anomaly,
    AnomalyDetector,
    AnomalySeverity,
    AnomalyType,
    RootCauseExplainer,
    RootCauseReport,
    TaintedVariable,
    diagnose_trace,
    format_diagnostic_report,
)
from .tui import TerminalScrubber, launch_tui

__all__ = [
    # v0.1 stable API
    "ReplaySession",
    "StepView",
    "Trace",
    "TraceException",
    "TraceStep",
    "rewindable",
    # v2 fluent replay
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
    # v3 Diagnostics Engine
    "Anomaly",
    "AnomalyDetector",
    "AnomalySeverity",
    "AnomalyType",
    "RootCauseExplainer",
    "RootCauseReport",
    "TaintedVariable",
    "diagnose_trace",
    "format_diagnostic_report",
    # v3 Terminal TUI
    "TerminalScrubber",
    "launch_tui",
]

__version__ = "0.3.0"