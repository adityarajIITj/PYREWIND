"""Run this file from the project root: python examples/basic_usage.py."""

from pyrewind import replay, rewindable


@rewindable
def order_total(quantity: int, unit_price: float, tax_rate: float = 0.05) -> float:
    subtotal = quantity * unit_price
    tax = subtotal * tax_rate
    return subtotal + tax


def main() -> None:
    # A normal call remains a normal function call.
    print(f"Direct result: {order_total(2, 19.99):.2f}")

    result, trace = order_total.run(2, 19.99)
    print(f"Traced result: {result:.2f}")
    print(f"Recorded steps: {len(trace.steps)}")

    first_step = trace.at(trace.steps[0].step_id)
    print(f"First location: {first_step.filename()}:{first_step.line_no()}")
    print(f"First locals: {first_step.locals()}")

    # v0.1 replay re-executes from the beginning, with keyword overrides.
    replayed_result, replayed_trace = replay(trace).from_step(0).run(quantity=4)
    print(f"Replayed result: {replayed_result:.2f}")
    print(f"Replay recorded steps: {len(replayed_trace.steps)}")


if __name__ == "__main__":
    main()
