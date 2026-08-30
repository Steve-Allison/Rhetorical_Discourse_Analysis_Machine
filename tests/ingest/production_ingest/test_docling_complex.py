"""Current-valid complex Docling content stays complete and out of default RST prose."""

from pathlib import Path

from docling_core.types.doc import ContentLayer, DoclingDocument

from isanlp_rst.ingest import SourceArtifact, SourceForm
from isanlp_rst.ingest.contracts import ContentClass, DispositionDecision, TableCoordinateAnchor
from isanlp_rst.ingest.prepare import inventory_source, prepare_source


PDF = Path("tests/fixtures/docling/pdf.docling.json")


def test_docling_complete_current_traversal_reconciles_to_inventory() -> None:
    document = DoclingDocument.load_from_json(PDF)
    expected_refs = {
        str(item.self_ref)
        for item, _depth in document.iterate_items(
            with_groups=True,
            traverse_pictures=True,
            included_content_layers=set(ContentLayer),
        )
    }
    inventory, _ = inventory_source(SourceArtifact.from_path(PDF, source_form=SourceForm.DOCLING_JSON))
    actual_ids = {item.item_id for item in inventory}
    assert expected_refs <= actual_ids


def test_docling_picture_classification_producer_and_confidence_are_preserved() -> None:
    inventory, _ = inventory_source(SourceArtifact.from_path(PDF, source_form=SourceForm.DOCLING_JSON))
    classified = [
        dict(item.provider_attributes) for item in inventory if "picture_class" in dict(item.provider_attributes)
    ]
    assert classified
    assert any(attributes["picture_class"] == "full_page_image" for attributes in classified)
    assert all(0.0 <= float(attributes["picture_class_confidence"]) <= 1.0 for attributes in classified)
    assert all(attributes["picture_class_created_by"] for attributes in classified)


def test_docling_table_cells_keep_parentage_and_native_coordinates_but_never_default_to_prose() -> None:
    artifact = SourceArtifact.from_path(PDF, source_form=SourceForm.DOCLING_JSON)
    inventory, _ = inventory_source(artifact)
    by_id = {item.item_id: item for item in inventory}
    table_cells = [item for item in inventory if item.classification is ContentClass.TABLE_CELL]
    assert table_cells
    assert all(item.parent_id in by_id for item in table_cells)
    assert all(any(isinstance(anchor, TableCoordinateAnchor) for anchor in item.anchors) for item in table_cells)
    outcome = prepare_source(artifact)
    assert all(
        item.disposition.decision is not DispositionDecision.PRIMARY
        for item in outcome.semantic.inventory
        if item.item_id in {cell.item_id for cell in table_cells}
    )
