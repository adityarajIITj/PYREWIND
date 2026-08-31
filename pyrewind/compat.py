"""Compatibility helpers for producing durable, JSON-safe trace values.

The tracer deliberately records a bounded value snapshot rather than retaining
references to live local variables.  ``freeze_value`` is intentionally small
and standard-library-only so it can also be used at the serialization boundary.
"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from typing import Any

DEFAULT_MAX_DEPTH = 3
"""Default recursive container depth retained in a locals snapshot."""

_MAX_REPR_LENGTH = 4_096


def safe_repr(value: object) -> str:
    """Return a representation without allowing a broken ``__repr__`` to fail tracing.

    A cap keeps one unusually large value from making a trace artifact
    impractical.  The normal, short representations used in debugging are left
    unchanged.
    """

    try:
        text = repr(value)
    except Exception as exc:  # pragma: no cover - uncommon, but defensive
        text = f"<unrepresentable {type(value).__name__}: {type(exc).__name__}>"

    if len(text) > _MAX_REPR_LENGTH:
        return f"{text[:_MAX_REPR_LENGTH]}...<truncated>"
    return text


def _marker(value: object) -> dict[str, str]:
    """Represent a value that cannot safely be retained as JSON data."""

    return {
        "__repr__": safe_repr(value),
        "__type__": type(value).__name__,
    }


def _stable_sort_key(value: object) -> str:
    """Create a deterministic sort key for frozen set members."""

    try:
        return json.dumps(
            value,
            sort_keys=True,
            ensure_ascii=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError):  # pragma: no cover - freeze_value should prevent it
        return safe_repr(value)


def freeze_value(value: object, max_depth: int = DEFAULT_MAX_DEPTH) -> object:
    """Return a detached, strictly JSON-safe snapshot of ``value``.

    Primitive values pass through.  Lists, tuples, sets, and mappings are
    recursively copied; tuples and sets become JSON arrays, and sets are sorted
    for deterministic output.  Values outside that supported subset, recursive
    references, and containers beyond ``max_depth`` are represented as::

        {"__repr__": "...", "__type__": "ClassName"}

    ``max_depth`` counts nested containers from the supplied value (depth zero).
    Primitive leaves remain visible even at the depth boundary.
    """

    if isinstance(max_depth, bool) or not isinstance(max_depth, int):
        raise TypeError("max_depth must be an integer")
    if max_depth < 0:
        raise ValueError("max_depth must be greater than or equal to zero")

    return _freeze(value, depth=0, max_depth=max_depth, active_container_ids=set())


def _freeze(
    value: object,
    *,
    depth: int,
    max_depth: int,
    active_container_ids: set[int],
) -> object:
    """Recursive implementation for :func:`freeze_value`."""

    # bool must be checked before int because bool is an int subclass.
    if value is None or isinstance(value, (str, bool)):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        # RFC-compliant JSON does not permit NaN or infinities.
        return value if math.isfinite(value) else _marker(value)

    if depth >= max_depth:
        return _marker(value)

    if isinstance(value, Mapping):
        return _freeze_mapping(
            value,
            depth=depth,
            max_depth=max_depth,
            active_container_ids=active_container_ids,
        )

    if isinstance(value, (list, tuple)):
        return _freeze_sequence(
            value,
            depth=depth,
            max_depth=max_depth,
            active_container_ids=active_container_ids,
        )

    if isinstance(value, (set, frozenset)):
        return _freeze_set(
            value,
            depth=depth,
            max_depth=max_depth,
            active_container_ids=active_container_ids,
        )

    return _marker(value)


def _enter_container(value: object, active_container_ids: set[int]) -> bool:
    """Mark a container active, returning false for a recursive reference."""

    identity = id(value)
    if identity in active_container_ids:
        return False
    active_container_ids.add(identity)
    return True


def _freeze_mapping(
    value: Mapping[Any, Any],
    *,
    depth: int,
    max_depth: int,
    active_container_ids: set[int],
) -> object:
    if not _enter_container(value, active_container_ids):
        return _marker(value)

    try:
        items = list(value.items())
        if all(isinstance(key, str) for key, _ in items):
            return {
                key: _freeze(
                    item,
                    depth=depth + 1,
                    max_depth=max_depth,
                    active_container_ids=active_container_ids,
                )
                for key, item in items
            }

        # JSON object keys must be strings.  Preserve a non-string-key mapping
        # structurally under an explicit marker instead of silently stringifying
        # keys (which could create collisions).
        frozen_items = [
            [
                _freeze(
                    key,
                    depth=depth + 1,
                    max_depth=max_depth,
                    active_container_ids=active_container_ids,
                ),
                _freeze(
                    item,
                    depth=depth + 1,
                    max_depth=max_depth,
                    active_container_ids=active_container_ids,
                ),
            ]
            for key, item in items
        ]
        return {
            "__repr__": safe_repr(value),
            "__type__": type(value).__name__,
            "__items__": frozen_items,
        }
    except Exception:  # custom Mapping implementations can fail while reading
        return _marker(value)
    finally:
        active_container_ids.discard(id(value))


def _freeze_sequence(
    value: list[Any] | tuple[Any, ...],
    *,
    depth: int,
    max_depth: int,
    active_container_ids: set[int],
) -> object:
    if not _enter_container(value, active_container_ids):
        return _marker(value)

    try:
        return [
            _freeze(
                item,
                depth=depth + 1,
                max_depth=max_depth,
                active_container_ids=active_container_ids,
            )
            for item in value
        ]
    except Exception:  # defensive for hostile list/tuple subclasses
        return _marker(value)
    finally:
        active_container_ids.discard(id(value))


def _freeze_set(
    value: set[Any] | frozenset[Any],
    *,
    depth: int,
    max_depth: int,
    active_container_ids: set[int],
) -> object:
    if not _enter_container(value, active_container_ids):
        return _marker(value)

    try:
        frozen = [
            _freeze(
                item,
                depth=depth + 1,
                max_depth=max_depth,
                active_container_ids=active_container_ids,
            )
            for item in value
        ]
        return sorted(frozen, key=_stable_sort_key)
    except Exception:  # defensive for hostile set subclasses
        return _marker(value)
    finally:
        active_container_ids.discard(id(value))

