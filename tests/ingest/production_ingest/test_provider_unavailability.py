"""Typed provider, format, cache, and persistence unavailability."""

import pytest

from rdam.ingest import (
    LifecycleStage,
    ProductionIngestError,
    ProductionIngestor,
    SourceArtifact,
    SourceForm,
)


def test_non_empty_analysis_without_parser_is_typed_unavailable() -> None:
    with pytest.raises(ProductionIngestError) as raised:
        ProductionIngestor().analyse(
            SourceArtifact.from_text("Non-empty.", source_name="source.txt")
        )
    assert raised.value.failure.failed_stage is LifecycleStage.INFERENCE
    assert raised.value.failure.code == "parser_not_configured"


def test_missing_optional_format_distribution_is_typed_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = SourceArtifact.from_bytes(
        b"# Heading\n\nText.",
        source_form=SourceForm.MARKDOWN,
        source_name="source.md",
        media_type="text/markdown; charset=utf-8",
    )

    def unavailable(_source: object) -> object:
        # A real missing-adapter import always carries the module name; a
        # nameless ModuleNotFoundError proves nothing about any distribution
        # and now classifies as an internal failure instead.
        raise ModuleNotFoundError("PRIVATE module import detail", name="markdown_it")

    monkeypatch.setattr("rdam.ingest.prepare.inventory_source", unavailable)
    with pytest.raises(ProductionIngestError) as raised:
        ProductionIngestor().prepare(source)
    assert raised.value.failure.failed_stage is LifecycleStage.CLASSIFICATION
    assert raised.value.failure.code == "source_adapter_distribution_unavailable"
    assert "PRIVATE" not in str(raised.value)
    assert isinstance(raised.value.__cause__, ModuleNotFoundError)
