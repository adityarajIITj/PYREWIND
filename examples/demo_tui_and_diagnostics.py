"""
Demonstration of PyRewind v0.3.0 Interactive Terminal TUI & Root-Cause Diagnostics.

Usage:
1. Run Automated Root-Cause Diagnosis:
       python examples/demo_tui_and_diagnostics.py --diagnose

2. Launch Interactive Terminal Time-Travel Scrubber:
       python examples/demo_tui_and_diagnostics.py --tui
"""

import sys
from pyrewind import rewindable, launch_tui, diagnose_trace


@rewindable
def faulty_financial_pipeline(initial_balance: float, transaction_rates: list[float]):
    """Simulates a complex financial transaction pipeline with an algorithmic bug."""
    balance = initial_balance
    log_records = []
    
    # Process transactions
    for idx, rate in enumerate(transaction_rates):
        fee_factor = rate - 0.05
        adjusted_multiplier = 1.0 + fee_factor
        
        # Step where bug is introduced: divisor becomes 0 when fee_factor is -1.0
        divisor = fee_factor + 1.0
        tax_offset = (balance * 0.02) / divisor
        
        balance = (balance * adjusted_multiplier) - tax_offset
        log_records.append({"step": idx, "balance": balance})
        
    return balance


@rewindable
def healthy_math_algorithm(base: int, count: int):
    """A healthy algorithm for time-travel stepping in the TUI."""
    accumulator = base
    history = []
    for i in range(count):
        step_val = (i + 1) * 3
        accumulator += step_val
        history.append(accumulator)
    return accumulator


def run_diagnostics_demo():
    print("[*] Running faulty_financial_pipeline to capture failure trace...\n")
    try:
        # rate = -0.95 causes fee_factor = -1.0 -> divisor = 0 -> ZeroDivisionError!
        faulty_financial_pipeline.run(1000.0, [0.10, 0.05, -0.95, 0.20])
    except ZeroDivisionError:
        print("[!] Execution crashed with ZeroDivisionError as expected.\n")

    trace = faulty_financial_pipeline.last_trace
    report = diagnose_trace(trace)
    print(report)


def run_tui_demo():
    print("[*] Running healthy_math_algorithm and launching interactive TUI...\n")
    healthy_math_algorithm.run(10, 5)
    trace = healthy_math_algorithm.last_trace
    launch_tui(trace)


if __name__ == "__main__":
    if "--tui" in sys.argv:
        run_tui_demo()
    else:
        run_diagnostics_demo()