from pathlib import Path

from rdam.rst.ingest import SourceArtifact
from rdam.rst.ingest.contracts import ContentClass, DispositionDecision
from rdam.rst.ingest.prepare import inventory_source
from rdam.rst.ingest.service import ProductionIngestor


FIXTURE = Path("tests/fixtures/markdown/gfm-rich.md")


def test_markdown_inventory_is_complete_before_policy() -> None:
    artifact = SourceArtifact.from_path(FIXTURE)
    inventory, _ = inventory_source(artifact)
    classes = {item.classification for item in inventory}
    assert ContentClass.HEADING in classes
    assert ContentClass.PARAGRAPH in classes
    assert ContentClass.CODE in classes
    assert ContentClass.TABLE in classes
    assert ContentClass.RAW_MARKUP in classes


def test_markdown_default_primary_excludes_code_html_and_tables() -> None:
    artifact = SourceArtifact.from_path(FIXTURE)
    outcome = ProductionIngestor().prepare(artifact)
    primary_classes = {
        item.classification
        for item in outcome.semantic.inventory
        if item.disposition.decision is DispositionDecision.PRIMARY
    }
    assert ContentClass.CODE not in primary_classes
    assert ContentClass.RAW_MARKUP not in primary_classes
    assert ContentClass.TABLE not in primary_classes
    assert ContentClass.TABLE_CELL not in primary_classes
