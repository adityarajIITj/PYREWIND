from pyrewind import rewindable


@rewindable
def _make_result(prefix: str) -> dict[str, int | str]:
    result = {"label": prefix, "count": 2}
    return result


def test_successful_trace_keeps_result_and_result_representation() -> None:
    result, trace = _make_result.run("items")

    assert trace.result == result
    assert trace.result_repr == repr(result)
    assert trace.exception is None
