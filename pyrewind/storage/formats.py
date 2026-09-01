"""Trace format handlers for serialization/deserialization."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any


class TraceFormat(ABC):
    """Abstract base for trace formats."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Format name."""
        pass

    @property
    @abstractmethod
    def extension(self) -> str:
        """File extension."""
        pass

    @abstractmethod
    def serialize(self, data: dict[str, Any]) -> bytes:
        """Serialize trace data to bytes."""
        pass

    @abstractmethod
    def deserialize(self, data: bytes) -> dict[str, Any]:
        """Deserialize trace data from bytes."""
        pass

    def save(self, data: dict[str, Any], path: str) -> None:
        """Save trace to file."""
        from pathlib import Path
        Path(path).write_bytes(self.serialize(data))

    def load(self, path: str) -> dict[str, Any]:
        """Load trace from file."""
        from pathlib import Path
        return self.deserialize(Path(path).read_bytes())


class JSONTraceFormat(TraceFormat):
    """Human-readable JSON format (default)."""

    def __init__(self, indent: int = 2) -> None:
        self.indent = indent

    @property
    def name(self) -> str:
        return "json"

    @property
    def extension(self) -> str:
        return ".json"

    def serialize(self, data: dict[str, Any]) -> bytes:
        return json.dumps(data, indent=self.indent, default=str).encode("utf-8")

    def deserialize(self, data: bytes) -> dict[str, Any]:
        return json.loads(data.decode("utf-8"))


class CompactJSONTraceFormat(TraceFormat):
    """Compact JSON (no whitespace)."""

    @property
    def name(self) -> str:
        return "json-compact"

    @property
    def extension(self) -> str:
        return ".json"

    def serialize(self, data: dict[str, Any]) -> bytes:
        return json.dumps(data, separators=(",", ":"), default=str).encode("utf-8")

    def deserialize(self, data: bytes) -> dict[str, Any]:
        return json.loads(data.decode("utf-8"))


class MessagePackTraceFormat(TraceFormat):
    """Binary MessagePack format (compact, fast)."""

    def __init__(self) -> None:
        try:
            import msgpack
            self._msgpack = msgpack
        except ImportError:
            raise ImportError(
                "msgpack is required for MessagePack format. "
                "Install with: pip install msgpack"
            )

    @property
    def name(self) -> str:
        return "msgpack"

    @property
    def extension(self) -> str:
        return ".msgpack"

    def serialize(self, data: dict[str, Any]) -> bytes:
        return self._msgpack.packb(data, use_bin_type=True)

    def deserialize(self, data: bytes) -> dict[str, Any]:
        return self._msgpack.unpackb(data, raw=False)


class CSVTraceFormat(TraceFormat):
    """CSV format for trace steps (steps only, limited)."""

    @property
    def name(self) -> str:
        return "csv"

    @property
    def extension(self) -> str:
        return ".csv"

    def serialize(self, data: dict[str, Any]) -> bytes:
        import csv
        import io

        output = io.StringIO()
        steps = data.get("steps", [])

        if not steps:
            return b""

        fieldnames = list(steps[0].keys()) if steps else []
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        for step in steps:
            row = {}
            for key in fieldnames:
                val = step.get(key)
                # Handle nested dicts/lists
                if isinstance(val, (dict, list)):
                    row[key] = json.dumps(val)
                else:
                    row[key] = val
            writer.writerow(row)

        return output.getvalue().encode("utf-8")

    def deserialize(self, data: bytes) -> dict[str, Any]:
        import csv
        import io

        text = data.decode("utf-8")
        reader = csv.DictReader(io.StringIO(text))
        steps = []

        for row in reader:
            step = {}
            for key, val in row.items():
                # Try to parse JSON for complex types
                if val and val.startswith(("{", "[")):
                    try:
                        step[key] = json.loads(val)
                    except json.JSONDecodeError:
                        step[key] = val
                else:
                    step[key] = val
            steps.append(step)

        return {"steps": steps}
