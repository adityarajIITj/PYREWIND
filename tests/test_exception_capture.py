import pytest

from pyrewind import Trace, rewindable


@rewindable
def _raise_for_trace(label: str) -> None:
    detail = f"invalid: {label}"
    raise ValueError(detail)


def test_run_reraises_original_exception_and_keeps_finalized_trace() -> None:
    assert _raise_for_trace.last_trace is None

    with pytest.raises(ValueError, match="invalid: sample"):
        _raise_for_trace.run("sample")

    trace = _raise_for_trace.last_trace
    assert isinstance(trace, Trace)
    assert trace.result is None
    assert trace.steps
    assert trace.exception is not None
    assert trace.exception.type_name == "ValueError"
    assert trace.exception.message == "invalid: sample"
    assert "ValueError" in trace.exception.repr_text
