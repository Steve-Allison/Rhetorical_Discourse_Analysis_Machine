"""Every source form retains its complete, classified source inventory."""

from pathlib import Path

import pytest

from rdam.ingest import ContentClass, DispositionDecision, ProductionIngestor, SourceArtifact, SourceForm
from rdam.ingest.prepare import inventory_source
from rdam.ingest.validation import validate_preparation_outcome
from tests.ingest.production_ingest.test_retained_structure import _archive_fixture


def source_case(form: SourceForm) -> tuple[SourceArtifact, set[str]]:
    """Small independently enumerable specimens, including retained table cells."""
    if form is SourceForm.TEXT:
        return SourceArtifact.from_text("First.\n\nSecond.", source_name="complete.txt"), {"text:document"}
    if form is SourceForm.EDUS:
        return SourceArtifact.from_edus(("First.", "Second."), source_name="complete.edus"), {"edu:0", "edu:1"}
    if form is SourceForm.DOCLING_JSON:
        return (
            SourceArtifact.from_path(Path("tests/fixtures/pipeline/merged-table.docling.json")),
            {"#/body", "#/texts/0", "#/tables/0", *(f"#/tables/0/data/table_cells/{i}" for i in range(5))},
        )
    if form is SourceForm.DOCLANG_ARCHIVE:
        data = _archive_fixture()
        expected = {"/doclang[1]", "/doclang[1]/heading[1]", "/doclang[1]/text[1]", "/doclang[1]/text[2]", "archive:media/figure.txt"}
        media_type = "application/vnd.doclang.archive+zip"
    elif form is SourceForm.DOCLANG_XML:
        data = b"<doclang><heading>Heading</heading><text>First.</text></doclang>"
        expected = {"/doclang[1]", "/doclang[1]/heading[1]", "/doclang[1]/text[1]"}
        media_type = "application/vnd.doclang+xml"
    elif form is SourceForm.MARKDOWN:
        data = b"# Heading\n\nFirst."
        expected = {"markdown:token:0", "markdown:token:3"}
        media_type = "text/markdown; charset=utf-8"
    else:
        raise AssertionError(f"Source form lacks an independently enumerated specimen: {form}")
    return SourceArtifact.from_bytes(data, source_form=form, source_name="complete", media_type=media_type), expected


@pytest.mark.parametrize("form", tuple(SourceForm))
def test_every_source_item_is_classified_dispositioned_and_accounted(form: SourceForm) -> None:
    source, expected = source_case(form)
    original, _ = inventory_source(source)
    outcome = ProductionIngestor().prepare(source)
    inventory = outcome.semantic.inventory
    assert {item.item_id for item in original} == expected
    assert {item.item_id for item in inventory} == expected
    assert len(inventory) == len(expected)
    assert all(isinstance(item.classification, ContentClass) for item in inventory)
    assert all(item.disposition.decision is not DispositionDecision.REJECTED_INVALID for item in inventory)
    assert {item.item_id: item.representation for item in inventory} == {
        item.item_id: item.representation for item in original
    }
    assert outcome.semantic.inventory_coverage.covered_units == len(expected)
    assert outcome.semantic.inventory_coverage.total_units == len(expected)
    assert outcome.semantic.primary_coverage.covered_units + outcome.semantic.retained_coverage.covered_units == len(expected)
    validate_preparation_outcome(outcome)
