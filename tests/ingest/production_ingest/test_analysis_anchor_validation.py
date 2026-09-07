"""Complete, bounded, reconstructable analysis anchors."""

import pytest

from rdam.ingest import ProductionIngestor, SourceArtifact
from rdam.ingest.contracts.analysis import AnchorTargetKind
from rdam.ingest.contracts.analysis import AnalysisAnchor, ParserAnalysisResult
from rdam.ingest.validation import build_analysis_validation_receipt

from .conftest import ParserBuilder


def test_every_graph_element_has_complete_native_source_anchors(
    parser_builder: ParserBuilder,
) -> None:
    outcome = ProductionIngestor(parser=parser_builder()).analyse(
        SourceArtifact.from_text("First claim. Second claim.", source_name="anchors.txt")
    )
    analysed = outcome.semantic.analysed_document
    analysis = outcome.semantic.analysis
    assert analysed is not None and analysis is not None
    expected = len(analysis.nodes) + len(analysis.primary_edges)
    graph_anchors = tuple(
        anchor
        for anchor in outcome.semantic.anchors
        if anchor.target_kind.value in {"node", "primary_edge"}
    )
    assert len(graph_anchors) == expected
    assert all(anchor.source_anchors for anchor in graph_anchors)
    assert all(
        native.artifact_identity == outcome.semantic.preparation.semantic.source.source_id
        for anchor in graph_anchors
        for native in anchor.source_anchors
    )
    assert all(
        analysed.text[token.character_range.start:token.character_range.end] == token.text
        for token in analysed.tokens
    )

    parser_result = outcome.semantic.parser_result
    assert parser_result is not None
    with pytest.raises(ValueError):
        validate_anchors(parser_result, parser_result.semantic.anchors[:-1])


@pytest.mark.parametrize("duplicate", (True, False))
def test_anchor_target_inventory_rejects_duplicates_and_unknown_nodes(
    parser_builder: ParserBuilder, duplicate: bool,
) -> None:
    outcome = ProductionIngestor(parser=parser_builder()).analyse(
        SourceArtifact.from_text("First claim. Second claim.", source_name="anchor-mutation")
    )
    result = outcome.semantic.parser_result
    assert result is not None
    anchor = next(value for value in result.semantic.anchors if value.target_kind is AnchorTargetKind.NODE)
    extra = anchor if duplicate else anchor.model_copy(update={"target_id": "absent-node"})
    message = "duplicate target identities" if duplicate else "absent graph element"
    with pytest.raises(ValueError, match=message):
        validate_anchors(result, (*result.semantic.anchors, extra))


@pytest.mark.parametrize("kind", (AnchorTargetKind.EDU, AnchorTargetKind.DECISION))
@pytest.mark.parametrize("mutation", ("missing", "unknown"))
def test_evidence_anchor_inventory_is_exact(
    parser_builder: ParserBuilder, kind: AnchorTargetKind, mutation: str,
) -> None:
    outcome = ProductionIngestor(parser=parser_builder()).analyse(
        SourceArtifact.from_text("First. Second.", source_name="evidence-anchors")
    )
    result = outcome.semantic.parser_result
    assert result is not None
    anchors = result.semantic.anchors
    target = next(anchor for anchor in anchors if anchor.target_kind is kind)
    changed = tuple(anchor for anchor in anchors if anchor is not target)
    if mutation == "unknown":
        changed = (*changed, target.model_copy(update={"target_id": "absent-evidence"}))
    with pytest.raises(ValueError, match="exactly cover every EDU and primary decision"):
        validate_anchors(result, changed)


def validate_anchors(result: ParserAnalysisResult, anchors: tuple[AnalysisAnchor, ...]) -> None:
    semantic = result.semantic
    build_analysis_validation_receipt(
        semantic.analysis, semantic.analysed_document, semantic.primary_inference,
        semantic.erst_completion, anchors, policy=semantic.policy,
        composite=semantic.composite_identity, recombination=semantic.recombination,
    )
