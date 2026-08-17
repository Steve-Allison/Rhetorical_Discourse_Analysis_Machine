"""Schema types for the Markdown-native RST output.

All types are frozen-slots dataclasses with value-equality semantics.
Serialise via ``result.to_dict()`` / ``result.to_json()``.

Addressing is markdown-native: each ``block_ref`` is ``#/blocks/N`` —
a stable sequential identifier assigned in document order, parallel to
Docling's ``#/texts/N``. Table cells live in their own address space
(``#/tables/T/cells/K``, K = grid position in row-major order) because
tables are analysed two-level (2026-06-12 directive, Option 2): cells
never enter the main document harvest; each table gets its own
mini-parse whose relations/edus land in
``MarkdownRstResult.table_analyses``.
"""

import json
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class HarvestSpan:
    """One unit of text harvested from a markdown document.

    ``block_ref`` is ``#/blocks/N`` for main-harvest spans and
    ``#/tables/T/cells/K`` for cells inside a table harvest.
    ``kind`` is one of: ``"heading"``, ``"paragraph"``, ``"list_item"``,
    ``"blockquote_paragraph"``, ``"blockquote_heading"``,
    ``"code_block"``, ``"html_block"``, ``"table_header_cell"``,
    ``"table_cell"``.

    ``line_begin`` / ``line_end`` are the 0-based source line range from
    markdown-it's ``token.map`` — kept for debugging (not exposed in the
    JSON result for shape parity with the other native paths).

    ``level`` is set only for headings (1–6, including quoted headings).
    ``table_idx`` / ``row_idx`` / ``col_idx`` are set only for cells.

    ``start`` / ``end`` are half-open character offsets into the harvest
    the span belongs to (document harvest or one table's harvest).
    """

    block_ref: str
    kind: str
    text: str
    start: int
    end: int
    line_begin: int
    line_end: int
    level: int | None = None
    table_idx: int | None = None
    row_idx: int | None = None
    col_idx: int | None = None


@dataclass(frozen=True, slots=True)
class HarvestResult:
    """Concatenated harvest produced from a markdown document.

    ``full_text`` is the input passed to the RST parser. ``spans`` is the
    ordered tuple of HarvestSpans that compose it.
    """

    full_text: str
    spans: tuple[HarvestSpan, ...]


@dataclass(frozen=True, slots=True)
class TableHarvest:
    """One table's cell harvest, offsets local to ``full_text``.

    ``marker_ref`` is the synthetic ``#/tables/T`` boundary marker.
    ``spans`` covers the non-empty cells in row-major order; cell refs
    are ``#/tables/T/cells/K`` with K counting every grid position
    (including empty cells), so refs stay stable.
    """

    table_idx: int
    marker_ref: str
    full_text: str
    spans: tuple[HarvestSpan, ...]


@dataclass(frozen=True, slots=True)
class Boundary:
    """One structural boundary in the source document.

    Boundaries are emitted from the markdown structure independently of
    the RST tree. The mapper intersects each relation's block_refs with
    each boundary's ``block_refs`` to compute ``boundary_memberships``.

    Boundary kinds: ``"section"``, ``"table"``, ``"code_block"``,
    ``"document"``. Section boundaries carry ``level`` (1–6). Table
    boundaries hold the synthetic ``#/tables/T`` marker plus each cell's
    ``block_ref``.
    """

    id: str
    kind: str
    label: str | None
    parent_block_ref: str | None
    block_refs: tuple[str, ...]
    level: int | None = None


@dataclass(frozen=True, slots=True)
class RstRelation:
    """One internal node of an RST tree."""

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
    """One leaf of an RST tree (Elementary Discourse Unit)."""

    id: int
    block_refs: tuple[str, ...]
    depth: int


@dataclass(frozen=True, slots=True)
class TableAnalysis:
    """The per-table RST mini-parse (two-level analysis, Option 2).

    ``id`` is the matching ``table-T`` boundary id. ``relations`` /
    ``edus`` use an id namespace local to this analysis. Cell refs
    resolve against the ``table-T`` boundary's ``block_refs``.
    """

    id: str
    relations: tuple[RstRelation, ...]
    edus: tuple[RstEdu, ...]


