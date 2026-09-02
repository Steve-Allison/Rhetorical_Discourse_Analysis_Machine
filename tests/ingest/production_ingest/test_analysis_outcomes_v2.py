"""Discriminated, self-contained production analysis outcomes."""

from rdam.rst.ingest import (
    AnalysedOutcome,
    EmptyPrimaryAnalysisOutcome,
    ProductionIngestor,
    SourceArtifact,
    load_contract,
    serialize_contract,
)

from .conftest import ParserBuilder


def test_analysed_outcome_embeds_complete_parser_and_preparation_evidence(
    parser_builder: ParserBuilder,
) -> None:
    result = ProductionIngestor(parser=parser_builder()).analyse(
        SourceArtifact.from_text("Complete evidence. A second claim.", source_name="source.txt")
    )
    assert isinstance(result, AnalysedOutcome)
    assert result.status.value == "analysed"
    assert result.semantic.preparation.semantic.inventory
    assert result.semantic.analysed_document is not None
    assert result.semantic.analysed_document.tokens
    assert result.semantic.parser_result is not None
    assert result.semantic.analysis is not None
    assert result.semantic.analysis.primary_edges
    assert result.semantic.primary_inference is not None
    assert result.semantic.validation is not None
    assert result.semantic.validation.passed
    assert result.semantic.cache_request_identity is not None
    assert result.semantic_digest is not None

    encoded = serialize_contract(result)
    loaded = load_contract(encoded)
    assert isinstance(loaded, AnalysedOutcome)
    assert serialize_contract(loaded) == encoded


def test_empty_primary_outcome_contains_no_fabricated_analysis(
    parser_builder: ParserBuilder,
) -> None:
    result = ProductionIngestor(parser=parser_builder()).analyse(
        SourceArtifact.from_text(" \n", source_name="empty.txt")
    )
    assert isinstance(result, EmptyPrimaryAnalysisOutcome)
    assert result.status.value == "empty_primary_discourse"
    assert result.semantic.parser_result is None
    assert result.semantic.analysed_document is None
    assert result.semantic.analysis is None
    assert result.semantic.primary_inference is None
    assert result.semantic.anchors == ()
