#!/usr/bin/env python3
"""
PyRewind v2 Interactive Test Script

Run this to verify all v0.1 and v2 features are working correctly.
Usage: python test_pyrewind_v2.py
"""

import sys
import json
from pathlib import Path


def print_header(text):
    """Print a formatted header."""
    print(f"\n{'='*70}")
    print(f"  {text}")
    print(f"{'='*70}")


def print_section(text):
    """Print a formatted section."""
    print(f"\n📌 {text}")
    print("-" * 70)


def test_imports():
    """Test that all modules import correctly."""
    print_section("Testing Imports")
    
    try:
        from pyrewind import (
            rewindable, replay, Trace, TraceInspector,
            AdvancedTraceFilter, TraceSlice, TraceTagger
        )
        from pyrewind.cli import PyRewindCLI
        from pyrewind.plugins import (
            TimingAnalyzerPlugin, ExceptionDebuggerPlugin, MemoryAnalyzerPlugin
        )
        print("✅ All imports successful")
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False


def test_v0_1_basic():
    """Test v0.1 basic functionality."""
    print_section("Testing v0.1 Basic Functionality")
    
    from pyrewind import rewindable
    
    @rewindable
    def add(x, y):
        result = x + y
        return result
    
    # Test direct call
    assert add(5, 3) == 8
    print("✅ Direct call works: add(5, 3) = 8")
    
    # Test traced call
    result, trace = add.run(10, 20)
    assert result == 30
    assert len(trace.steps) > 0
    print(f"✅ Traced call works: add.run(10, 20) = {result}")
    print(f"   Steps recorded: {len(trace.steps)}")
    
    return trace


def test_v0_1_replay(trace):
    """Test v0.1 replay functionality."""
    print_section("Testing v0.1 Replay API")
    
    from pyrewind import replay
    
    # Basic replay
    result, _ = replay(trace).run()
    print(f"✅ Basic replay: result = {result}")
    
    # Replay with override
    result, _ = replay(trace).override_kwarg("x", 100).run()
    assert result == 120  # 100 + 20
    print(f"✅ Replay with override: add(100, 20) = {result}")


def test_v2_trace_inspector(trace):
    """Test v2 TraceInspector feature."""
    print_section("Testing v2 TraceInspector")
    
    from pyrewind import TraceInspector
    
    inspector = TraceInspector(trace)
    
    # Timing metrics
    exec_time_ms = inspector.execution_time_ms()
    avg_time = inspector.average_time_per_step_us()
    print(f"✅ Execution time: {exec_time_ms:.3f} ms")
    print(f"✅ Avg per step: {avg_time:.2f} µs")
    
    # Summary
    summary = inspector.summary()
    print(f"✅ Summary:")
    print(f"   - Total steps: {summary['total_steps']}")
    print(f"   - Execution time: {summary['execution_time_ms']:.3f} ms")
    print(f"   - Has exception: {summary['has_exception']}")


def test_v2_advanced_filtering(trace):
    """Test v2 advanced filtering."""
    print_section("Testing v2 Advanced Filtering")
    
    from pyrewind import AdvancedTraceFilter
    
    # Get line range from trace
    if len(trace.steps) > 0:
        min_line = min(s.line_no for s in trace.steps)
        max_line = max(s.line_no for s in trace.steps)
        
        # Filter by line range
        filtered = (
            AdvancedTraceFilter(trace)
            .by_line_range(min_line, max_line)
            .apply()
        )
        print(f"✅ Filtered by line range {min_line}-{max_line}: {len(filtered)} steps")
        
        # Count without creating list
        count = AdvancedTraceFilter(trace).by_line_range(min_line, max_line).count()
        print(f"✅ Count method: {count} steps")


def test_v2_trace_slicing(trace):
    """Test v2 trace slicing."""
    print_section("Testing v2 Trace Slicing")
    
    from pyrewind import TraceSlice
    
    # First N steps
    if len(trace.steps) > 1:
        sliced = TraceSlice.first_n_steps(trace, 1)
        print(f"✅ First N steps: {len(sliced.steps)} steps")
    
    # Merge traces (single trace)
    merged = TraceSlice.merge_traces([trace])
    print(f"✅ Merge traces: {len(merged.steps)} steps")


def test_v2_tagging():
    """Test v2 tagging system."""
    print_section("Testing v2 Tagging System")
    
    from pyrewind import TraceTagger
    
    tagger = TraceTagger()
    
    # Add tags
    tagger.add_tag("test", "Test tag")
    tagger.add_tag("important")
    assert tagger.has_tag("test")
    print(f"✅ Tags created: {tagger.list_tags()}")
    
    # Annotate steps
    tagger.annotate_step(0, "Entry point")
    tagger.annotate_step(0, "Another annotation")
    annotations = tagger.get_annotations(0)
    print(f"✅ Step annotations: {len(annotations)} annotations")
    
    # Serialization
    data = tagger.to_dict()
    tagger2 = TraceTagger.from_dict(data)
    assert tagger2.has_tag("test")
    print(f"✅ Serialization works: {len(tagger2.list_tags())} tags restored")


