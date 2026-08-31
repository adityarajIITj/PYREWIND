from pyrewind import replay, rewindable


@rewindable
def replayable_total(quantity: int, unit_price: int = 10) -> int:
    subtotal = quantity * unit_price
    return subtotal + 1


def test_same_process_replay_applies_keyword_overrides() -> None:
    original_result, trace = replayable_total.run(2, unit_price=10)

    replayed_result, replayed_trace = replay(trace).run(quantity=5)

    assert original_result == 21
    assert replayed_result == 51
    assert replayed_trace.result == 51


def test_from_step_is_a_metadata_only_checkpoint_in_v0_1() -> None:
    _, trace = replayable_total.run(2, unit_price=10)
    checkpoint = trace.steps[-1].step_id

    replayed_result, replayed_trace = replay(trace).from_step(checkpoint).run(quantity=3)

    # The selected step does not resume execution; the function is rerun from start.
    assert replayed_result == 31
    assert replayed_trace.result == 31
