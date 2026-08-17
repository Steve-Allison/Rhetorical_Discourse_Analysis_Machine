"""Schema types for the Docling-native RST output.

All types are frozen-slots dataclasses with value-equality semantics.
Serialise via ``result.to_dict()`` / ``result.to_json()``.

Tables are analysed two-level (2026-06-12 directive, Option 2): cells
never enter the main document harvest; each table gets its own
mini-parse whose relations/edus land in ``DoclingRstResult.table_analyses``.
Cell addresses are real JSON pointers into the Docling document
(``#/tables/N/data/table_cells/M``), so consumers can resolve them
mechanically against the source.
"""

import json
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class HarvestSpan:
    """One unit of text harvested from the Docling document.

    ``self_ref`` is the source node's Docling identifier (``#/texts/47``
    for a TextItem, ``#/pictures/3`` for a picture-description span,
    ``#/tables/2/data/table_cells/5`` for a table cell inside a
    table harvest). ``start`` and ``end`` are half-open character
    offsets into the harvest the span belongs to (document harvest or
    one table's harvest).

    ``kind`` carries the Docling item label (``"text"``,
    ``"section_header"``, ``"list_item"``, …), ``"picture_description"``
    for picture spans, or ``"table_cell"`` / ``"table_header_cell"``
    for cells. ``row_idx`` / ``col_idx`` are set only for cells
    (``TableCell.start_row_offset_idx`` / ``start_col_offset_idx``).
    """

    self_ref: str
    text: str
    start: int
    end: int
    kind: str = ""
    row_idx: int | None = None
    col_idx: int | None = None


@dataclass(frozen=True, slots=True)
class HarvestResult:
    """Concatenated harvest produced from a DoclingDocument.

    ``full_text`` is the input passed to the RST parser. ``spans`` is the
    ordered tuple of HarvestSpans that compose it.
    """

    full_text: str
    spans: tuple[HarvestSpan, ...]


@dataclass(frozen=True, slots=True)
class TableHarvest:
    """One table's cell harvest, offsets local to ``full_text``.

    ``marker_ref`` is the table's own ``self_ref`` (``#/tables/N``) —
    the synthetic boundary marker. ``spans`` covers the non-empty cells
    in ``TableItem.data.table_cells`` order.
    """

    table_idx: int
    marker_ref: str
    full_text: str
    spans: tuple[HarvestSpan, ...]


@dataclass(frozen=True, slots=True)
class Boundary:
    """One structural boundary in the source document.

    Boundaries are emitted from the Docling structure independently of
    the RST tree. The mapper intersects each relation's refs with each
    boundary's ``self_refs`` to compute ``boundary_memberships``.
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
    self_refs: tuple[str, ...]
    depth: int


@dataclass(frozen=True, slots=True)
class TableAnalysis:
    """The per-table RST mini-parse (two-level analysis, Option 2).

    ``id`` is the matching ``table-N`` boundary id. ``relations`` /
    ``edus`` use an id namespace local to this analysis (independent of
    the document tree and of other tables). Cell refs resolve against
    the ``table-N`` boundary's ``self_refs``.
    """

    id: str
    relations: tuple[RstRelation, ...]
    edus: tuple[RstEdu, ...]


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
            for ref in edu.self_refs:
                node_map[ref] = edu.id
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

