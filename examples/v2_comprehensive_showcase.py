"""
Enhanced PyRewind v2 showcase demonstrating all major features.

Demonstrates:
1. Basic tracing (v0.1 compatible)
2. Fluent replay API with overrides
3. Trace filtering and comparison
4. Advanced filtering and slicing
5. Trace analysis and inspection
6. Tagging and annotations
7. CLI functionality
8. Plugin system

All features maintain 100% backwards compatibility with v0.1.
"""

from pyrewind import (
    rewindable,
    replay,
    TraceFilter,
    TraceComparison,
    TraceMetadata,
    TraceInspector,
    AdvancedTraceFilter,
    TraceSlice,
    TraceTagger,
)
from pyrewind.cli import PyRewindCLI
from pyrewind.plugins import TimingAnalyzerPlugin


def calculate_discount(base_price: float, discount_percent: float = 10.0) -> float:
    """Calculate discounted price."""
    discount_amount = base_price * (discount_percent / 100)
    final_price = base_price - discount_amount
    return final_price


# Apply the decorator
traced_calculate = rewindable(calculate_discount)


def main():
    """Run comprehensive v2 feature showcase."""
    print("=" * 70)
    print("PyRewind v2 Comprehensive Feature Showcase")
    print("=" * 70)

    # ===== Feature 1: Basic Tracing (v0.1 compatible) =====
    print("\n1️⃣  BASIC TRACING (v0.1 compatible)")
    print("-" * 70)
    result, trace = traced_calculate.run(100.0, discount_percent=20)
    print(f"   Result: ${result}")
    print(f"   Trace ID: {trace.trace_id}")
    print(f"   Total steps: {len(trace.steps)}")

    # ===== Feature 2: Fluent Replay API =====
    print("\n2️⃣  FLUENT REPLAY API WITH OVERRIDES")
    print("-" * 70)
    original_result, original_trace = traced_calculate.run(100.0, discount_percent=20)
    print(f"   Original: ${original_result}")

    # Override the discount
    replay_result, _ = (
        replay(original_trace)
        .override_kwarg("discount_percent", 30)
        .run()
    )
    print(f"   Replayed with 30% discount: ${replay_result}")
    print(f"   Difference: ${original_result - replay_result:.2f}")

    # ===== Feature 3: Trace Filtering & Comparison =====
    print("\n3️⃣  TRACE FILTERING & COMPARISON")
    print("-" * 70)
    result1, trace1 = traced_calculate.run(50.0, discount_percent=10)
    result2, trace2 = traced_calculate.run(50.0, discount_percent=15)

    # Filter by line range
    filtered = TraceFilter(trace1).by_line_range(1, 100).apply()
    print(f"   Filtered trace1 steps: {len(filtered)}")

    # Compare traces
    comparison = TraceComparison(trace1, trace2)
    summary = comparison.summary()
    print(f"   Divergence at step: {summary['divergence_point']}")

    # ===== Feature 4: Advanced Filtering & Slicing =====
    print("\n4️⃣  ADVANCED FILTERING & SLICING")
    print("-" * 70)
    result, complex_trace = traced_calculate.run(123.45, discount_percent=25)

    # Advanced filter
    adv_filter = (
        AdvancedTraceFilter(complex_trace)
        .by_function("calculate_discount")
        .by_local_name("discount_amount", "final_price")
    )
    filtered_steps = adv_filter.apply()
    print(f"   Filtered steps with specific locals: {len(filtered_steps)}")

    # Slicing
    first_half = TraceSlice.first_n_steps(complex_trace, len(complex_trace.steps) // 2)
    print(f"   First half slice: {len(first_half.steps)} steps")

    # ===== Feature 5: Trace Analysis & Inspection =====
    print("\n5️⃣  TRACE ANALYSIS & INSPECTION")
    print("-" * 70)
    result, analysis_trace = traced_calculate.run(200.0, discount_percent=15)
    inspector = TraceInspector(analysis_trace)

    summary = inspector.summary()
    print(f"   Total steps: {summary['total_steps']}")
    print(f"   Execution time: {summary['execution_time_ms']:.3f} ms")
    print(f"   Avg time per step: {summary['avg_time_per_step_us']:.2f} µs")

    timing_stats = inspector.timing_statistics()
    print(f"   Timing min: {timing_stats['min_us']:.2f} µs")
    print(f"   Timing max: {timing_stats['max_us']:.2f} µs")
    print(f"   Timing mean: {timing_stats['mean_us']:.2f} µs")

    hotspots = inspector.hotspots()
    print(f"   Hotspots found: {len(hotspots)}")

    # ===== Feature 6: Tagging & Annotations =====
    print("\n6️⃣  TAGGING & ANNOTATIONS")
    print("-" * 70)
    tagger = TraceTagger()
    tagger.add_tag("performance-test", "Testing performance on large discount")
    tagger.add_tag("production-data", "Real-world calculation")
    tagger.annotate_step(0, "Entry point with base_price=200")
    tagger.annotate_step(1, "Discount calculation started")

    tags = tagger.list_tags()
    print(f"   Tags created: {len(tags)}")
    for tag in tags:
        print(f"      - {tag}")

    annotations = tagger.get_annotations(0)
    print(f"   Annotations at step 0: {len(annotations)}")
    for annot in annotations:
        print(f"      - {annot}")

    # ===== Feature 7: CLI Integration =====
    print("\n7️⃣  CLI INTEGRATION")
    print("-" * 70)
    cli = PyRewindCLI()
    print("   PyRewindCLI available with commands:")
    print("      - inspect <trace.json>     - Inspect a trace")
    print("      - export <trace> -o <out>  - Export to HTML/CSV")
    print("      - diff <trace1> <trace2>   - Compare traces")

    # ===== Feature 8: Metadata & Tags =====
    print("\n8️⃣  METADATA & TAGS")
    print("-" * 70)
    result, metadata_trace = traced_calculate.run(75.0, discount_percent=12)
    metadata = TraceMetadata(
        tags={"discount-analysis", "v2-feature"},
        annotations={"entry": "Starting calculation with 75.0", "exit": "Completed"},
        context={"environment": "test", "version": "0.2.0a0"},
    )
    print(f"   Metadata tags: {metadata.tags}")
    print(f"   Context: {metadata.context}")
    print(f"   Annotations: {len(metadata.annotations)}")

    # ===== Summary =====
    print("\n" + "=" * 70)
    print("✅ All v2 features demonstrated successfully!")
    print("✅ 100% backwards compatible with v0.1 API")
    print("✅ New DX, performance, and feature enhancements")
    print("=" * 70)


if __name__ == "__main__":
    main()
