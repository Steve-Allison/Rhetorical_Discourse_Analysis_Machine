"""Validated, identity-bound, atomic v2 outcome caching."""

import json
from pathlib import Path

import pytest

from rdam.ingest import (
    CacheStatus,
    ProductionIngestError,
    ProductionIngestor,
    SourceArtifact,
)
from rdam.ingest.cache import ProductionIngestCache
from rdam.ingest.contracts.failure import FailureCategory, LifecycleStage, Retryability

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
    assert raised.value.failure.category is FailureCategory.PERSISTENCE_FAILURE
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

    monkeypatch.setattr("rdam.ingest.cache.os.replace", interrupt_replace)
    with pytest.raises(ProductionIngestError) as raised:
        ingestor.analyse(source, cache_directory=tmp_path)
    assert raised.value.failure.code == "cache_persistence_failed"
    assert "private operating-system detail" not in str(raised.value)
    assert not tuple(tmp_path.rglob("*.json"))
    assert not tuple(tmp_path.rglob("*.tmp"))


def test_tampered_semantic_content_fails_digest_verification_on_load(
    parser_builder: ParserBuilder,
    tmp_path: Path,
) -> None:
    ingestor = ProductionIngestor(parser=parser_builder())
    source = SourceArtifact.from_text("First. Second.", source_name="cache.txt")
    written = ingestor.analyse(source, cache_directory=tmp_path)
    request_identity = written.semantic.request.semantic_digest
    assert request_identity is not None
    cache = ProductionIngestCache(tmp_path)
    path = cache.path_for(request_identity)
    payload = json.loads(path.read_text(encoding="utf-8"))
    recorded = payload["semantic"]["cache_request_identity"]["hex_digest"]
    payload["semantic"]["cache_request_identity"]["hex_digest"] = (
        ("0" if recorded[0] != "0" else "1") + recorded[1:]
    )
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ProductionIngestError) as raised:
        ingestor.analyse(source, cache_directory=tmp_path)
    assert raised.value.failure.code == "corrupt_cache_entry"
    assert raised.value.failure.retryability is Retryability.NOT_RETRYABLE


def test_entry_copied_under_a_foreign_key_is_a_typed_identity_contradiction(
    parser_builder: ParserBuilder,
    tmp_path: Path,
) -> None:
    ingestor = ProductionIngestor(parser=parser_builder())
    source = SourceArtifact.from_text("First. Second.", source_name="cache.txt")
    written = ingestor.analyse(source, cache_directory=tmp_path)
    request_identity = written.semantic.request.semantic_digest
    assert request_identity is not None
    cache = ProductionIngestCache(tmp_path)
    foreign = request_identity.model_copy(
        update={
            "hex_digest": (
                ("0" if request_identity.hex_digest[0] != "0" else "1")
                + request_identity.hex_digest[1:]
            )
        }
    )
    foreign_path = cache.path_for(foreign)
    foreign_path.parent.mkdir(parents=True, exist_ok=True)
    foreign_path.write_bytes(cache.path_for(request_identity).read_bytes())

    with pytest.raises(ProductionIngestError) as raised:
        cache.load(foreign)
    assert raised.value.failure.code == "contradictory_cache_identity"


def test_policy_change_rekeys_the_cache_instead_of_false_hitting(
    parser_builder: ParserBuilder,
    tmp_path: Path,
) -> None:
    from rdam.ingest.contracts.analysis import AnalysisPolicy, MarkerRefinementMode
    from rdam.ingest.service import DEFAULT_ANALYSIS_POLICY

    ingestor = ProductionIngestor(parser=parser_builder())
    source = SourceArtifact.from_text("First. Second.", source_name="cache.txt")
    default_written = ingestor.analyse(source, cache_directory=tmp_path)
    variant_policy = AnalysisPolicy.model_validate(
        {
            **DEFAULT_ANALYSIS_POLICY.model_dump(exclude={"semantic_digest"}),
            "marker_refinement": MarkerRefinementMode.DISABLED,
        }
    )
    variant_written = ingestor.analyse(
        source, analysis_policy=variant_policy, cache_directory=tmp_path
    )
    assert default_written.execution.cache_status is CacheStatus.WRITTEN
    assert variant_written.execution.cache_status is CacheStatus.WRITTEN
    assert (
        default_written.semantic.request.semantic_digest
        != variant_written.semantic.request.semantic_digest
    )


def test_empty_primary_outcome_is_cacheable_without_a_parser(tmp_path: Path) -> None:
    ingestor = ProductionIngestor()
    source = SourceArtifact.from_text("  \n", source_name="empty.txt")
    written = ingestor.analyse(source, cache_directory=tmp_path)
    hit = ingestor.analyse(source, cache_directory=tmp_path)
    assert written.execution.cache_status is CacheStatus.WRITTEN
    assert hit.execution.cache_status is CacheStatus.HIT
    assert written.semantic_digest == hit.semantic_digest
