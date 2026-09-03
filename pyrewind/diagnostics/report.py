"""Diagnostic report formatter for PyRewind traces."""

from __future__ import annotations

from typing import List, Optional
from pyrewind.trace_model import Trace
from pyrewind.diagnostics.anomaly import Anomaly, AnomalyDetector
from pyrewind.diagnostics.explainer import RootCauseExplainer, RootCauseReport


def format_diagnostic_report(
    trace: Trace,
    report: RootCauseReport,
    anomalies: List[Anomaly],
    color: bool = True,
) -> str:
    """Render a human-readable diagnostic report with optional ANSI styling."""
    c_red = "\033[91m" if color else ""
    c_green = "\033[92m" if color else ""
    c_yellow = "\033[93m" if color else ""
    c_cyan = "\033[96m" if color else ""
    c_bold = "\033[1m" if color else ""
    c_dim = "\033[2m" if color else ""
    c_reset = "\033[0m" if color else ""

    lines: List[str] = []
    lines.append(f"{c_bold}{c_cyan}=== PyRewind Automated Diagnostic Report ==={c_reset}")
    lines.append(f"Function: {c_bold}{trace.qualname}{c_reset} ({trace.module})")
    lines.append(f"Total Steps: {len(trace.steps)} | Trace ID: {trace.trace_id[:8]}")
    lines.append("-" * 60)

    # 1. Root Cause Section
    if report.has_failure:
        lines.append(f"\n{c_bold}{c_red}[!] ROOT CAUSE DIAGNOSIS: {report.failure_type}{c_reset}")
        lines.append(f"    Message: {report.failure_message}")
        lines.append(f"    Failure Point: Step #{report.failure_step_id} (line {report.failure_line_no})")
        lines.append(f"    Root Cause Point: Step #{report.root_cause_step_id} (line {report.root_cause_line_no})")
        lines.append(f"\n    {c_bold}Explanation:{c_reset} {report.explanation}")
        lines.append(f"    {c_bold}{c_green}Remediation:{c_reset} {report.remediation_suggestion}")

        if report.tainted_variables:
            lines.append(f"\n    {c_bold}Tainted Variables:{c_reset}")
            for tv in report.tainted_variables:
                lines.append(f"      - {c_bold}{tv.name}{c_reset}: introduced at Step #{tv.introduced_step} (line {tv.introduced_line}) -> {tv.reason}")
    else:
        lines.append(f"\n{c_bold}{c_green}[✓] EXECUTION HEALTH: NORMAL{c_reset}")
        lines.append(f"    Result: {trace.result_repr}")
        lines.append(f"    {report.explanation}")

    # 2. Anomalies Section
    lines.append(f"\n{c_bold}{c_cyan}[*] DETECTED ANOMALIES ({len(anomalies)} found):{c_reset}")
    if anomalies:
        for a in anomalies:
            sev_color = c_red if a.severity.value == "CRITICAL" else (c_yellow if a.severity.value == "WARNING" else c_cyan)
            var_part = f" [{a.variable_name}]" if a.variable_name else ""
            lines.append(f"    {sev_color}[{a.severity.value}]{c_reset} Step #{a.step_id} (line {a.line_no}){var_part}: {a.message}")
    else:
        lines.append(f"    {c_dim}No data-flow or arithmetic anomalies detected.{c_reset}")

    lines.append("\n" + "=" * 60)
    return "\n".join(lines)


def diagnose_trace(trace: Trace, target_variable: Optional[str] = None) -> str:
    """Convenience helper to run full diagnosis and return formatted text report."""
    explainer = RootCauseExplainer()
    detector = AnomalyDetector()

    report = explainer.explain(trace, target_variable=target_variable)
    anomalies = detector.detect_all(trace)

    return format_diagnostic_report(trace, report, anomalies)