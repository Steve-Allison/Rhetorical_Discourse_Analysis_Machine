"""Complete, bounded, reconstructable analysis anchors."""

import pytest

from rdam.rst.ingest import ProductionIngestor, SourceArtifact
from rdam.rst.ingest.parser_result import validate_parser_analysis_result

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
    damaged_semantic = parser_result.semantic.model_copy(
        update={"anchors": parser_result.semantic.anchors[:-1]}
    )
    with pytest.raises(ValueError):
        validate_parser_analysis_result(
            parser_result.model_copy(update={"semantic": damaged_semantic})
        )
