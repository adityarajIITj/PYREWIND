"""Strategy pattern for trace serialization and deserialization.

Supports multiple formats:
- JSON (human-readable)
- MessagePack (binary, compact)
- CSV (tabular)
- Custom formats via plugin system
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any
import json
from pathlib import Path


class SerializationStrategy(ABC):
    """Abstract base class for serialization strategies."""

    @property
    @abstractmethod
    def format_name(self) -> str:
        """Name of the format (e.g., 'json', 'msgpack')."""
        pass

    @property
    @abstractmethod
    def file_extension(self) -> str:
        """File extension for this format (e.g., '.json')."""
        pass

    @abstractmethod
    def serialize(self, data: dict[str, Any]) -> bytes:
        """Serialize data to bytes."""
        pass

    @abstractmethod
    def deserialize(self, data: bytes) -> dict[str, Any]:
        """Deserialize bytes back to data."""
        pass

    def serialize_to_file(self, data: dict[str, Any], path: str | Path) -> None:
        """Serialize data to a file."""
        path = Path(path)
        serialized = self.serialize(data)
        path.write_bytes(serialized)

    def deserialize_from_file(self, path: str | Path) -> dict[str, Any]:
        """Deserialize data from a file."""
        path = Path(path)
        data = path.read_bytes()
        return self.deserialize(data)


class JSONSerializationStrategy(SerializationStrategy):
    """JSON serialization (human-readable, default)."""

    def __init__(self, indent: int = 2) -> None:
        self.indent = indent

    @property
    def format_name(self) -> str:
        return "json"

    @property
    def file_extension(self) -> str:
        return ".json"

    def serialize(self, data: dict[str, Any]) -> bytes:
        """Serialize to JSON bytes."""
        return json.dumps(data, indent=self.indent, default=str).encode("utf-8")

    def deserialize(self, data: bytes) -> dict[str, Any]:
        """Deserialize from JSON bytes."""
        return json.loads(data.decode("utf-8"))


class CompactJSONSerializationStrategy(SerializationStrategy):
    """Compact JSON (no whitespace, smaller files)."""

    @property
    def format_name(self) -> str:
        return "json-compact"

    @property
    def file_extension(self) -> str:
        return ".json"

    def serialize(self, data: dict[str, Any]) -> bytes:
        """Serialize to compact JSON bytes."""
        return json.dumps(data, separators=(",", ":"), default=str).encode("utf-8")

    def deserialize(self, data: bytes) -> dict[str, Any]:
        """Deserialize from JSON bytes."""
        return json.loads(data.decode("utf-8"))


class MessagePackSerializationStrategy(SerializationStrategy):
    """MessagePack serialization (binary, compact)."""

    def __init__(self) -> None:
        try:
            import msgpack
            self._msgpack = msgpack
        except ImportError:
            raise ImportError(
                "msgpack is required for MessagePack serialization. "
                "Install it with: pip install msgpack"
            )

    @property
    def format_name(self) -> str:
        return "msgpack"

    @property
    def file_extension(self) -> str:
        return ".msgpack"

    def serialize(self, data: dict[str, Any]) -> bytes:
        """Serialize to MessagePack bytes."""
        return self._msgpack.packb(data, use_bin_type=True)

    def deserialize(self, data: bytes) -> dict[str, Any]:
        """Deserialize from MessagePack bytes."""
        return self._msgpack.unpackb(data, raw=False)


class CSVSerializationStrategy(SerializationStrategy):
    """CSV serialization (tabular, steps only)."""

    @property
    def format_name(self) -> str:
        return "csv"

    @property
    def file_extension(self) -> str:
        return ".csv"

    def serialize(self, data: dict[str, Any]) -> bytes:
        """Serialize trace steps as CSV."""
        import csv
        import io

        output = io.StringIO()
        steps = data.get("steps", [])

        if not steps:
            return b""

        # Get fieldnames from first step
        fieldnames = list(steps[0].keys()) if steps else []
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(steps)

        return output.getvalue().encode("utf-8")

    def deserialize(self, data: bytes) -> dict[str, Any]:
        """Deserialize CSV (limited support, returns steps list)."""
        import csv
        import io

        text = data.decode("utf-8")
        reader = csv.DictReader(io.StringIO(text))
        steps = list(reader)
        return {"steps": steps}


class SerializationStrategyRegistry:
    """Registry for available serialization strategies."""

    def __init__(self) -> None:
        self._strategies: dict[str, SerializationStrategy] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        """Register built-in strategies."""
        self.register(JSONSerializationStrategy())
        self.register(CompactJSONSerializationStrategy())
        self.register(CSVSerializationStrategy())

        # Try to register MessagePack if available
        try:
            self.register(MessagePackSerializationStrategy())
        except ImportError:
            pass  # msgpack not installed

    def register(self, strategy: SerializationStrategy) -> None:
        """Register a serialization strategy."""
        self._strategies[strategy.format_name] = strategy

    def get(self, format_name: str) -> SerializationStrategy | None:
        """Get a strategy by format name."""
        return self._strategies.get(format_name)

    def list_formats(self) -> list[str]:
        """List available format names."""
        return list(self._strategies.keys())

    def serialize(
        self, format_name: str, data: dict[str, Any]
    ) -> bytes:
        """Serialize using a named strategy."""
        strategy = self.get(format_name)
        if strategy is None:
            raise ValueError(f"Unknown serialization format: {format_name}")
        return strategy.serialize(data)

    def deserialize(
        self, format_name: str, data: bytes
    ) -> dict[str, Any]:
        """Deserialize using a named strategy."""
        strategy = self.get(format_name)
        if strategy is None:
            raise ValueError(f"Unknown serialization format: {format_name}")
        return strategy.deserialize(data)


# Global registry singleton
_global_registry: SerializationStrategyRegistry | None = None


def get_global_registry() -> SerializationStrategyRegistry:
    """Get or create the global serialization strategy registry."""
    global _global_registry
    if _global_registry is None:
        _global_registry = SerializationStrategyRegistry()
    return _global_registry
