"""Minimal legacy parser-input leaf record required for safe model inventory import."""

from dataclasses import dataclass, field, fields
import json
from pathlib import Path
from typing import Any, cast


def _strings() -> list[str]:
    return []


def _integers() -> list[int]:
    return []


def _integer_rows() -> list[list[int]]:
    return []


def _extras() -> dict[str, Any]:
    return {}


@dataclass(slots=True)
class ParserInput:
    """Mutable historical parser record with no corpus or training behavior."""

    sentences: list[str] = field(default_factory=_strings)
    edu_breaks: list[int] = field(default_factory=_integers)
    label_for_metrics_list: list[str] = field(default_factory=_strings)
    label_for_metrics: str = ""
    parsing_index: list[int] = field(default_factory=_integers)
    relation: list[int] = field(default_factory=_integers)
    decoder_inputs: list[int] = field(default_factory=_integers)
    parents: list[int] = field(default_factory=_integers)
    siblings: list[int] = field(default_factory=_integers)
    sentence_span: list[list[int]] = field(default_factory=_integer_rows)
    LabelforMetric: list[str] = field(default_factory=_strings)
    relation_table: list[str] = field(default_factory=_strings)
    extra: dict[str, Any] = field(default_factory=_extras)

    @property
    def edu_count(self) -> int:
        """Return the parser's exact limiting-unit count for this materialized input."""

        return len(self.edu_breaks)

    def to_dict(self) -> dict[str, Any]:
        base = {field_.name: getattr(self, field_.name) for field_ in fields(self) if field_.name != "extra"}
        return base | self.extra

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> ParserInput:
        known = {field_.name for field_ in fields(cls) if field_.name != "extra"}
        record = cls(**{key: payload[key] for key in known if key in payload})
        for key, value in payload.items():
            if key not in known:
                record.extra[key] = value
        return record

    def write_json(self, path: Path) -> None:
        path.write_text(json.dumps(self.to_dict(), sort_keys=True) + "\n", encoding="utf-8")

    @classmethod
    def from_json(cls, path: Path) -> ParserInput:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("parser input JSON must contain an object")
        return cls.from_dict(cast(dict[str, Any], payload))
