"""Automated root-cause diagnostic explainer for PyRewind execution traces."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from pyrewind.trace_model import Trace, TraceStep


@dataclass(slots=True)
class TaintedVariable:
    """Represents a variable identified as contributing to a crash or anomaly."""

    name: str
    introduced_step: int
    introduced_line: int
    final_value_repr: str
    reason: str


@dataclass(slots=True)
class RootCauseReport:
    """Comprehensive root-cause diagnosis for an execution trace."""

    has_failure: bool
    failure_type: Optional[str]
    failure_message: Optional[str]
    failure_step_id: Optional[int]
    failure_line_no: Optional[int]
    root_cause_step_id: Optional[int]
    root_cause_line_no: Optional[int]
    tainted_variables: List[TaintedVariable] = field(default_factory=list)
    explanation: str = ""
    remediation_suggestion: str = ""
    critical_path_steps: List[int] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "has_failure": self.has_failure,
            "failure_type": self.failure_type,
            "failure_message": self.failure_message,
            "failure_step_id": self.failure_step_id,
            "failure_line_no": self.failure_line_no,
            "root_cause_step_id": self.root_cause_step_id,
            "root_cause_line_no": self.root_cause_line_no,
            "tainted_variables": [
                {
                    "name": tv.name,
                    "introduced_step": tv.introduced_step,
                    "introduced_line": tv.introduced_line,
                    "final_value_repr": tv.final_value_repr,
                    "reason": tv.reason,
                }
                for tv in self.tainted_variables
            ],
            "explanation": self.explanation,
            "remediation_suggestion": self.remediation_suggestion,
            "critical_path_steps": self.critical_path_steps,
        }


class RootCauseExplainer:
    """Traces backward data-flow dependencies from a crash or anomalous return to find root causes."""

    def explain(self, trace: Trace, target_variable: Optional[str] = None) -> RootCauseReport:
        """Analyze a trace and produce a root cause diagnosis report."""
        if not trace.steps:
            return RootCauseReport(
                has_failure=False,
                failure_type=None,
                failure_message=None,
                failure_step_id=None,
                failure_line_no=None,
                root_cause_step_id=None,
                root_cause_line_no=None,
                explanation="Trace contains no recorded execution steps.",
            )

        if trace.exception:
            return self._explain_exception(trace)

        if target_variable:
            return self._explain_variable(trace, target_variable)

        return self._explain_successful_trace(trace)

    def _explain_exception(self, trace: Trace) -> RootCauseReport:
        """Perform backward dependency analysis on an exception trace."""
        assert trace.exception is not None
        exc = trace.exception
        last_step = trace.steps[-1]
        failure_step_id = last_step.step_id
        failure_line_no = last_step.line_no

        tainted_vars: List[TaintedVariable] = []
        root_cause_step = failure_step_id
        root_cause_line = failure_line_no
        explanation = ""
        suggestion = ""
        critical_path: List[int] = [failure_step_id]

        locals_at_crash = last_step.locals_snapshot

        if "ZeroDivision" in exc.type_name:
            # Find variable(s) with value 0 or 0.0 at the crash point
            zero_vars = [k for k, v in locals_at_crash.items() if v == 0 or v == 0.0]
            if zero_vars:
                target_var = zero_vars[0]
                intro_step, intro_line = self._find_where_value_assigned(trace, target_var, 0)
                tainted_vars.append(
                    TaintedVariable(
                        name=target_var,
                        introduced_step=intro_step,
                        introduced_line=intro_line,
                        final_value_repr=repr(locals_at_crash[target_var]),
                        reason=f"Assigned 0/0.0 at Step #{intro_step} (line {intro_line}), subsequently used as divisor.",
                    )
                )
                root_cause_step = intro_step
                root_cause_line = intro_line
                critical_path.insert(0, intro_step)
                explanation = (
                    f"ZeroDivisionError occurred at line {failure_line_no} because variable '{target_var}' was evaluated as 0. "
                    f"Variable '{target_var}' was assigned 0 at Step #{intro_step} (line {intro_line})."
                )
                suggestion = f"Add a defensive check: 'if {target_var} == 0: ...' or check the assignment logic at line {intro_line}."
            else:
                explanation = f"ZeroDivisionError occurred at line {failure_line_no} from literal division by zero."
                suggestion = "Inspect arithmetic expressions on the failure line for direct division by 0."

        elif "TypeError" in exc.type_name:
            # Look for None values or mismatched types
            none_vars = [k for k, v in locals_at_crash.items() if v is None]
            if none_vars:
                target_var = none_vars[0]
                intro_step, intro_line = self._find_where_none_assigned(trace, target_var)
                tainted_vars.append(
                    TaintedVariable(
                        name=target_var,
                        introduced_step=intro_step,
                        introduced_line=intro_line,
                        final_value_repr="None",
                        reason=f"Variable '{target_var}' became None at Step #{intro_step} (line {intro_line}).",
                    )
                )
                root_cause_step = intro_step
                root_cause_line = intro_line
                critical_path.insert(0, intro_step)
                explanation = (
                    f"TypeError triggered at line {failure_line_no} due to unexpected NoneType operand on variable '{target_var}'. "
                    f"Variable '{target_var}' received None at Step #{intro_step} (line {intro_line})."
                )
                suggestion = f"Check return value or assignment for '{target_var}' at line {intro_line} before performing operations on it."
            else:
                explanation = f"TypeError occurred at line {failure_line_no}: {exc.message}"
                suggestion = "Ensure operands have compatible types for the invoked operator or function call."

        elif "IndexError" in exc.type_name:
            explanation = f"IndexError at line {failure_line_no}: sequence subscript out of range ({exc.message})."
            suggestion = f"Verify boundary checks: ensure index is strictly less than collection length."

        elif "KeyError" in exc.type_name:
            explanation = f"KeyError at line {failure_line_no}: key {exc.message} not found in dictionary."
            suggestion = "Use dict.get(key, default) or verify key existence with 'if key in dict:' before lookup."

        else:
            explanation = f"{exc.type_name} raised at line {failure_line_no}: {exc.message}"
            suggestion = f"Inspect variables in scope at failure: {list(locals_at_crash.keys())}"

        return RootCauseReport(
            has_failure=True,
            failure_type=exc.type_name,
            failure_message=exc.message,
            failure_step_id=failure_step_id,
            failure_line_no=failure_line_no,
            root_cause_step_id=root_cause_step,
            root_cause_line_no=root_cause_line,
            tainted_variables=tainted_vars,
            explanation=explanation,
            remediation_suggestion=suggestion,
            critical_path_steps=critical_path,
        )

    def _explain_variable(self, trace: Trace, var_name: str) -> RootCauseReport:
        """Trace the full lifecycle and origins of a specific variable."""
        history: List[Tuple[int, int, Any]] = []
        for step in trace.steps:
            if var_name in step.locals_snapshot:
                history.append((step.step_id, step.line_no, step.locals_snapshot[var_name]))

        if not history:
            return RootCauseReport(
                has_failure=False,
                failure_type=None,
                failure_message=None,
                failure_step_id=None,
                failure_line_no=None,
                root_cause_step_id=None,
                root_cause_line_no=None,
                explanation=f"Variable '{var_name}' was never observed in this trace.",
            )

        first_step, first_line, first_val = history[0]
        last_step, last_line, last_val = history[-1]

        tainted_vars = [
            TaintedVariable(
                name=var_name,
                introduced_step=first_step,
                introduced_line=first_line,
                final_value_repr=repr(last_val),
                reason=f"Introduced at Step #{first_step} (line {first_line}) with initial value {repr(first_val)[:30]}.",
            )
        ]

        critical_path = [h[0] for h in history]

        return RootCauseReport(
            has_failure=False,
            failure_type=None,
            failure_message=None,
            failure_step_id=last_step,
            failure_line_no=last_line,
            root_cause_step_id=first_step,
            root_cause_line_no=first_line,
            tainted_variables=tainted_vars,
            explanation=f"Variable '{var_name}' evolved through {len(history)} observations from {repr(first_val)[:20]} to {repr(last_val)[:20]}.",
            remediation_suggestion="Inspect critical path steps to verify variable state transitions.",
            critical_path_steps=critical_path,
        )

    def _explain_successful_trace(self, trace: Trace) -> RootCauseReport:
        """Summary diagnosis for a successful trace."""
        last_step = trace.steps[-1]
        return RootCauseReport(
            has_failure=False,
            failure_type=None,
            failure_message=None,
            failure_step_id=None,
            failure_line_no=None,
            root_cause_step_id=last_step.step_id,
            root_cause_line_no=last_step.line_no,
            explanation=f"Execution completed normally across {len(trace.steps)} steps with result: {trace.result_repr}.",
            remediation_suggestion="No errors observed. Trace is healthy.",
            critical_path_steps=[s.step_id for s in trace.steps],
        )

    def _find_where_value_assigned(self, trace: Trace, var_name: str, target_val: Any) -> Tuple[int, int]:
        """Find the earliest step where variable was assigned a specific target value."""
        for step in trace.steps:
            if var_name in step.locals_snapshot and step.locals_snapshot[var_name] == target_val:
                return step.step_id, step.line_no
        return trace.steps[0].step_id, trace.steps[0].line_no

    def _find_where_none_assigned(self, trace: Trace, var_name: str) -> Tuple[int, int]:
        """Find the step where a variable became None."""
        for step in trace.steps:
            if var_name in step.locals_snapshot and step.locals_snapshot[var_name] is None:
                return step.step_id, step.line_no
        return trace.steps[0].step_id, trace.steps[0].line_no