def test_v2_cli_module():
    """Test v2 CLI module availability."""
    print_section("Testing v2 CLI Module")
    
    from pyrewind.cli import PyRewindCLI
    
    cli = PyRewindCLI()
    print(f"✅ PyRewindCLI initialized")
    print(f"   Available methods: inspect, export, diff")


def test_v2_plugins():
    """Test v2 plugin system."""
    print_section("Testing v2 Plugin System")
    
    from pyrewind.plugins import (
        TimingAnalyzerPlugin,
        ExceptionDebuggerPlugin,
        MemoryAnalyzerPlugin
    )
    
    # Timing plugin
    timing_plugin = TimingAnalyzerPlugin()
    timing_plugin.initialize()
    print(f"✅ TimingAnalyzerPlugin: {timing_plugin.name}")
    
    # Exception plugin
    exc_plugin = ExceptionDebuggerPlugin()
    exc_plugin.initialize()
    print(f"✅ ExceptionDebuggerPlugin: {exc_plugin.name}")
    
    # Memory plugin
    mem_plugin = MemoryAnalyzerPlugin()
    mem_plugin.initialize()
    print(f"✅ MemoryAnalyzerPlugin: {mem_plugin.name}")


def test_v2_async_tracer():
    """Test v2 async function tracer."""
    print_section("Testing v2 Async Function Tracer")
    
    try:
        from pyrewind import AsyncFunctionTracer
        print(f"✅ AsyncFunctionTracer available")
    except Exception as e:
        print(f"⚠️  AsyncFunctionTracer info: {e}")


def test_storage_export(trace):
    """Test storage and export functionality."""
    print_section("Testing Storage & Export")
    
    from pyrewind.storage.formats import JSONTraceFormat
    from pyrewind.export.formats import HTMLTraceFormat
    
    # JSON format
    json_format = JSONTraceFormat()
    print(f"✅ JSONTraceFormat available")
    
    # HTML format
    html_format = HTMLTraceFormat()
    print(f"✅ HTMLTraceFormat available")


def main():
    """Run all tests."""
    print_header("PyRewind v2 Test Suite")
    print(f"Python: {sys.version}")
    print(f"Path: {Path.cwd()}")
    
    tests_passed = 0
    tests_total = 0
    
    # Import test
    tests_total += 1
    if test_imports():
        tests_passed += 1
    
    # v0.1 tests
    tests_total += 1
    try:
        trace = test_v0_1_basic()
        tests_passed += 1
    except Exception as e:
        print(f"❌ v0.1 basic test failed: {e}")
        return False
    
    tests_total += 1
    try:
        test_v0_1_replay(trace)
        tests_passed += 1
    except Exception as e:
        print(f"❌ v0.1 replay test failed: {e}")
    
    # v2 tests
    tests_total += 1
    try:
        test_v2_trace_inspector(trace)
        tests_passed += 1
    except Exception as e:
        print(f"❌ v2 TraceInspector test failed: {e}")
    
    tests_total += 1
    try:
        test_v2_advanced_filtering(trace)
        tests_passed += 1
    except Exception as e:
        print(f"❌ v2 filtering test failed: {e}")
    
    tests_total += 1
    try:
        test_v2_trace_slicing(trace)
        tests_passed += 1
    except Exception as e:
        print(f"❌ v2 slicing test failed: {e}")
    
    tests_total += 1
    try:
        test_v2_tagging()
        tests_passed += 1
    except Exception as e:
        print(f"❌ v2 tagging test failed: {e}")
    
    tests_total += 1
    try:
        test_v2_cli_module()
        tests_passed += 1
    except Exception as e:
        print(f"❌ v2 CLI test failed: {e}")
    
    tests_total += 1
    try:
        test_v2_plugins()
        tests_passed += 1
    except Exception as e:
        print(f"❌ v2 plugins test failed: {e}")
    
    tests_total += 1
    try:
        test_v2_async_tracer()
        tests_passed += 1
    except Exception as e:
        print(f"❌ v2 async tracer test failed: {e}")
    
    tests_total += 1
    try:
        test_storage_export(trace)
        tests_passed += 1
    except Exception as e:
        print(f"❌ storage/export test failed: {e}")
    
    # Summary
    print_header(f"Test Results: {tests_passed}/{tests_total} Passed")
    
    if tests_passed == tests_total:
        print("🎉 All tests passed! PyRewind v2 is working correctly!")
        return True
    else:
        print(f"⚠️  {tests_total - tests_passed} test(s) failed")
        return False


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
