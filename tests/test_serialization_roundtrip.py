from pyrewind import Trace, rewindable


@rewindable
def _serialize_me(value: int) -> int:
    state = {"value": value}
    return state["value"] + 1


def test_trace_json_round_trip_preserves_diagnostic_data(tmp_path) -> None:
    _, trace = _serialize_me.run(4)
    output_path = tmp_path / "execution.pyrewind.json"

    assert trace.to_file(str(output_path)) is None
    loaded = Trace.from_file(str(output_path))

    assert output_path.is_file()
    assert loaded.trace_id == trace.trace_id
    assert loaded.module == trace.module
    assert loaded.qualname == trace.qualname
    assert loaded.result_repr == trace.result_repr
    assert loaded.exception is None
    assert len(loaded.steps) == len(trace.steps)
    assert [step.step_id for step in loaded.steps] == [
        step.step_id for step in trace.steps
    ]
    assert [loaded.at(step.step_id).line_no() for step in loaded.steps] == [
        trace.at(step.step_id).line_no() for step in trace.steps
    ]
    assert [loaded.at(step.step_id).locals() for step in loaded.steps] == [
        trace.at(step.step_id).locals() for step in trace.steps
    ]
