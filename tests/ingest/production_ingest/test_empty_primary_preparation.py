"""Successful empty and retained-only preparation states."""

import pytest

from rdam.ingest import ProductionIngestor, SourceArtifact, SourceForm


@pytest.mark.parametrize("text", ("", "   \n\t"))
def test_empty_or_whitespace_source_prepares_successfully(text: str) -> None:
    outcome = ProductionIngestor().prepare(SourceArtifact.from_text(text, source_name="empty.txt"))
    assert outcome.semantic.prepared_document.text == ""
    assert outcome.semantic.prepared_document.segments == ()
    assert outcome.semantic.inventory_coverage.covered_units == len(outcome.semantic.inventory)
    assert outcome.semantic.mapping_coverage.covered_units == 0
    assert outcome.semantic.mapping_coverage.total_units == 0
    assert [warning.value for warning in outcome.semantic.warnings] == [
        "empty_submitted_content"
    ]


def test_valid_retained_only_source_is_not_misclassified_as_invalid() -> None:
    source = SourceArtifact.from_bytes(
        b"![Diagram](diagram.png)",
        source_form=SourceForm.MARKDOWN,
        source_name="retained.md",
        media_type="text/markdown; charset=utf-8",
    )
    outcome = ProductionIngestor().prepare(source)
    assert outcome.semantic.prepared_document.text == ""
    assert outcome.retained_items
    assert all(item.disposition.retained for item in outcome.semantic.inventory)
    assert [warning.value for warning in outcome.semantic.warnings] == [
        "retained_only_source"
    ]
