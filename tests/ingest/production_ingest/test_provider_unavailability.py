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


def test_missing_doclang_adapter_distribution_is_typed_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = SourceArtifact.from_bytes(
        b"<doclang><text>Text.</text></doclang>",
        source_form=SourceForm.DOCLANG_XML,
        source_name="source.dclg",
        media_type="application/vnd.doclang+xml",
    )

    def unavailable(_source: object) -> object:
        # A real missing-adapter import always carries the module name; a
        # nameless ModuleNotFoundError proves nothing about any distribution
        # and now classifies as an internal failure instead.
        raise ModuleNotFoundError("PRIVATE module import detail", name="dclq")

    monkeypatch.setattr("rdam.ingest.prepare.inventory_source", unavailable)
    with pytest.raises(ProductionIngestError) as raised:
        ProductionIngestor().prepare(source)
    assert raised.value.failure.failed_stage is LifecycleStage.CLASSIFICATION
    assert raised.value.failure.code == "source_adapter_distribution_unavailable"
    assert "PRIVATE" not in str(raised.value)
    assert isinstance(raised.value.__cause__, ModuleNotFoundError)
