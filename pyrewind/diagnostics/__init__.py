"""Automated diagnostics, root-cause explanation, and anomaly detection for PyRewind."""

from pyrewind.diagnostics.anomaly import Anomaly, AnomalyDetector, AnomalySeverity, AnomalyType
from pyrewind.diagnostics.explainer import RootCauseExplainer, RootCauseReport, TaintedVariable
from pyrewind.diagnostics.report import diagnose_trace, format_diagnostic_report

__all__ = [
    "Anomaly",
    "AnomalyDetector",
    "AnomalySeverity",
    "AnomalyType",
    "RootCauseExplainer",
    "RootCauseReport",
    "TaintedVariable",
    "diagnose_trace",
    "format_diagnostic_report",
]