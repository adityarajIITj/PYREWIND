from pyrewind import rewindable


@rewindable
def _calculate(number: int) -> int:
    total = number + 1
    doubled = total * 2
    return doubled


def test_locals_snapshots_include_values_created_during_execution() -> None:
    _, trace = _calculate.run(10)

    snapshots = [trace.at(step.step_id).locals() for step in trace.steps]

    assert any(snapshot.get("total") == 11 for snapshot in snapshots)
    assert any(snapshot.get("doubled") == 22 for snapshot in snapshots)
