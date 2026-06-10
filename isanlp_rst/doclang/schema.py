"""Schema types for the DocLang-native RST output.

All types are frozen-slots dataclasses with value-equality semantics.
Serialise to JSON via stdlib `json` after `dataclasses.asdict`.

Addressing is DocLang-native: each ``xpath`` is a local-name canonical
path (e.g. ``"/doclang[1]/heading[2]"``) — namespace-agnostic, 1-based
sibling positions per local name. See ``loader.local_path`` for the
generator and the Phase 1 verification memory at
``.claude/memory/verified_doclang_fixtures.md`` for the rationale.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class HarvestSpan:
    """One unit of text harvested from a DocLang document.

    ``xpath`` is the source element's local-name canonical path; it is
    unique within the document. ``thread_id`` is the host element's
    ``<thread thread_id="N"/>`` value when present (None otherwise — the
    common case). ``layer`` records the effective ``<layer>`` value
    (``"body" | "background" | "furniture"``) — defaulting to ``"body"``
    when no ``<layer>`` head property is present.

    ``start`` / ``end`` are half-open character offsets into the
    concatenated harvest.
    """

    xpath: str
    thread_id: int | None
    layer: str
    text: str
    start: int
    end: int


@dataclass(frozen=True, slots=True)
class HarvestResult:
    """Concatenated harvest produced from a DocLang document.

    ``full_text`` is the input passed to the RST parser. ``spans`` is the
    ordered tuple of HarvestSpans that compose it.
    """

    full_text: str
    spans: tuple[HarvestSpan, ...]


@dataclass(frozen=True, slots=True)
class Boundary:
    """One structural boundary in the source document.

    Boundaries are emitted from the DocLang structure independently of
    the RST tree. The mapper intersects each relation's xpaths with each
    boundary's ``xpaths`` to compute ``boundary_memberships``.

    Boundary kinds (per the Phase 0 plan):
    ``"heading"``, ``"page"``, ``"group"``, ``"table"``,
    ``"field_region"``, ``"document"``.
    """

    id: str
    kind: str
    label: str | None
    parent_xpath: str | None
    xpaths: tuple[str, ...]
    level: int | None = None
    page_no: int | None = None


@dataclass(frozen=True, slots=True)
class RstRelation:
    """One internal node of the RST tree."""

    id: int
    relation: str
    nuclearity: str
    nucleus_xpaths: tuple[str, ...]
    satellite_xpaths: tuple[str, ...]
    nucleus_thread_ids: tuple[int, ...]
    satellite_thread_ids: tuple[int, ...]
    depth: int
    left_id: int
    right_id: int
    boundary_memberships: tuple[str, ...]
    note: str | None = None


@dataclass(frozen=True, slots=True)
class RstEdu:
    """One leaf of the RST tree (Elementary Discourse Unit)."""

    id: int
    xpaths: tuple[str, ...]
    thread_ids: tuple[int, ...]
    depth: int


@dataclass(frozen=True, slots=True)
class DoclangRstResult:
    """Top-level output of ``parse_doclang``."""

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
