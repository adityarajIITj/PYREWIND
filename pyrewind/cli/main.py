"""Command-line interface for PyRewind."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from pyrewind.analysis import TraceInspector
from pyrewind.export.formats import CSVTraceFormat, HTMLTraceFormat, JSONTraceFormat
from pyrewind.storage.backends import FileStorageBackend
from pyrewind.trace.filter import AdvancedTraceFilter
from pyrewind.trace_model import Trace, TraceException, TraceStep
from pyrewind.diagnostics import diagnose_trace
from pyrewind.tui import TerminalScrubber, launch_tui


class PyRewindCLI:
    """Command-line interface for PyRewind operations."""

    def __init__(self) -> None:
        self.format = JSONTraceFormat()

    def load_trace(self, path: str) -> Trace:
        """Load a trace from file."""
        trace_file = Path(path)
        if not trace_file.exists():
            raise FileNotFoundError(f"Trace file not found: {path}")

        try:
            data = json.loads(trace_file.read_text(encoding="utf-8"))
            steps = []
            for step_data in data.get("steps", []):
                step = TraceStep(
                    step_id=step_data["step_id"],
                    timestamp_ns=step_data["timestamp_ns"],
                    filename=step_data["filename"],
                    function=step_data["function"],
                    line_no=step_data["line_no"],
                    locals_snapshot=step_data.get("locals_snapshot", {}),
                )
                steps.append(step)

            exception = None
            if exc_data := data.get("exception"):
                exception = TraceException(
                    type_name=exc_data["type_name"],
                    message=exc_data["message"],
                    repr_text=exc_data.get("repr_text", ""),
                )

            trace = Trace(
                trace_id=data.get("trace_id", ""),
                module=data.get("module", ""),
                qualname=data.get("qualname", ""),
                python_version=data.get("python_version", ""),
                platform=data.get("platform", ""),
                started_at_ns=data.get("started_at_ns", 0),
                ended_at_ns=data.get("ended_at_ns"),
                args_repr=data.get("args_repr", []),
                kwargs_repr=data.get("kwargs_repr", {}),
                steps=steps,
                result_repr=data.get("result_repr"),
                exception=exception,
            )
            return trace
        except Exception as e:
            raise ValueError(f"Failed to load trace: {e}") from e

    def inspect(self, trace_path: str, verbose: bool = False) -> None:
        """Inspect a trace and print summary."""
        trace = self.load_trace(trace_path)
        inspector = TraceInspector(trace)
        summary = inspector.summary()

        print(f"\n[*] Trace Summary: {trace.qualname}")
        print(f"   Module: {trace.module}")
        print(f"   Total Steps: {summary['total_steps']}")
        print(f"   Execution Time: {summary['execution_time_ms']:.2f} ms")
        print(f"   Avg Time/Step: {summary['avg_time_per_step_us']:.2f} us")
        print(f"   Has Exception: {summary['has_exception']}")

        if verbose:
            print(f"\n[^] Timing Stats:")
            timing = summary["timing"]
            print(f"   Min: {timing['min_us']:.2f} us")
            print(f"   Max: {timing['max_us']:.2f} us")
            print(f"   Mean: {timing['mean_us']:.2f} us")
            print(f"   Median: {timing['median_us']:.2f} us")

            print(f"\n[v] Variables:")
            for var_name, info in summary["variables"].items():
                print(f"   {var_name}: {info['steps_present']} steps")

            print(f"\n[!] Hotspots (slowest steps):")
            hotspots = inspector.hotspots()
            for step_id, time_us in hotspots[:5]:
                print(f"   Step {step_id}: {time_us:.2f} us")

    def diagnose(self, trace_path: str, target_var: Optional[str] = None) -> None:
        """Run automated root-cause diagnosis on a trace."""
        trace = self.load_trace(trace_path)
        report_text = diagnose_trace(trace, target_variable=target_var)
        print(report_text)

    def tui(self, trace_path: str) -> None:
        """Launch interactive Terminal Scrubber TUI."""
        trace = self.load_trace(trace_path)
        launch_tui(trace)

    def export(self, trace_path: str, output_path: str, format: str = "html") -> None:
        """Export trace to a different format."""
        trace = self.load_trace(trace_path)

        if format == "html":
            exporter = HTMLTraceFormat()
        elif format == "csv":
            exporter = CSVTraceFormat()
        elif format == "json":
            exporter = JSONTraceFormat()
        else:
            raise ValueError(f"Unknown format: {format}")

        trace_dict = {
            "trace_id": trace.trace_id,
            "module": trace.module,
            "qualname": trace.qualname,
            "python_version": trace.python_version,
            "platform": trace.platform,
            "result_repr": trace.result_repr,
            "exception": None,
            "steps": [
                {
                    "step_id": s.step_id,
                    "timestamp_ns": s.timestamp_ns,
                    "filename": s.filename,
                    "function": s.function,
                    "line_no": s.line_no,
                    "locals_snapshot": s.locals_snapshot,
                }
                for s in trace.steps
            ],
        }

        if trace.exception:
            trace_dict["exception"] = {
                "type_name": trace.exception.type_name,
                "message": trace.exception.message,
                "repr_text": trace.exception.repr_text,
            }

        try:
            data = exporter.serialize(trace_dict)
            Path(output_path).write_bytes(data)
            print(f"[✓] Exported to {output_path} ({len(data)} bytes)")
        except Exception as e:
            print(f"[!] Export failed: {e}")

    def diff(self, trace1_path: str, trace2_path: str, verbose: bool = False) -> None:
        """Compare two traces."""
        from pyrewind.trace_comparison import TraceComparison

        trace1 = self.load_trace(trace1_path)
        trace2 = self.load_trace(trace2_path)
        comparison = TraceComparison(trace1, trace2)
        summary = comparison.summary()

        print(f"\n[~] Trace Comparison")
        print(f"   Step Count Diff: {summary['step_count_diff']:+d}")
        print(f"   Execution Time Diff: {summary['execution_time_diff_ns']:+.0f} ns")
        print(f"   Results Same: {summary['result_repr_same']}")

        divergence = summary["divergence_point"]
        if divergence is not None:
            print(f"   Divergence at step: {divergence}")

        if summary["exception_diff"][0] != summary["exception_diff"][1]:
            exc1, exc2 = summary["exception_diff"]
            if exc1:
                print(f"   Trace 1 Exception: {exc1.type_name}")
            if exc2:
                print(f"   Trace 2 Exception: {exc2.type_name}")


def main() -> None:
    """Main CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="PyRewind CLI Tool")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # tui command
    tui_parser = subparsers.add_parser("tui", help="Launch interactive Terminal Scrubber TUI")
    tui_parser.add_argument("trace_path", help="Path to trace JSON file")

    # diagnose command
    diag_parser = subparsers.add_parser("diagnose", help="Run automated root-cause diagnosis")
    diag_parser.add_argument("trace_path", help="Path to trace JSON file")
    diag_parser.add_argument("--var", dest="target_var", help="Target variable to diagnose")

    # inspect command
    inspect_parser = subparsers.add_parser("inspect", help="Inspect a trace")
    inspect_parser.add_argument("trace_path", help="Path to trace file")
    inspect_parser.add_argument("-v", "--verbose", action="store_true")

    # export command
    export_parser = subparsers.add_parser("export", help="Export trace to different format")
    export_parser.add_argument("trace_path", help="Path to trace file")
    export_parser.add_argument("-o", "--output", required=True, help="Output file path")
    export_parser.add_argument(
        "-f", "--format", default="html", choices=["html", "csv", "json"]
    )

    # diff command
    diff_parser = subparsers.add_parser("diff", help="Compare two traces")
    diff_parser.add_argument("trace1", help="First trace file")
    diff_parser.add_argument("trace2", help="Second trace file")
    diff_parser.add_argument("-v", "--verbose", action="store_true")

    args = parser.parse_args()

    cli = PyRewindCLI()

    if args.command == "tui":
        cli.tui(args.trace_path)
    elif args.command == "diagnose":
        cli.diagnose(args.trace_path, target_var=args.target_var)
    elif args.command == "inspect":
        cli.inspect(args.trace_path, verbose=args.verbose)
    elif args.command == "export":
        cli.export(args.trace_path, args.output, format=args.format)
    elif args.command == "diff":
        cli.diff(args.trace1, args.trace2, verbose=args.verbose)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()