"""Persisted analysis provenance remains total, source-bound, and origin-aware."""

from isanlp_rst.contracts import (
    NodeKindEnum,
    NuclearityPatternEnum,
    OutputFormalismEnum,
    PrimaryRelationEdge,
    RstAnalysis,
    RstDocument,
    RstNode,
)
from isanlp_rst.ingest import ProductionAnalysisResult, SourceArtifact
from isanlp_rst.ingest.contracts import AnalysisUnit, PreparedRange, StructureKind
from isanlp_rst.ingest.prepare import prepare_source
from isanlp_rst.ingest.service import ProductionIngestor, _analysis_anchors
from isanlp_rst.model_loading import ParserCapacity


class _OneEduParser:
    analysis_capacity = ParserCapacity(unit="edu_count", maximum=512, source="test")
    model_release_identity = None

    def parse_document(self, document: RstDocument, output: str = "rst_tree") -> RstAnalysis:
        return RstAnalysis(
            document_id=document.document_id,
            formalism=OutputFormalismEnum(output),
            nodes=(
                RstNode(
                    node_id=1,
                    kind=NodeKindEnum.EDU,
                    edu_span=(1, 1),
                    char_span=(0, len(document.text)),
                    text=document.text,
                ),
            ),
            primary_edges=(),
        )


def test_persisted_result_retains_total_anchor_coverage_and_source_identity() -> None:
    first = ProductionIngestor(parser=_OneEduParser()).analyse(
        SourceArtifact.from_text("Authored discourse.", source_name="first.txt")
    )
    reloaded = ProductionAnalysisResult.from_json(first.to_json())
    assert reloaded.semantic_digest == first.semantic_digest
    assert reloaded.preparation_receipt.analysis_anchor_coverage == 1.0
    assert len(reloaded.analysis_anchors) == 1
    assert reloaded.analysis_anchors[0].origin == "local"

    changed = ProductionIngestor(parser=_OneEduParser()).analyse(
        SourceArtifact.from_text("Changed discourse.", source_name="first.txt")
    )
    assert changed.source.source_id != first.source.source_id
    assert changed.semantic_digest != first.semantic_digest


def test_relation_spanning_recursive_units_is_persisted_as_macro_origin() -> None:
    prepared, _inventory, _dispositions, _contract = prepare_source(
        SourceArtifact.from_text("Alpha Beta", source_name="macro.txt")
    )
    analysis = RstAnalysis(
        document_id=prepared.document.document_id,
        formalism=OutputFormalismEnum.RST_TREE,
        nodes=(
            RstNode(1, NodeKindEnum.ROOT, (1, 2), (0, 10), "Alpha Beta"),
            RstNode(2, NodeKindEnum.EDU, (1, 1), (0, 5), "Alpha"),
            RstNode(3, NodeKindEnum.EDU, (2, 2), (6, 10), "Beta"),
        ),
        primary_edges=(
            PrimaryRelationEdge(
                edge_id="edge-1",
                parent_id=1,
                child_id=2,
                relation_raw="elaboration",
                relation_concept="elaboration",
                nuclearity=NuclearityPatternEnum.NS,
            ),
        ),
    )
    units = (
        AnalysisUnit(
            unit_id="unit-1",
            structure_kind=StructureKind.RANGE,
            output_range=PreparedRange(start=0, end=5),
            capacity_unit="edu_count",
            capacity_maximum=512,
        ),
        AnalysisUnit(
            unit_id="unit-2",
            structure_kind=StructureKind.RANGE,
            output_range=PreparedRange(start=5, end=10),
            capacity_unit="edu_count",
            capacity_maximum=512,
        ),
    )
    anchors = _analysis_anchors(analysis, prepared, units)
    by_id = {anchor.analysis_id: anchor for anchor in anchors}
    assert by_id["node:1"].origin == "macro"
    assert by_id["edge:edge-1"].origin == "macro"
    assert by_id["node:2"].origin == "local"
