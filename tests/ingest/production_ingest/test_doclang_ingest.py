from pathlib import Path

from isanlp_rst.ingest import SourceArtifact, SourceForm
from isanlp_rst.ingest.contracts import ContentClass, DispositionDecision
from isanlp_rst.ingest.prepare import inventory_source
from isanlp_rst.ingest.service import ProductionIngestor


def test_doclang_empty_namespace_validates_under_current_contract() -> None:
    artifact = SourceArtifact.from_path(
        Path("tests/fixtures/doclang/ok_no_namespace.dclg"),
        source_form=SourceForm.DOCLANG_XML,
    )
    inventory, contract = inventory_source(artifact)
    assert inventory
    assert contract.upstream_version == "0.7.3"


def test_doclang_table_is_retained_but_not_primary() -> None:
    artifact = SourceArtifact.from_path(
        Path("tests/fixtures/doclang/ok_table_rectangular.dclg"),
        source_form=SourceForm.DOCLANG_XML,
    )
    outcome = ProductionIngestor().prepare(artifact)
    inventory = outcome.semantic.inventory
    table_ids = {
        item.item_id for item in inventory if item.classification in {ContentClass.TABLE, ContentClass.TABLE_CELL}
    }
    assert table_ids
    assert all(
        item.disposition.decision is not DispositionDecision.PRIMARY for item in inventory if item.item_id in table_ids
    )
    assert outcome.semantic.prepared_document.text == ""
