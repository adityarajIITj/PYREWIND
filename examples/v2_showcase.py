"""PyRewind v2 Feature Showcase"""

from pyrewind import rewindable, replay, TraceFilter, TraceComparison
from pyrewind.storage import StreamingTraceWriter, JSONTraceFormat
from pyrewind.export import HTMLTraceFormat
from pyrewind.trace_comparison import TraceMetadata
import tempfile
from pathlib import Path


# Example 1: Basic rewindable function
@rewindable
def calculate_discount(price: float, percent: int = 10) -> float:
    """Calculate final price after discount."""
    discount_amount = price * percent / 100
    final_price = price - discount_amount
    return final_price


print("=" * 60)
print("🎯 PyRewind v2 Feature Showcase")
print("=" * 60)

# Example 1: Regular trace
print("\n1️⃣  BASIC TRACE (v0.1 compatible)")
result1, trace1 = calculate_discount.run(100, percent=20)
print(f"   Result: ${result1}")
print(f"   Steps recorded: {len(trace1.steps)}")
print(f"   Module: {trace1.module}")

# Example 2: Fluent replay API (NEW!)
print("\n2️⃣  FLUENT REPLAY API (new v2 feature)")
result2, trace2 = replay(trace1).override_kwarg("percent", 30).run()
print(f"   Original result: ${result1:.2f}")
print(f"   After override (30%): ${result2:.2f}")
print(f"   Difference: ${result1 - result2:.2f}")

# Example 3: Trace filtering (NEW!)
print("\n3️⃣  TRACE FILTERING (new v2 feature)")
trace_filter = TraceFilter(trace1).by_line_range(1, 20)
filtered_steps = trace_filter.apply()
print(f"   Original steps: {len(trace1.steps)}")
print(f"   Filtered steps (lines 1-20): {len(filtered_steps)}")

# Example 4: Trace comparison (NEW!)
print("\n4️⃣  TRACE COMPARISON (new v2 feature)")
comparison = TraceComparison(trace1, trace2)
summary = comparison.summary()
print(f"   Step count diff: {summary['step_count_diff']}")
print(f"   Results same? {summary['result_repr_same']}")
print(f"   Execution time diff (ns): {summary['execution_time_diff_ns']}")

# Example 5: Metadata (NEW!)
print("\n5️⃣  TRACE METADATA (new v2 feature)")
meta = TraceMetadata()
meta.add_tag("discount-calculation")
meta.add_tag("v2-test")
meta.annotate_step(0, "Starting discount calculation")
print(f"   Tags: {meta.tags}")
print(f"   Annotations: {len(meta.annotations)}")

# Example 6: Streaming writer (NEW!)
print("\n6️⃣  STREAMING TRACE WRITER (new v2 feature)")
with tempfile.TemporaryDirectory() as tmpdir:
    trace_file = Path(tmpdir) / "trace.json"
    
    # Create streaming writer
    writer = StreamingTraceWriter(
        trace_file,
        format=JSONTraceFormat(),
        buffer_size=10
    )
    
    # Write trace data
    writer.write_metadata({
        "module": trace1.module,
        "qualname": trace1.qualname,
        "started_at_ns": trace1.started_at_ns,
    })
    
    for step in trace1.steps:
        writer.write_step({
            "step_id": step.step_id,
            "timestamp_ns": step.timestamp_ns,
            "filename": step.filename,
            "function": step.function,
            "line_no": step.line_no,
            "locals_snapshot": step.locals_snapshot,
        })
    
    writer.finalize({
        "ended_at_ns": trace1.ended_at_ns,
        "result_repr": trace1.result_repr,
    })
    writer.close()
    
    # Read back
    loaded_data = trace_file.read_text()
    print(f"   File size: {len(loaded_data)} bytes")
    print(f"   File created: {trace_file.exists()}")

# Example 7: HTML Export (NEW!)
print("\n7️⃣  HTML EXPORT (new v2 feature)")
with tempfile.TemporaryDirectory() as tmpdir:
    html_file = Path(tmpdir) / "trace.html"
    html_format = HTMLTraceFormat()
    
    trace_dict = {
        "qualname": trace1.qualname,
        "steps": [
            {
                "step_id": step.step_id,
                "timestamp_ns": step.timestamp_ns,
                "filename": step.filename,
                "function": step.function,
                "line_no": step.line_no,
                "locals_snapshot": step.locals_snapshot,
            }
            for step in trace1.steps
        ],
        "result_repr": trace1.result_repr,
        "exception": None,
    }
    
    html_data = html_format.serialize(trace_dict)
    html_file.write_bytes(html_data)
    print(f"   HTML file size: {len(html_data)} bytes")
    print(f"   Interactive viewer ready: {html_file.exists()}")

print("\n" + "=" * 60)
print("✅ All v2 features working!")
print("=" * 60)
