"""Unit tests for the automated root-cause diagnostics and anomaly engine."""

import math
import pytest
from pyrewind import rewindable
from pyrewind.diagnostics import (
    AnomalyDetector,
    AnomalyType,
    AnomalySeverity,
    RootCauseExplainer,
    diagnose_trace,
)


def test_zero_division_root_cause_explanation():
    """Test that RootCauseExplainer pinpoints the exact assignment of 0 causing division error."""
    @rewindable
    def divide_pipeline(x, offset):
        base = x + 10
        divisor = offset - 5  # When offset == 5, divisor is 0
        result = base / divisor
        return result

    try:
        divide_pipeline.run(10, 5)
    except ZeroDivisionError:
        pass

    trace = divide_pipeline.last_trace
    assert trace.exception is not None

    explainer = RootCauseExplainer()
    report = explainer.explain(trace)

    assert report.has_failure is True
    assert report.failure_type == "ZeroDivisionError"
    assert len(report.tainted_variables) >= 1
    assert report.tainted_variables[0].name == "divisor"
    assert "ZeroDivisionError occurred" in report.explanation
    assert "divisor" in report.explanation


def test_none_transition_anomaly_detection():
    """Test that AnomalyDetector flags unexpected transition from integer to None."""
    @rewindable
    def process_data(flag):
        config = 42
        if flag:
            config = None
        return config

    process_data.run(True)
    trace = process_data.last_trace

    detector = AnomalyDetector()
    anomalies = detector.detect_all(trace)

    none_anomalies = [a for a in anomalies if a.anomaly_type == AnomalyType.NONE_TRANSITION]
    assert len(none_anomalies) == 1
    assert none_anomalies[0].variable_name == "config"
    assert none_anomalies[0].severity == AnomalySeverity.WARNING


def test_nan_floating_point_anomaly_detection():
    """Test that AnomalyDetector identifies NaN values."""
    @rewindable
    def compute_math():
        val = float("nan")
        multiplier = 2.0
        out = val * multiplier
        return out

    compute_math.run()
    trace = compute_math.last_trace

    detector = AnomalyDetector()
    anomalies = detector.detect_all(trace)

    nan_anomalies = [a for a in anomalies if a.anomaly_type == AnomalyType.NAN_OR_INF]
    assert len(nan_anomalies) >= 1
    assert nan_anomalies[0].severity == AnomalySeverity.CRITICAL


def test_runaway_collection_growth_detection():
    """Test that AnomalyDetector identifies rapid collection expansion in loops."""
    @rewindable
    def expand_collection():
        buffer = []
        for i in range(60):
            buffer.append(i * 2)
        return len(buffer)

    expand_collection.run()
    trace = expand_collection.last_trace

    detector = AnomalyDetector(collection_growth_threshold=40)
    anomalies = detector.detect_all(trace)

    growth_anomalies = [a for a in anomalies if a.anomaly_type == AnomalyType.RUNAWAY_COLLECTION]
    assert len(growth_anomalies) >= 1
    assert growth_anomalies[0].variable_name == "buffer"


def test_diagnose_trace_report_formatter():
    """Test that diagnose_trace outputs a well-formatted string report."""
    @rewindable
    def healthy_func(a, b):
        c = a + b
        return c * 2

    healthy_func.run(3, 4)
    trace = healthy_func.last_trace

    report_text = diagnose_trace(trace)
    assert "PyRewind Automated Diagnostic Report" in report_text
    assert "healthy_func" in report_text
    assert "EXECUTION HEALTH: NORMAL" in report_text