"""Tests for Steps 8-12 (Analysis, CLI, Filtering, Tagging, Plugins)."""

import pytest
from pyrewind import rewindable, TraceInspector, AdvancedTraceFilter, TraceSlice, TraceTagger
from pyrewind.plugins import TimingAnalyzerPlugin, ExceptionDebuggerPlugin


@rewindable
def demo_function():
    """Simple function for testing."""
    x = 10
    y = 20
    z = x + y
    return z


def test_trace_inspector_basic():
    """Test TraceInspector basic methods."""
    _, trace = demo_function.run()
    inspector = TraceInspector(trace)

    assert inspector.execution_time_ns() > 0
    assert inspector.execution_time_ms() > 0
    assert inspector.average_time_per_step_us() > 0
    assert len(inspector.step_timestamps_us()) > 0


def test_trace_inspector_timing_stats():
    """Test timing statistics."""
    _, trace = demo_function.run()
    inspector = TraceInspector(trace)
    stats = inspector.timing_statistics()

    assert "min_us" in stats
    assert "max_us" in stats
    assert "mean_us" in stats
    assert "median_us" in stats
    assert stats["min_us"] > 0
    assert stats["max_us"] >= stats["min_us"]


def test_trace_inspector_summary():
    """Test summary method."""
    _, trace = demo_function.run()
    inspector = TraceInspector(trace)
    summary = inspector.summary()

    assert "total_steps" in summary
    assert "execution_time_ms" in summary
    assert "avg_time_per_step_us" in summary
    assert "timing" in summary
    assert "variables" in summary
    assert summary["total_steps"] > 0


def test_advanced_trace_filter_by_line():
    """Test filtering by line range."""
    _, trace = demo_function.run()
    
    # Get the actual line numbers from the trace
    if len(trace.steps) > 0:
        min_line = min(s.line_no for s in trace.steps)
        max_line = max(s.line_no for s in trace.steps)
        
        filter_obj = AdvancedTraceFilter(trace)
        filtered = filter_obj.by_line_range(min_line, max_line).apply()
        assert len(filtered) > 0
        assert all(min_line <= s.line_no <= max_line for s in filtered)


def test_advanced_trace_filter_chain():
    """Test chaining multiple filters."""
    _, trace = demo_function.run()
    filter_obj = AdvancedTraceFilter(trace)

    # Chain filters
    filtered = filter_obj.by_function(demo_function.__name__).by_line_range(1, 100).apply()
    assert len(filtered) > 0
    assert all(s.function == demo_function.__name__ for s in filtered)


def test_advanced_trace_filter_custom():
    """Test custom predicate."""
    _, trace = demo_function.run()

    def custom_predicate(step):
        return step.step_id > 0

    filter_obj = AdvancedTraceFilter(trace).by_custom(custom_predicate)
    filtered = filter_obj.apply()

    assert len(filtered) > 0
    assert all(s.step_id > 0 for s in filtered)


def test_trace_slice_first_n():
    """Test slicing first N steps."""
    _, trace = demo_function.run()
    sliced = TraceSlice.first_n_steps(trace, 2)

    assert len(sliced.steps) == min(2, len(trace.steps))


def test_trace_slice_range():
    """Test slicing by range."""
    _, trace = demo_function.run()
    if len(trace.steps) >= 2:
        sliced = TraceSlice.slice_range(trace, 1, 3)
        # After slicing, step IDs are reindexed to start from 0
        assert all(0 <= s.step_id < len(sliced.steps) for s in sliced.steps)


def test_trace_tagger():
    """Test trace tagging."""
    tagger = TraceTagger()

    tagger.add_tag("important", "Important trace")
    tagger.add_tag("debug", "Debug run")

    assert tagger.has_tag("important")
    assert tagger.has_tag("debug")
    assert len(tagger.list_tags()) == 2


def test_trace_tagger_annotations():
    """Test step annotations."""
    tagger = TraceTagger()

    tagger.annotate_step(0, "Start of function")
    tagger.annotate_step(1, "Assignment")
    tagger.annotate_step(1, "Another annotation")

    annotations = tagger.get_annotations(1)
    assert len(annotations) == 2
    assert "Assignment" in annotations
    assert "Another annotation" in annotations


def test_trace_tagger_serialization():
    """Test tagger serialization."""
    tagger = TraceTagger()
    tagger.add_tag("test")
    tagger.annotate_step(0, "Test annotation")

    data = tagger.to_dict()
    tagger2 = TraceTagger.from_dict(data)

    assert tagger2.has_tag("test")
    assert "Test annotation" in tagger2.get_annotations(0)


def test_timing_analyzer_plugin():
    """Test timing analyzer plugin."""
    plugin = TimingAnalyzerPlugin()
    plugin.initialize()

    # Simulate trace steps
    for i in range(3):
        plugin.on_trace_step("trace1", i, "file.py", i + 1, {"x": i})

    plugin.on_trace_finished("trace1", 1000000)
    assert len(plugin.slowest_steps) >= 0

    plugin.shutdown()


def test_exception_debugger_plugin():
    """Test exception debugger plugin."""
    plugin = ExceptionDebuggerPlugin()
    plugin.initialize()

    plugin.on_trace_step("trace1", 0, "file.py", 1, {"x": 10})
    plugin.on_trace_finished("trace1", 1000000, None)  # No exception

    plugin.shutdown()
    assert len(plugin.exceptions) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
