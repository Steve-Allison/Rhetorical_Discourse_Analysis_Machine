from pathlib import Path

from isanlp_rst.ingest import SourceArtifact, SourceForm
from isanlp_rst.ingest.contracts import ContentClass
from isanlp_rst.ingest.prepare import inventory_source
from isanlp_rst.ingest.service import ProductionIngestor


def test_doclang_empty_namespace_validates_under_current_contract() -> None:
    artifact = SourceArtifact.from_path(
        Path("tests/fixtures/doclang/ok_no_namespace.dclg"),
        source_form=SourceForm.DOCLANG_XML,
    )
    inventory, contract = inventory_source(artifact)
    assert inventory
    assert contract.validator_version == "0.7.3"


def test_doclang_table_is_retained_but_not_primary() -> None:
    artifact = SourceArtifact.from_path(
        Path("tests/fixtures/doclang/ok_table_rectangular.dclg"),
        source_form=SourceForm.DOCLANG_XML,
    )
    inventory, _ = inventory_source(artifact)
    prepared = ProductionIngestor(parser=None).prepare(artifact)
    table_ids = {
        item.item_id for item in inventory if item.content_class in {ContentClass.TABLE, ContentClass.TABLE_CELL}
    }
    assert table_ids
    assert table_ids.isdisjoint(prepared.primary_item_ids)
    assert prepared.text == ""
