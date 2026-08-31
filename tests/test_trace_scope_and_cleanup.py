import sys

from pyrewind import rewindable


@rewindable
def _only_target_function(value: int) -> int:
    def helper(number: int) -> int:
        return number + 1

    return helper(value) * 2


def test_trace_records_only_the_decorated_function_frame() -> None:
    _, trace = _only_target_function.run(3)

    assert trace.steps
    assert all(
        trace.at(step.step_id).function().endswith("_only_target_function")
        for step in trace.steps
    )


def test_previous_trace_function_is_restored_after_a_run() -> None:
    previous_trace = sys.gettrace()

    _only_target_function.run(3)

    assert sys.gettrace() is previous_trace
