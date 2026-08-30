import pytest

from isanlp_rst.ingest import ProductionIngestError, ProductionIngestor, SourceArtifact, SourceForm
from isanlp_rst.ingest.contracts.failure import FailureCategory, LifecycleStage


def test_invalid_doclang_is_a_text_safe_typed_failure() -> None:
    private_text = "private malformed paragraph"
    artifact = SourceArtifact.from_bytes(
        f"<doclang><text>{private_text}</doclang>".encode(),
        source_form=SourceForm.DOCLANG_XML,
        source_name="invalid.dclg",
        media_type="application/vnd.doclang+xml",
    )
    with pytest.raises(ProductionIngestError) as raised:
        ProductionIngestor(parser=None).prepare(artifact)
    assert raised.value.failure.failed_stage is LifecycleStage.CLASSIFICATION
    assert raised.value.failure.category is FailureCategory.MALFORMED_INPUT
    assert raised.value.failure.code == "source_classification_failed"
    assert private_text not in str(raised.value)
    assert private_text not in repr(raised.value)


def test_invalid_doclang_archive_never_returns_a_partial_preparation() -> None:
    artifact = SourceArtifact.from_bytes(
        b"not-a-zip",
        source_form=SourceForm.DOCLANG_ARCHIVE,
        source_name="invalid.dclx",
        media_type="application/vnd.doclang.archive+zip",
    )
    with pytest.raises(ProductionIngestError) as raised:
        ProductionIngestor(parser=None).prepare(artifact)
    assert raised.value.failure.failed_stage is LifecycleStage.CLASSIFICATION
    assert raised.value.failure.category is FailureCategory.MALFORMED_INPUT
    assert raised.value.failure.code == "source_classification_failed"
