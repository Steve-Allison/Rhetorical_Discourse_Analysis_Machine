"""Truthful source-anchor enrichment: narrowing guard and strict native mapping."""

import pytest

from rdam.rst.ingest import ProductionIngestor, SourceArtifact
from rdam.rst.ingest.contracts.source import TextSpanAnchor
from rdam.rst.ingest.enrichment import _anchors_for_range, _enrich_analysis_anchor

from .conftest import ParserBuilder


def test_anchor_narrowing_requires_untransformed_segment_text() -> None:
    prepared = (
        ProductionIngestor()
        .prepare(SourceArtifact.from_text("First. Second.", source_name="anchors.txt"))
        .semantic.prepared_document
    )
    segment = prepared.segments[0]
    assert segment.transformation_ids == ()
    anchor = segment.source_anchors[0]
    assert isinstance(anchor, TextSpanAnchor)
    assert anchor.end - anchor.start == len(segment.text)

    narrowed = _anchors_for_range(
        segment.prepared_range.start,
        segment.prepared_range.start + 5,
        (segment,),
    )
    assert len(narrowed) == 1
    narrowed_anchor = narrowed[0]
    assert isinstance(narrowed_anchor, TextSpanAnchor)
    assert narrowed_anchor.start == anchor.start
    assert narrowed_anchor.end - narrowed_anchor.start == 5
    assert narrowed_anchor.quote == segment.text[:5]

    transformed = segment.model_copy(update={"transformation_ids": ("transformation:0000",)})
    unnarrowed = _anchors_for_range(
        segment.prepared_range.start,
        segment.prepared_range.start + 5,
        (transformed,),
    )
    assert unnarrowed == tuple(segment.source_anchors)


def test_analysis_anchor_without_native_mapping_raises(parser_builder: ParserBuilder) -> None:
    outcome = ProductionIngestor(parser=parser_builder()).analyse(
        SourceArtifact.from_text("First. Second.", source_name="anchors.txt")
    )
    parser_result = outcome.semantic.parser_result
    assert parser_result is not None
    document = parser_result.semantic.analysed_document
    tokenless = parser_result.semantic.anchors[0].model_copy(update={"token_ids": ()})
    with pytest.raises(ValueError, match="no native source mapping"):
        _enrich_analysis_anchor(tokenless, document, ())
