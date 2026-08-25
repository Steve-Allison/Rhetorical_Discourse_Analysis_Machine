from datetime import UTC, datetime

import pytest

from isanlp_rst.contracts.serialization import ingest_result_from_json
from isanlp_rst.ingest.contracts import (
    AnalysisStatus,
    CacheStatus,
    ExecutionReceipt,
    PreparationReceipt,
    ProductionAnalysisResult,
    SourceArtifact,
)


def _result() -> ProductionAnalysisResult:
    artifact = SourceArtifact.from_text("", source_name="empty.txt")
    receipt = PreparationReceipt(
        source_id=artifact.source_id,
        source_contract_digest="0" * 64,
        policy_digest="1" * 64,
        preparation_digest="2" * 64,
        subdivision_digest="3" * 64,
        model_digest="4" * 64,
        result_contract_version="1.0.0",
        inventory_count=0,
        disposition_count=0,
        inventory_coverage=1.0,
        primary_source_coverage=1.0,
        prepared_text_coverage=1.0,
        analysis_anchor_coverage=1.0,
    )
    return ProductionAnalysisResult(
        source=artifact.summary(),
        analysis_status=AnalysisStatus.EMPTY_PRIMARY_DISCOURSE,
        preparation_receipt=receipt,
        execution_receipt=ExecutionReceipt(
            run_id="run",
            started_at=datetime(2026, 8, 25, tzinfo=UTC),
            cache_status=CacheStatus.DISABLED,
        ),
    )


def test_result_round_trip_preserves_semantic_digest() -> None:
    result = _result()
    loaded = ingest_result_from_json(result.to_json())
    assert loaded.semantic_digest == result.semantic_digest


def test_result_rejects_integrity_mismatch() -> None:
    result = _result()
    payload = result.model_dump(mode="json")
    payload["semantic_digest"] = "f" * 64
    with pytest.raises(ValueError, match="semantic digest"):
        ProductionAnalysisResult.model_validate(payload)
