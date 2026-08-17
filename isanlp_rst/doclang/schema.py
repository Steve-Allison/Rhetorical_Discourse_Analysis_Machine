"""Schema types for the DocLang-native RST output.

All types are frozen-slots dataclasses with value-equality semantics.
Serialise via ``result.to_dict()`` / ``result.to_json()``.

Addressing is DocLang-native: each ``xpath`` is a local-name canonical
path (e.g. ``"/doclang[1]/heading[2]"``) — namespace-agnostic, 1-based
sibling positions per local name. See ``loader.local_path`` for the
generator and the Phase 1 verification memory at
``.claude/memory/verified_doclang_fixtures.md`` for the rationale.

Tables are analysed two-level (2026-06-12 directive, Option 2): cells
never enter the main document harvest; each ``<table>`` gets its own
mini-parse whose relations/edus land in
``DoclangRstResult.table_analyses``. Cells are addressed by their cell
marker's xpath (``.../table[1]/fcel[3]``).
"""

import json
from dataclasses import asdict, dataclass
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

    ``kind`` carries the source element's local name (``"text"``,
    ``"heading"``, ``"footnote"``, ``"ldiv"`` for list items,
    ``"caption"``, …) or ``"table_cell"`` / ``"table_header_cell"`` for
    cells inside a table harvest. ``row_idx`` / ``col_idx`` are set only
    for cells (rows delimited by ``<nl/>``, columns counted across all
    grid markers including empty and span-continuation cells).

    ``start`` / ``end`` are half-open character offsets into the harvest
    the span belongs to (document harvest or one table's harvest).
    """

    xpath: str
    thread_id: int | None
    layer: str
    text: str
    start: int
    end: int
    kind: str = ""
    row_idx: int | None = None
    col_idx: int | None = None


@dataclass(frozen=True, slots=True)
class HarvestResult:
    """Concatenated harvest produced from a DocLang document.

    ``full_text`` is the input passed to the RST parser. ``spans`` is the
    ordered tuple of HarvestSpans that compose it. Spans sharing a
    ``thread_id`` with their predecessor are joined with a single space
    (paragraph continuation across page breaks), all other gaps use the
    harvest separator.
    """

    full_text: str
    spans: tuple[HarvestSpan, ...]


@dataclass(frozen=True, slots=True)
class TableHarvest:
    """One ``<table>``'s cell harvest, offsets local to ``full_text``.

    ``marker_xpath`` is the table element's own xpath — the synthetic
    boundary marker. ``spans`` covers the non-empty cells in document
    order.
    """

    table_idx: int
    marker_xpath: str
    full_text: str
    spans: tuple[HarvestSpan, ...]


@dataclass(frozen=True, slots=True)
class Boundary:
    """One structural boundary in the source document.

    Boundaries are emitted from the DocLang structure independently of
    the RST tree. The mapper intersects each relation's xpaths with each
    boundary's ``xpaths`` to compute ``boundary_memberships``.

    Boundary kinds: ``"heading"``, ``"page"``, ``"group"``, ``"table"``,
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
    """One internal node of an RST tree."""

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
    """One leaf of an RST tree (Elementary Discourse Unit)."""

    id: int
    xpaths: tuple[str, ...]
    thread_ids: tuple[int, ...]
    depth: int


@dataclass(frozen=True, slots=True)
class TableAnalysis:
    """The per-table RST mini-parse (two-level analysis, Option 2).

    ``id`` is the matching ``table-N`` boundary id. ``relations`` /
    ``edus`` use an id namespace local to this analysis. Cell xpaths
    resolve against the ``table-N`` boundary's ``xpaths``.
    """

    id: str
    relations: tuple[RstRelation, ...]
    edus: tuple[RstEdu, ...]


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
    table_analyses: tuple[TableAnalysis, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        """JSON-shaped plain data (nested dataclasses → dicts, tuples → lists)."""
        return json.loads(self.to_json(indent=None))

    def to_json(self, *, indent: int | None = 2) -> str:
        """JSON string of the result."""
        return json.dumps(asdict(self), ensure_ascii=False, indent=indent)
