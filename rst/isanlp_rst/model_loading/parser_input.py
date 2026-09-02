"""Minimal legacy parser-input leaf record required for safe model inventory import."""

from dataclasses import dataclass, field, fields
import json
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class ParserInput:
    """Mutable historical parser record with no corpus or training behavior."""

    sentences: list[str] = field(default_factory=list)
    edu_breaks: list[int] = field(default_factory=list)
    label_for_metrics_list: list[str] = field(default_factory=list)
    label_for_metrics: str = ""
    parsing_index: list[int] = field(default_factory=list)
    relation: list[int] = field(default_factory=list)
    decoder_inputs: list[int] = field(default_factory=list)
    parents: list[int] = field(default_factory=list)
    siblings: list[int] = field(default_factory=list)
    sentence_span: list[list[int]] = field(default_factory=list)
    LabelforMetric: list[str] = field(default_factory=list)
    relation_table: list[str] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def edu_count(self) -> int:
        """Return the parser's exact limiting-unit count for this materialized input."""

        return len(self.edu_breaks)

    def to_dict(self) -> dict[str, Any]:
        base = {field_.name: getattr(self, field_.name) for field_ in fields(self) if field_.name != "extra"}
        return base | self.extra

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ParserInput":
        known = {field_.name for field_ in fields(cls) if field_.name != "extra"}
        record = cls(**{key: payload[key] for key in known if key in payload})
        for key, value in payload.items():
            if key not in known:
                record.extra[key] = value
        return record

    def write_json(self, path: Path) -> None:
        path.write_text(json.dumps(self.to_dict(), sort_keys=True) + "\n", encoding="utf-8")

    @classmethod
    def from_json(cls, path: Path) -> "ParserInput":
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("parser input JSON must contain an object")
        return cls.from_dict(payload)
