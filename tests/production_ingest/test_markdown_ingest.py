from pathlib import Path

from isanlp_rst.ingest import SourceArtifact
from isanlp_rst.ingest.contracts import ContentClass
from isanlp_rst.ingest.prepare import inventory_source
from isanlp_rst.ingest.service import ProductionIngestor


FIXTURE = Path("tests/fixtures/markdown/gfm-rich.md")


def test_markdown_inventory_is_complete_before_policy() -> None:
    artifact = SourceArtifact.from_path(FIXTURE)
    inventory, _ = inventory_source(artifact)
    classes = {item.content_class for item in inventory}
    assert ContentClass.HEADING in classes
    assert ContentClass.PARAGRAPH in classes
    assert ContentClass.CODE in classes
    assert ContentClass.TABLE in classes
    assert ContentClass.RAW_MARKUP in classes


def test_markdown_default_primary_excludes_code_html_and_tables() -> None:
    artifact = SourceArtifact.from_path(FIXTURE)
    prepared = ProductionIngestor(parser=None).prepare(artifact)
    inventory, _ = inventory_source(artifact)
    primary_classes = {
        item.content_class for item in inventory if item.item_id in set(prepared.primary_item_ids)
    }
    assert ContentClass.CODE not in primary_classes
    assert ContentClass.RAW_MARKUP not in primary_classes
    assert ContentClass.TABLE not in primary_classes
    assert ContentClass.TABLE_CELL not in primary_classes
