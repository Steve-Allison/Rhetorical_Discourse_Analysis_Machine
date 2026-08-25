from datetime import UTC, datetime
from pathlib import Path
from pathlib import PurePosixPath

import pytest

from isanlp_rst.contracts import OutputFormalismEnum, RstAnalysis, RstDocument
from isanlp_rst.ingest.cache import ProductionIngestCache
from isanlp_rst.ingest.contracts import (
    AnalysisStatus,
    CacheStatus,
    ExecutionReceipt,
    FailureStage,
    PreparationReceipt,
    ProductionAnalysisResult,
    ProductionIngestError,
    SourceArtifact,
)
from isanlp_rst.ingest.policy import AUTHORED_PROSE_V1
from isanlp_rst.ingest.service import ProductionIngestor
import isanlp_rst.ingest.service as service_module
from isanlp_rst.model_loading import ModelFile, ModelReleaseIdentity, ParserCapacity


class ImmutableParser:
    def __init__(self, *, release_id: str = "test-release", capacity: int = 512) -> None:
        self.analysis_capacity = ParserCapacity(unit="edu_count", maximum=capacity, source="cache-test")
        self.model_release_identity = ModelReleaseIdentity(
            release_id=release_id,
            manifest_sha256="a" * 64,
            runtime_contract="isanlp_rst.parser/test-v1",
            architecture="test",
            files=(
                ModelFile(
                    path=PurePosixPath("model.bin"),
                    role="weights",
                    size_bytes=1,
                    sha256="b" * 64,
                ),
            ),
            capacity=self.analysis_capacity,
        )

    def parse_document(self, document: RstDocument, output: str = "rst_tree") -> RstAnalysis:
        return RstAnalysis(
            document_id=document.document_id,
            formalism=OutputFormalismEnum(output),
            nodes=(),
            primary_edges=(),
        )


def _empty_result(*, cache_fingerprint: str) -> ProductionAnalysisResult:
    artifact = SourceArtifact.from_text("", source_name="empty.txt")
    return ProductionAnalysisResult(
        source=artifact.summary(),
        analysis_status=AnalysisStatus.EMPTY_PRIMARY_DISCOURSE,
        preparation_receipt=PreparationReceipt(
            source_id=artifact.source_id,
            source_contract_digest="0" * 64,
            policy_digest="1" * 64,
            preparation_digest="2" * 64,
            subdivision_digest="3" * 64,
            model_digest="4" * 64,
            inventory_count=0,
            disposition_count=0,
            inventory_coverage=1.0,
            primary_source_coverage=1.0,
            prepared_text_coverage=1.0,
            analysis_anchor_coverage=1.0,
            cache_fingerprint=cache_fingerprint,
        ),
        execution_receipt=ExecutionReceipt(
            run_id="run",
            started_at=datetime(2026, 8, 25, tzinfo=UTC),
            cache_status=CacheStatus.MISS,
        ),
    )


def test_cache_round_trip_verifies_semantic_payload(tmp_path: Path) -> None:
    cache = ProductionIngestCache(tmp_path)
    result = _empty_result(cache_fingerprint="a" * 64)
    cache.store("a" * 64, result)
    loaded = cache.load("a" * 64)
    assert loaded is not None
    assert loaded.semantic_digest == result.semantic_digest


def test_cache_corruption_is_an_actionable_failure(tmp_path: Path) -> None:
    cache = ProductionIngestCache(tmp_path)
    cache.store("b" * 64, _empty_result(cache_fingerprint="b" * 64))
    cache.path_for("b" * 64).write_text("{}", encoding="utf-8")
    with pytest.raises(ProductionIngestError) as raised:
        cache.load("b" * 64)
    assert raised.value.stage is FailureStage.CACHE
    assert raised.value.code == "corrupt_cache_entry"


def test_cache_identity_changes_for_every_analytical_dimension(monkeypatch: pytest.MonkeyPatch) -> None:
    artifact = SourceArtifact.from_text("", source_name="empty.txt")
    base = ProductionIngestor(parser=ImmutableParser()).analyse(artifact)
    base_fingerprint = base.preparation_receipt.cache_fingerprint
    assert base_fingerprint is not None

    variants = {
        ProductionIngestor(parser=ImmutableParser()).analyse(
            SourceArtifact.from_text("", source_name="renamed.txt")
        ).preparation_receipt.cache_fingerprint,
        ProductionIngestor(parser=ImmutableParser()).analyse(
            artifact,
            policy=AUTHORED_PROSE_V1.model_copy(update={"version": "2"}),
        ).preparation_receipt.cache_fingerprint,
        ProductionIngestor(parser=ImmutableParser(release_id="other-release")).analyse(
            artifact
        ).preparation_receipt.cache_fingerprint,
        ProductionIngestor(parser=ImmutableParser(capacity=256)).analyse(
            artifact
        ).preparation_receipt.cache_fingerprint,
    }
    monkeypatch.setattr(service_module, "INGEST_PIPELINE_VERSION", "2.0.0")
    variants.add(ProductionIngestor(parser=ImmutableParser()).analyse(artifact).preparation_receipt.cache_fingerprint)
    monkeypatch.setattr(service_module, "INGEST_SCHEMA_VERSION", "2.0.0")
    variants.add(ProductionIngestor(parser=ImmutableParser()).analyse(artifact).preparation_receipt.cache_fingerprint)

    assert None not in variants
    assert len(variants) == 6
    assert base_fingerprint not in variants


def test_cache_rejects_a_payload_stored_under_a_contradictory_key(tmp_path: Path) -> None:
    cache = ProductionIngestCache(tmp_path)
    requested = "c" * 64
    cache.path_for(requested).parent.mkdir(parents=True)
    cache.path_for(requested).write_text(
        _empty_result(cache_fingerprint="d" * 64).to_json(),
        encoding="utf-8",
    )

    with pytest.raises(ProductionIngestError) as raised:
        cache.load(requested)

    assert raised.value.stage is FailureStage.CACHE
    assert raised.value.code == "contradictory_cache_identity"


def test_interrupted_atomic_write_leaves_no_cache_entry_or_temporary_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cache = ProductionIngestCache(tmp_path)
    fingerprint = "e" * 64

    def interrupt_replace(*_args: object) -> None:
        raise OSError("simulated interrupted atomic replace")

    monkeypatch.setattr("isanlp_rst.ingest.cache.os.replace", interrupt_replace)
    with pytest.raises(OSError, match="simulated interrupted atomic replace"):
        cache.store(fingerprint, _empty_result(cache_fingerprint=fingerprint))

    assert not cache.path_for(fingerprint).exists()
    assert not tuple(cache.path_for(fingerprint).parent.glob("*.tmp"))
