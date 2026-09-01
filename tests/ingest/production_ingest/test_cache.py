"""Validated, identity-bound, atomic v2 outcome caching."""

from pathlib import Path

import pytest

from isanlp_rst.ingest import (
    CacheStatus,
    ProductionIngestError,
    ProductionIngestor,
    SourceArtifact,
)
from isanlp_rst.ingest.cache import ProductionIngestCache
from isanlp_rst.ingest.contracts.failure import FailureCategory, LifecycleStage, Retryability

from .conftest import ParserBuilder


def test_cache_round_trip_binds_request_result_and_entry_identities(
    parser_builder: ParserBuilder,
    tmp_path: Path,
) -> None:
    ingestor = ProductionIngestor(parser=parser_builder())
    source = SourceArtifact.from_text("First. Second.", source_name="cache.txt")
    written = ingestor.analyse(source, cache_directory=tmp_path)
    hit = ingestor.analyse(source, cache_directory=tmp_path)

    assert written.execution.cache_status is CacheStatus.WRITTEN
    assert hit.execution.cache_status is CacheStatus.HIT
    assert written.execution.cache_entry_identity == hit.execution.cache_entry_identity
    assert written.semantic == hit.semantic
    assert written.semantic_digest == hit.semantic_digest
    assert written.execution != hit.execution


def test_cache_corruption_is_typed_and_does_not_fall_back_to_inference(
    parser_builder: ParserBuilder,
    tmp_path: Path,
) -> None:
    ingestor = ProductionIngestor(parser=parser_builder())
    source = SourceArtifact.from_text("First. Second.", source_name="cache.txt")
    written = ingestor.analyse(source, cache_directory=tmp_path)
    request_identity = written.semantic.request.semantic_digest
    assert request_identity is not None
    cache = ProductionIngestCache(tmp_path)
    cache.path_for(request_identity).write_text("{}", encoding="utf-8")

    with pytest.raises(ProductionIngestError) as raised:
        ingestor.analyse(source, cache_directory=tmp_path)
    assert raised.value.failure.code == "corrupt_cache_entry"
    assert raised.value.failure.category is FailureCategory.CORRUPT_CACHE_ENTRY
    assert raised.value.failure.retryability is Retryability.NOT_RETRYABLE


def test_cache_read_io_error_is_unknown_not_corrupt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ingestor = ProductionIngestor()
    source = SourceArtifact.from_text("  \n", source_name="empty.txt")
    ingestor.analyse(source, cache_directory=tmp_path)

    original_read_bytes = Path.read_bytes

    def unreadable(self: Path) -> bytes:
        if tmp_path in self.parents:
            raise OSError("private operating-system detail")
        return original_read_bytes(self)

    monkeypatch.setattr(Path, "read_bytes", unreadable)
    with pytest.raises(ProductionIngestError) as raised:
        ingestor.analyse(source, cache_directory=tmp_path)
    assert raised.value.failure.failed_stage is LifecycleStage.CACHE_RETRIEVAL
    assert raised.value.failure.code == "cache_read_failed"
    assert raised.value.failure.category is FailureCategory.INTERNAL_PROCESSING_FAILURE
    assert raised.value.failure.retryability is Retryability.UNKNOWN
    assert "private operating-system detail" not in str(raised.value)


def test_interrupted_atomic_write_leaves_no_success_or_temporary_entry(
    parser_builder: ParserBuilder,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ingestor = ProductionIngestor(parser=parser_builder())
    source = SourceArtifact.from_text("First. Second.", source_name="cache.txt")

    def interrupt_replace(*_args: object) -> None:
        raise OSError("private operating-system detail")

    monkeypatch.setattr("isanlp_rst.ingest.cache.os.replace", interrupt_replace)
    with pytest.raises(ProductionIngestError) as raised:
        ingestor.analyse(source, cache_directory=tmp_path)
    assert raised.value.failure.code == "cache_persistence_failed"
    assert "private operating-system detail" not in str(raised.value)
    assert not tuple(tmp_path.rglob("*.json"))
    assert not tuple(tmp_path.rglob("*.tmp"))


def test_empty_primary_outcome_is_cacheable_without_a_parser(tmp_path: Path) -> None:
    ingestor = ProductionIngestor()
    source = SourceArtifact.from_text("  \n", source_name="empty.txt")
    written = ingestor.analyse(source, cache_directory=tmp_path)
    hit = ingestor.analyse(source, cache_directory=tmp_path)
    assert written.execution.cache_status is CacheStatus.WRITTEN
    assert hit.execution.cache_status is CacheStatus.HIT
    assert written.semantic_digest == hit.semantic_digest
