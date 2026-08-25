from pathlib import Path

from isanlp_rst.ingest import SourceArtifact, SourceForm
from isanlp_rst.ingest.contracts import ContentClass, PreparationPolicy
from isanlp_rst.ingest.policy import AUTHORED_PROSE_V1
from isanlp_rst.ingest.prepare import inventory_source
from isanlp_rst.ingest.service import ProductionIngestor


FIXTURE = Path("tests/fixtures/docling/pptx.docling.json")


def test_docling_inventory_includes_notes_tables_and_pictures() -> None:
    artifact = SourceArtifact.from_path(FIXTURE, source_form=SourceForm.DOCLING_JSON)
    inventory, contract = inventory_source(artifact)
    classes = {item.content_class for item in inventory}
    assert contract.validator_version == "2.92.0"
    assert ContentClass.NOTE in classes
    assert ContentClass.TABLE in classes
    assert ContentClass.PICTURE in classes


def test_docling_default_primary_excludes_notes_and_table_structure() -> None:
    artifact = SourceArtifact.from_path(FIXTURE, source_form=SourceForm.DOCLING_JSON)
    prepared = ProductionIngestor(parser=None).prepare(artifact)
    inventory, _ = inventory_source(artifact)
    primary_classes = {
        item.content_class for item in inventory if item.item_id in set(prepared.primary_item_ids)
    }
    assert ContentClass.NOTE not in primary_classes
    assert ContentClass.TABLE not in primary_classes
    assert ContentClass.TABLE_CELL not in primary_classes


def test_named_policy_explicitly_admits_notes_with_source_identity() -> None:
    artifact = SourceArtifact.from_path(FIXTURE, source_form=SourceForm.DOCLING_JSON)
    policy = PreparationPolicy(
        name="authored_prose_with_notes",
        version="1",
        primary_classes=(*AUTHORED_PROSE_V1.primary_classes, ContentClass.NOTE),
        side_channel_classes=AUTHORED_PROSE_V1.side_channel_classes,
        excluded_classes=tuple(
            content_class
            for content_class in AUTHORED_PROSE_V1.excluded_classes
            if content_class is not ContentClass.NOTE
        ),
    )
    prepared = ProductionIngestor(parser=None).prepare(artifact, policy=policy)
    inventory, _ = inventory_source(artifact)
    note_ids = {item.item_id for item in inventory if item.content_class is ContentClass.NOTE}

    assert note_ids
    assert note_ids <= set(prepared.primary_item_ids)
    assert all(
        segment.source_item_id in note_ids
        for segment in prepared.segments
        if segment.source_item_id in note_ids
    )
