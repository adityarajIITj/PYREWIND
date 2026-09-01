"""Tagging and metadata management for traces."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class TraceTag:
    """A tag for organizing traces."""

    name: str
    description: str = ""
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class TraceAnnotation:
    """Annotation for a specific step."""

    step_id: int
    text: str
    created_at: datetime = field(default_factory=datetime.now)


class TraceTagger:
    """Manage tags and annotations for traces."""

    def __init__(self) -> None:
        self.tags: dict[str, TraceTag] = {}
        self.annotations: dict[int, list[TraceAnnotation]] = {}

    def add_tag(self, name: str, description: str = "") -> None:
        """Add a tag."""
        self.tags[name] = TraceTag(name=name, description=description)

    def remove_tag(self, name: str) -> None:
        """Remove a tag."""
        self.tags.pop(name, None)

    def has_tag(self, name: str) -> bool:
        """Check if a tag exists."""
        return name in self.tags

    def list_tags(self) -> list[str]:
        """List all tags."""
        return list(self.tags.keys())

    def annotate_step(self, step_id: int, text: str) -> None:
        """Add annotation to a step."""
        if step_id not in self.annotations:
            self.annotations[step_id] = []
        self.annotations[step_id].append(TraceAnnotation(step_id=step_id, text=text))

    def get_annotations(self, step_id: int) -> list[str]:
        """Get all annotations for a step."""
        if step_id not in self.annotations:
            return []
        return [a.text for a in self.annotations[step_id]]

    def clear_annotations(self, step_id: int) -> None:
        """Clear all annotations for a step."""
        self.annotations.pop(step_id, None)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "tags": list(self.tags.keys()),
            "annotations": {
                step_id: self.get_annotations(step_id)
                for step_id in self.annotations.keys()
            },
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TraceTagger:
        """Deserialize from dictionary."""
        tagger = cls()
        for tag in data.get("tags", []):
            tagger.add_tag(tag)
        for step_id, annots in data.get("annotations", {}).items():
            for text in annots:
                tagger.annotate_step(int(step_id), text)
        return tagger
