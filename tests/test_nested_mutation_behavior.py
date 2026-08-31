from pyrewind import rewindable


@rewindable
def _mutate_nested_container() -> dict[str, list[str]]:
    state = {"items": []}
    state["items"].append("first")
    state["items"].append("second")
    return state


def test_historical_locals_are_frozen_across_nested_mutations() -> None:
    result, trace = _mutate_nested_container.run()
    snapshots = [trace.at(step.step_id).locals() for step in trace.steps]
    historical_states = [snapshot["state"] for snapshot in snapshots if "state" in snapshot]

    assert {"items": []} in historical_states
    assert {"items": ["first"]} in historical_states
    assert {"items": ["first", "second"]} in historical_states

    # Mutating the returned live object must not rewrite already captured snapshots.
    result["items"].append("after run")
    assert all("after run" not in state["items"] for state in historical_states)
