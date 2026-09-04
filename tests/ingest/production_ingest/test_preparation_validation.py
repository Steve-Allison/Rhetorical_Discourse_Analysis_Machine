"""Preparation source mapping, transformation, anchor, boundary, and coverage tests."""

from rdam.ingest import ProductionIngestor, SourceArtifact
from rdam.ingest.contracts.source import DispositionDecision
from rdam.ingest.validation import validate_preparation_outcome


def test_segments_reconstruct_text_and_source_anchors_exactly() -> None:
    source = SourceArtifact.from_edus(("First EDU.", "Second EDU."), source_name="source.edus")
    outcome = ProductionIngestor().prepare(source)
    prepared = outcome.semantic.prepared_document
    assert "".join(segment.text for segment in prepared.segments) == prepared.text
    assert prepared.text == "First EDU. Second EDU."
    primary = {
        item.item_id: item
        for item in outcome.semantic.inventory
        if item.disposition.decision is DispositionDecision.PRIMARY
    }
    for segment in prepared.segments:
        if segment.contributing_item_ids:
            assert segment.text == primary[segment.contributing_item_ids[0]].text
            assert segment.source_anchors
            assert all(anchor.artifact_identity == source.source_id for anchor in segment.source_anchors)
            assert segment.structural_boundary_id is not None
    assert outcome.semantic.transformations
    assert outcome.semantic.mapping_coverage.covered_units == len(prepared.text)
    assert outcome.semantic.mapping_coverage.total_units == len(prepared.text)
    validate_preparation_outcome(outcome)


def test_every_transformation_and_boundary_reference_resolves() -> None:
    outcome = ProductionIngestor().prepare(
        SourceArtifact.from_edus(("First.", "Second."), source_name="source.edus")
    )
    segment_ids = {segment.segment_id for segment in outcome.semantic.prepared_document.segments}
    transformation_ids = {item.transformation_id for item in outcome.semantic.transformations}
    boundary_ids = {
        boundary.boundary_id
        for boundary in outcome.semantic.prepared_document.structural_boundaries
    }
    assert all(
        set(item.output_segment_ids) <= segment_ids
        for item in outcome.semantic.transformations
    )
    assert all(
        set(segment.transformation_ids) <= transformation_ids
        for segment in outcome.semantic.prepared_document.segments
    )
    assert all(
        segment.structural_boundary_id is None or segment.structural_boundary_id in boundary_ids
        for segment in outcome.semantic.prepared_document.segments
    )
