"""Truthful source-anchor enrichment: narrowing guard and strict native mapping."""

import pytest

from rdam.ingest import ProductionIngestor, SourceArtifact
from rdam.ingest.contracts.source import TextSpanAnchor
from rdam.ingest.enrichment import enrich_parser_evidence, resolve_source_range
from rdam.ingest.contracts.preparation import PreparedRange
from rdam.ingest.contracts.analysis import AnchorTargetKind
from rdam.rst.contracts import RstDocument
from rdam.rst.relations.primer import DiscourseMarkerPrimer

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

    narrowed = resolve_source_range(
        prepared,
        segment.prepared_range.start,
        segment.prepared_range.start + 5,
    )
    assert len(narrowed) == 1
    narrowed_anchor = narrowed[0]
    assert isinstance(narrowed_anchor, TextSpanAnchor)
    assert narrowed_anchor.start == anchor.start
    assert narrowed_anchor.end - narrowed_anchor.start == 5
    assert narrowed_anchor.quote == segment.text[:5]

    transformed = segment.model_copy(update={"transformation_ids": ("transformation:0000",)})
    unnarrowed = resolve_source_range(
        prepared.model_copy(update={"segments": (transformed,)}),
        segment.prepared_range.start,
        segment.prepared_range.start + 5,
    )
    assert unnarrowed == tuple(segment.source_anchors)


def test_analysis_anchor_without_native_mapping_raises(parser_builder: ParserBuilder) -> None:
    outcome = ProductionIngestor(parser=parser_builder()).analyse(
        SourceArtifact.from_text("First. Second.", source_name="anchors.txt")
    )
    parser_result = outcome.semantic.parser_result
    assert parser_result is not None
    primary = parser_result.semantic.primary_inference
    first, *remaining = primary.segmentation_decisions
    tokenless = primary.model_copy(update={
        "segmentation_decisions": (first.model_copy(update={"token_ids": ()}), *remaining)
    })
    damaged = parser_result.model_copy(update={
        "semantic": parser_result.semantic.model_copy(update={"primary_inference": tokenless})
    })
    with pytest.raises(ValueError, match="no native source mapping"):
        enrich_parser_evidence(outcome.semantic.preparation, damaged)


def test_graph_source_ranges_do_not_expand_into_descendant_token_anchors(parser_builder: ParserBuilder) -> None:
    text = "First claim. However, second claim."
    outcome = ProductionIngestor(parser=parser_builder()).analyse(
        SourceArtifact.from_text(text, source_name="compact-ranges")
    )
    analysis = outcome.semantic.analysis
    assert analysis is not None
    root = analysis.root_node
    assert root is not None
    anchor = next(item for item in outcome.semantic.anchors
                  if item.target_kind is AnchorTargetKind.NODE and item.target_id == str(root.node_id))
    assert len(anchor.token_ids) > 1
    assert anchor.source_anchors == (TextSpanAnchor(
        artifact_identity=outcome.semantic.preparation.semantic.source.source_id,
        start=root.char_span[0], end=root.char_span[1], quote=text[root.char_span[0]:root.char_span[1]],
    ),)
    parser = outcome.semantic.parser_result
    assert parser is not None
    primed = DiscourseMarkerPrimer().prime_analysis(
        parser.analysis, RstDocument.from_text(text, document_id=analysis.document_id),
    )
    assert primed.signals
    with_signals = parser.model_copy(update={
        "semantic": parser.semantic.model_copy(update={"analysis": primed})
    })
    _, enriched = enrich_parser_evidence(outcome.semantic.preparation, with_signals)
    for signal in primed.signals:
        signal_anchor = next(item for item in enriched
                             if item.target_kind is AnchorTargetKind.SUPPORTING_SIGNAL
                             and item.target_id == signal.signal_id)
        assert tuple(item.quote for item in signal_anchor.source_anchors if isinstance(item, TextSpanAnchor)) == (
            tuple(text[start:end] for start, end in signal.char_spans)
        )


def test_range_resolution_clips_each_untransformed_segment_in_original_coordinates() -> None:
    prepared = ProductionIngestor().prepare(
        SourceArtifact.from_text("αβγδεζ", source_name="unicode-ranges")
    ).semantic.prepared_document
    original = prepared.segments[0]
    source = original.source_anchors[0]
    assert isinstance(source, TextSpanAnchor)
    segments = tuple(original.model_copy(update={
        "segment_id": f"segment:{start}",
        "text": prepared.text[start:end],
        "prepared_range": PreparedRange(start=start, end=end),
        "source_anchors": (TextSpanAnchor(
            artifact_identity=source.artifact_identity,
            start=source.start + start,
            end=source.start + end,
            quote=prepared.text[start:end],
        ),),
    }) for start, end in ((0, 3), (3, 6)))
    split = prepared.model_copy(update={"segments": segments})
    resolved = resolve_source_range(split, 1, 5)
    assert resolved == (
        TextSpanAnchor(artifact_identity=source.artifact_identity, start=source.start + 1,
                      end=source.start + 3, quote="βγ"),
        TextSpanAnchor(artifact_identity=source.artifact_identity, start=source.start + 3,
                      end=source.start + 5, quote="δε"),
    )


@pytest.mark.parametrize(("start", "end"), ((-1, 2), (1, 1), (2, 1), (0, 100)))
def test_range_resolution_rejects_invalid_coordinates(start: int, end: int) -> None:
    prepared = ProductionIngestor().prepare(
        SourceArtifact.from_text("Text.", source_name="bounds")
    ).semantic.prepared_document
    with pytest.raises(ValueError, match="within prepared text"):
        resolve_source_range(prepared, start, end)
