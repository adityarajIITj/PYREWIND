from pathlib import Path

from pyrewind import Trace, rewindable


@rewindable
def _add_and_double(left: int, right: int = 1) -> int:
    total = left + right
    return total * 2


def test_direct_call_and_traced_run_return_expected_result() -> None:
    assert _add_and_double(2, 3) == 10

    result, trace = _add_and_double.run(2, right=3)

    assert result == 10
    assert isinstance(trace, Trace)
    assert trace.result == 10
    assert trace.exception is None
    assert isinstance(trace.steps, list)
    assert trace.steps


def test_steps_are_zero_based_ordered_and_exposed_through_step_view() -> None:
    _, trace = _add_and_double.run(2, right=3)

    step_ids = [step.step_id for step in trace.steps]
    assert step_ids == list(range(len(trace.steps)))

    first = trace.at(step_ids[0])
    assert isinstance(first.locals(), dict)
    assert isinstance(first.line_no(), int)
    assert first.line_no() > 0
    assert first.function().endswith("_add_and_double")
    assert Path(first.filename()).name == Path(__file__).name
