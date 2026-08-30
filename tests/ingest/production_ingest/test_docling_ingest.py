from pathlib import Path

from isanlp_rst.ingest import SourceArtifact, SourceForm
from isanlp_rst.ingest.contracts import ContentClass, PreparationPolicy
from isanlp_rst.ingest.contracts.source import DispositionDecision
from isanlp_rst.ingest.policy import DEFAULT_PREPARATION_POLICY
from isanlp_rst.ingest.service import ProductionIngestor


FIXTURE = Path("tests/fixtures/docling/pptx.docling.json")


def test_docling_inventory_includes_notes_tables_and_pictures() -> None:
    artifact = SourceArtifact.from_path(FIXTURE, source_form=SourceForm.DOCLING_JSON)
    outcome = ProductionIngestor().prepare(artifact)
    classes = {item.classification for item in outcome.semantic.inventory}
    assert outcome.semantic.source_contract.upstream_version == "2.92.0"
    assert ContentClass.NOTE in classes
    assert ContentClass.TABLE in classes
    assert ContentClass.PICTURE in classes


def test_docling_default_primary_excludes_notes_and_table_structure() -> None:
    artifact = SourceArtifact.from_path(FIXTURE, source_form=SourceForm.DOCLING_JSON)
    outcome = ProductionIngestor().prepare(artifact)
    primary_classes = {
        item.classification
        for item in outcome.semantic.inventory
        if item.disposition.decision is DispositionDecision.PRIMARY
    }
    assert ContentClass.NOTE not in primary_classes
    assert ContentClass.TABLE not in primary_classes
    assert ContentClass.TABLE_CELL not in primary_classes


def test_named_policy_explicitly_admits_notes_with_source_identity() -> None:
    artifact = SourceArtifact.from_path(FIXTURE, source_form=SourceForm.DOCLING_JSON)
    policy = PreparationPolicy.model_validate(
        {
            **DEFAULT_PREPARATION_POLICY.model_dump(exclude={"semantic_digest"}),
            "primary_classes": (*DEFAULT_PREPARATION_POLICY.primary_classes, ContentClass.NOTE),
            "retained_classes": tuple(
                content_class
                for content_class in DEFAULT_PREPARATION_POLICY.retained_classes
                if content_class is not ContentClass.NOTE
            ),
        }
    )
    outcome = ProductionIngestor().prepare(artifact, policy=policy)
    notes = tuple(item for item in outcome.semantic.inventory if item.classification is ContentClass.NOTE)

    assert notes
    assert all(item.disposition.decision is DispositionDecision.PRIMARY for item in notes)
    note_ids = {item.item_id for item in notes}
    assert note_ids <= {
        item_id for segment in outcome.semantic.prepared_document.segments for item_id in segment.contributing_item_ids
    }
