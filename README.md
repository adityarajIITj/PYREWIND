# pyrewind

`pyrewind` records the line-by-line execution of a regular Python function and returns an inspectable trace alongside its result. It is intended for local debugging, teaching, and lightweight execution forensics: run a function, inspect the values that were in scope at each recorded line, save the trace, and make an assisted rerun with changed keyword arguments.

## Install

pyrewind has no required runtime dependencies and supports Python 3.10+.

```bash
python -m pip install pyrewind
```

For a checkout of this repository:

```bash
python -m pip install -e .
```

## 60-second quickstart

```python
from pyrewind import rewindable


@rewindable
def apply_discount(price, percent):
    discount = price * percent / 100
    return price - discount


# Ordinary calls retain the function's normal behavior.
assert apply_discount(100, 20) == 80

# Use .run() when a trace is wanted.
result, trace = apply_discount.run(100, 20)
print(result)                         # 80.0
print(len(trace.steps))               # one or more line snapshots
print(trace.at(0).locals())           # locals at the first recorded step

trace.to_file("discount.pyrewind.json")
```

See [examples/basic_usage.py](examples/basic_usage.py) for a complete runnable example.

## API reference

### `@rewindable`

```python
from pyrewind import rewindable


@rewindable
def function(...):
    ...
```

The decorated callable preserves its usual call behavior: `function(*args, **kwargs)` simply executes the original function and returns its result.

Call `function.run(*args, **kwargs)` to execute it under pyrewind's tracer. On success it returns `(result, trace)`. Step IDs are zero-based, contiguous, and identify the corresponding entry in `trace.steps`.

The decorator also accepts these optional keyword arguments:

```python
@rewindable(max_depth=3, capture_exceptions=True)
def function(...):
    ...
```

`max_depth` bounds recursive freezing of container values in local snapshots. With the default `capture_exceptions=True`, `.run()` still re-raises the original exception, preserving normal Python error handling. The finalized trace is then available as `function.last_trace` (it is `None` before the first traced run). Its `exception` field contains the exception type, message, and representation.

### `Trace`

`Trace` is the object returned by `.run()`.

- `trace.steps` is an ordered list of step records. Each record has a `step_id`, timestamp, filename, function name, line number, and frozen local snapshot.
- `trace.result` is the in-memory return value for a successful execution.
- `trace.exception` is `None` for a successful run or an exception record for a failed traced run.
- `trace.at(step_id)` returns a `StepView` for that recorded step.
- `trace.to_file(path)` writes a JSON trace artifact.
- `Trace.from_file(path)` loads a JSON trace artifact.

A `StepView` provides:

```python
view = trace.at(0)
view.locals()    # dict
view.line_no()   # int
view.function()  # str
view.filename()  # str
```

Trace artifacts use the `.pyrewind.json` suffix by convention. They contain a versioned, JSON-safe representation of the trace. The original runtime return object is intentionally in-memory only; use `result_repr` when inspecting a trace loaded from disk.

### `replay(trace)`

```python
from pyrewind import replay

new_result, new_trace = replay(trace).run(quantity=4)
new_result, new_trace = replay(trace).from_step(2).run(quantity=4)
```

Replay is an **assisted rerun**, not time travel. In the same Python process, pyrewind can reuse captured call inputs and patch the keyword arguments given to `.run()`. A persisted trace cannot safely reconstruct arbitrary values from their `repr`; supply the function's required keyword arguments yourself when rerunning one. Functions that require positional-only inputs are therefore not portable replay targets in v0.1.

`from_step(step_id)` records a checkpoint selection for the replay workflow, but in v0.1 it is metadata-only: the function is always re-executed from its start. It does not resume Python execution from that line.

## Determinism notes

pyrewind captures Python `line` events for the decorated function only. Step order and source locations follow that function's execution, but timestamps, randomness, I/O, clocks, threads, and external services are outside its control. Replaying such a function reruns those effects; pyrewind does not stub or reverse them.

Local snapshots are frozen into JSON-safe values as they are captured. Primitive values are retained; standard containers are copied recursively up to `max_depth`; unsupported or deeply nested values are represented with their type and `repr`. This makes earlier snapshots stable even when a mutable local is changed later, but it is not a deep object debugger.

## Limitations and non-goals (v0.1)

- Regular synchronous Python functions are the supported target. Async, generator, and coroutine tracing are not a v0.1 feature.
- Nested calls are not expanded into the parent trace; only the decorated function's own line events are recorded.
- Replay is a rerun with supplied or same-process inputs, not checkpoint restoration or deterministic execution.
- Saved traces are portable JSON diagnostics, not a serialization format for arbitrary Python objects or executable state.
- This release does not provide configurable variable filtering, secret redaction hooks, I/O stubs, or a visual trace viewer.

## Performance and privacy

Line tracing and freezing locals add noticeable overhead, so use pyrewind for debugging and focused investigations rather than hot production paths.

Traces can contain values from local variables, including credentials, tokens, customer data, and file paths. Treat trace files as sensitive artifacts: avoid committing or sharing them, review them before export, and redact sensitive values in application code until configurable redaction hooks are available.