@dataclass(frozen=True, slots=True)
class MarkdownRstResult:
    """Top-level output of ``parse_markdown``."""

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

    def to_format_analysis(self) -> Any:
        """Project result into a typed FormatRstAnalysis contract."""
        from isanlp_rst.contracts import (
            FormatRstAnalysis,
            NodeKindEnum,
            NuclearityPatternEnum,
            OutputFormalismEnum,
            PrimaryRelationEdge,
            ProvenanceRecord,
            RstAnalysis,
            RstNode,
        )

        nodes: list[RstNode] = []
        primary_edges: list[PrimaryRelationEdge] = []
        node_map: dict[str, int] = {}

        for edu in self.edus:
            for blk in edu.block_refs:
                node_map[blk] = edu.id
            nodes.append(
                RstNode(
                    node_id=edu.id,
                    kind=NodeKindEnum.EDU,
                    edu_span=(edu.id, edu.id),
                    char_span=(0, 0),
                    text="",
                )
            )

        for rel in self.relations:
            nuc = (
                NuclearityPatternEnum(rel.nuclearity)
                if rel.nuclearity in NuclearityPatternEnum
                else NuclearityPatternEnum.NS
            )
            nodes.append(
                RstNode(
                    node_id=rel.id,
                    kind=NodeKindEnum.MULTINUCLEAR_GROUP if rel.nuclearity == "NN" else NodeKindEnum.SPAN,
                    edu_span=(min(rel.left_id, rel.right_id), max(rel.left_id, rel.right_id)),
                    char_span=(0, 0),
                    text="",
                )
            )
            primary_edges.append(
                PrimaryRelationEdge(
                    edge_id=f"e_{rel.id}_{rel.left_id}",
                    parent_id=rel.id,
                    child_id=rel.left_id,
                    relation_raw=rel.relation,
                    relation_concept=rel.relation,
                    nuclearity=nuc,
                )
            )
            primary_edges.append(
                PrimaryRelationEdge(
                    edge_id=f"e_{rel.id}_{rel.right_id}",
                    parent_id=rel.id,
                    child_id=rel.right_id,
                    relation_raw=rel.relation,
                    relation_concept=rel.relation,
                    nuclearity=nuc,
                )
            )

        doc_analysis = RstAnalysis(
            document_id=self.source,
            formalism=OutputFormalismEnum.RST_TREE,
            nodes=tuple(nodes),
            primary_edges=tuple(primary_edges),
            provenance=ProvenanceRecord(
                producer=self.tool,
                software_version=self.tool_version,
                model_id=self.model_version,
            ),
        )

        table_map: dict[str, RstAnalysis] = {}
        for tbl in self.table_analyses:
            tbl_nodes: list[RstNode] = []
            tbl_edges: list[PrimaryRelationEdge] = []
            for edu in tbl.edus:
                tbl_nodes.append(
                    RstNode(
                        node_id=edu.id,
                        kind=NodeKindEnum.EDU,
                        edu_span=(edu.id, edu.id),
                        char_span=(0, 0),
                        text="",
                    )
                )
            for rel in tbl.relations:
                nuc = (
                    NuclearityPatternEnum(rel.nuclearity)
                    if rel.nuclearity in NuclearityPatternEnum
                    else NuclearityPatternEnum.NS
                )
                tbl_nodes.append(
                    RstNode(
                        node_id=rel.id,
                        kind=NodeKindEnum.MULTINUCLEAR_GROUP if rel.nuclearity == "NN" else NodeKindEnum.SPAN,
                        edu_span=(min(rel.left_id, rel.right_id), max(rel.left_id, rel.right_id)),
                        char_span=(0, 0),
                        text="",
                    )
                )
                tbl_edges.append(
                    PrimaryRelationEdge(
                        edge_id=f"e_{rel.id}_{rel.left_id}",
                        parent_id=rel.id,
                        child_id=rel.left_id,
                        relation_raw=rel.relation,
                        relation_concept=rel.relation,
                        nuclearity=nuc,
                    )
                )
                tbl_edges.append(
                    PrimaryRelationEdge(
                        edge_id=f"e_{rel.id}_{rel.right_id}",
                        parent_id=rel.id,
                        child_id=rel.right_id,
                        relation_raw=rel.relation,
                        relation_concept=rel.relation,
                        nuclearity=nuc,
                    )
                )
            table_map[tbl.id] = RstAnalysis(
                document_id=f"{self.source}_{tbl.id}",
                formalism=OutputFormalismEnum.RST_TREE,
                nodes=tuple(tbl_nodes),
                primary_edges=tuple(tbl_edges),
            )

        return FormatRstAnalysis(
            document_analysis=doc_analysis,
            table_analyses=table_map,
            node_map=node_map,
        )
