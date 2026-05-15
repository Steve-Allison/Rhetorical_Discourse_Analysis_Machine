"""Schema types for the Docling-native RST output.

All types are frozen-slots dataclasses with value-equality semantics.
Serialise to JSON via stdlib `json` after `dataclasses.asdict`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class HarvestSpan:
    """One unit of text harvested from the Docling document.

    `self_ref` is the source node's Docling identifier (e.g. ``#/texts/47``
    for a TextItem, ``#/pictures/3`` for a picture-description span). `start`
    and `end` are half-open character offsets into the concatenated harvest.
    """

    self_ref: str
    text: str
    start: int
    end: int


@dataclass(frozen=True, slots=True)
class HarvestResult:
    """Concatenated harvest produced from a DoclingDocument.

    `full_text` is the input passed to the RST parser. `spans` is the
    ordered tuple of HarvestSpans that compose it.
    """

    full_text: str
    spans: tuple[HarvestSpan, ...]


@dataclass(frozen=True, slots=True)
class Boundary:
    """One structural boundary in the source document.

    Boundaries are emitted from the Docling structure independently of
    the RST tree. The mapper intersects each relation's refs with each
    boundary's `self_refs` to compute `boundary_memberships`.
    """

    id: str
    kind: str
    label: str | None
    parent_self_ref: str | None
    self_refs: tuple[str, ...]
    level: int | None = None
    page_no: int | None = None


@dataclass(frozen=True, slots=True)
class RstRelation:
    """One internal node of the RST tree."""

    id: int
    relation: str
    nuclearity: str
    nucleus_refs: tuple[str, ...]
    satellite_refs: tuple[str, ...]
    depth: int
    left_id: int
    right_id: int
    boundary_memberships: tuple[str, ...]
    note: str | None = None


@dataclass(frozen=True, slots=True)
class RstEdu:
    """One leaf of the RST tree (Elementary Discourse Unit)."""

    id: int
    self_refs: tuple[str, ...]
    depth: int


@dataclass(frozen=True, slots=True)
class DoclingRstResult:
    """Top-level output of ``parse_docling``."""

    schema_name: str
    schema_version: str
    tool: str
    tool_version: str
    model_version: str
    inventory: str
    source: str
    source_origin: dict[str, Any]
    boundaries: tuple[Boundary, ...]
    relations: tuple[RstRelation, ...]
    edus: tuple[RstEdu, ...]
