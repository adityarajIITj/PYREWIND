"""Unit tests for the interactive Terminal TUI Scrubber."""

import pytest
from pyrewind import rewindable
from pyrewind.tui import TerminalScrubber


def test_tui_scrubber_initialization_and_stepping():
    """Test scrubber navigation across execution steps."""
    @rewindable
    def step_function():
        a = 1
        b = 2
        c = a + b
        return c

    step_function.run()
    trace = step_function.last_trace
    assert len(trace.steps) >= 3

    scrubber = TerminalScrubber(trace)
    assert scrubber.current_step_idx == 0

    # Step forward
    scrubber.next_step()
    assert scrubber.current_step_idx == 1

    # Jump to end
    scrubber.jump_to_end()
    assert scrubber.current_step_idx == len(trace.steps) - 1

    # Jump to start
    scrubber.jump_to_start()
    assert scrubber.current_step_idx == 0

    # Step backward at start remains 0
    scrubber.prev_step()
    assert scrubber.current_step_idx == 0


def test_tui_render_step_frame_output():
    """Test text rendering of a step frame."""
    @rewindable
    def calc(x):
        y = x * 10
        return y

    calc.run(5)
    trace = calc.last_trace

    scrubber = TerminalScrubber(trace, source_code="def calc(x):\n    y = x * 10\n    return y")
    frame_text = scrubber.render_step_frame(0, color=False)

    assert "PyRewind Time-Travel Terminal Scrubber" in frame_text
    assert "calc()" in frame_text
    assert "LOCAL VARIABLES" in frame_text
    assert "x" in frame_text
    assert "Controls:" in frame_text


def test_tui_render_exception_badge():
    """Test that scrubber highlights crashed executions."""
    @rewindable
    def failing_function():
        val = 100
        raise ValueError("Intentional crash")

    try:
        failing_function.run()
    except ValueError:
        pass

    trace = failing_function.last_trace
    scrubber = TerminalScrubber(trace)
    frame_text = scrubber.render_step_frame(color=False)

    assert "CRASH: ValueError" in frame_text