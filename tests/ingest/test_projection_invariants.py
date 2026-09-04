"""Every source-form projection reconstructs text and names source contributors."""

import pytest

from rdam.ingest import ProductionIngestor
from rdam.ingest.contracts.preparation import ContentInventory, SegmentKind
from rdam.ingest.contracts.source import SourceForm
from rdam.ingest.projection import project
from tests.ingest.test_inventory_completeness import source_case
from tests.ingest.test_projection_contracts import prose_requirement
from tests.ingest.test_table_linearisation import table_requirement


@pytest.mark.parametrize("form", tuple(SourceForm))
@pytest.mark.parametrize("tables", (False, True))
def test_reconstruct_and_transformation_invariants(form: SourceForm, tables: bool) -> None:
    source, _ = source_case(form)
    inventory = ContentInventory.from_preparation(ProductionIngestor().prepare(source))
    projection = project(inventory, table_requirement() if tables else prose_requirement())
    originals = {item.item_id: item for item in inventory.items}
    text = ""
    transformations = {record.transformation_id: record for record in projection.transformations}
    for order, segment in enumerate(projection.prepared_document.segments):
        assert segment.order == order and segment.prepared_range.start == len(text)
        text += segment.text
        if segment.kind is not SegmentKind.SEPARATOR:
            assert segment.contributing_item_ids and segment.source_anchors
            assert all(identity in originals for identity in segment.contributing_item_ids)
            assert all(
                any(anchor in originals[identity].anchors for identity in segment.contributing_item_ids)
                for anchor in segment.source_anchors
            )
            assert all(
                any(anchor in segment.source_anchors for anchor in originals[identity].anchors)
                for identity in segment.contributing_item_ids
            )
        if segment.kind is SegmentKind.DERIVED:
            assert segment.transformation_ids
        for identity in segment.transformation_ids:
            assert segment.segment_id in transformations[identity].output_segment_ids
    assert text == projection.prepared_document.text


def test_projection_admits_tables_only_when_declared() -> None:
    source, _ = source_case(SourceForm.DOCLING_JSON)
    inventory = ContentInventory.from_preparation(ProductionIngestor().prepare(source))
    assert "North" in project(inventory, table_requirement()).prepared_document.text
    assert "North" not in project(inventory, prose_requirement()).prepared_document.text
