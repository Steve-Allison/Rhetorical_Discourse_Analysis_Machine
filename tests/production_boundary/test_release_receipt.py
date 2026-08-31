"""Strict canonical release-receipt and evidence lifecycle tests."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from tools.production_boundary.contracts import (
    BuildIdentity,
    CheckStatus,
    EvidenceRecord,
    EvidenceState,
    GateResult,
    PreparationPerformanceCase,
    PreparationPerformanceEvidence,
    ReleaseArtifactIdentity,
    ReleaseContractIdentity,
    ReleaseReceipt,
    SourceReleaseIdentity,
    SourceReleaseRecord,
    VerificationCheck,
    canonical_record_bytes,
)


IDENTITY = "a" * 64
COMMIT = "b" * 40
TREE = "c" * 40
NOW = datetime(2026, 8, 29, tzinfo=UTC)


def _check() -> VerificationCheck:
    return VerificationCheck(
        check_id="pytest.full",
        status=CheckStatus.PASSED,
        command=("pixi", "run", "test"),
        tool_identity="pytest 9.1.1",
        evidence_path="specs/004-production-api-contract/evidence/source-release-gates.json",
        evidence_sha256=IDENTITY,
        completed_at=NOW,
    )


def _gate() -> GateResult:
    return GateResult(
        check_id="pytest.focused",
        status=CheckStatus.PASSED,
        command=("pixi", "run", "production-api-contract"),
        tool_identity="pytest 9.1.1",
        output_sha256=IDENTITY,
        completed_at=NOW,
        summary="all focused checks passed",
    )


def test_pre_source_evidence_rejects_future_commit_identity() -> None:
    with pytest.raises(ValidationError, match="future commit"):
        EvidenceRecord(
            schema_name="isanlp_rst.release_evidence.pre_release_quality",
            state=EvidenceState.PRE_SOURCE,
            created_at=NOW,
            source_commit=COMMIT,
            checks=(_gate(),),
        )


def test_performance_evidence_requires_exactly_one_warm_up_and_five_runs() -> None:
    measurements = PreparationPerformanceEvidence(
        cases=(
            PreparationPerformanceCase(
                character_count=100_000,
                threshold_seconds=2.0,
                warmup_seconds=0.1,
                run_seconds=(0.1, 0.2, 0.1, 0.2, 0.1),
            ),
        ),
    )
    record = EvidenceRecord(
        schema_name="isanlp_rst.release_evidence.performance",
        state=EvidenceState.PRE_SOURCE,
        created_at=NOW,
        checks=(_gate(),),
        preparation_performance=measurements,
    )
    assert record.preparation_performance is not None
    assert record.preparation_performance.passed

    with pytest.raises(ValidationError, match="only performance evidence"):
        EvidenceRecord(
            schema_name="isanlp_rst.release_evidence.pre_release_quality",
            state=EvidenceState.PRE_SOURCE,
            created_at=NOW,
            checks=(_gate(),),
            preparation_performance=measurements,
        )


def test_source_release_record_is_versioned_canonical_and_source_selected() -> None:
    record = SourceReleaseRecord(
        source=SourceReleaseIdentity(
            commit=COMMIT,
            tree=TREE,
            archive_sha256=IDENTITY,
            source_date_epoch=1_787_958_400,
        )
    )
    payload = canonical_record_bytes(record)
    assert SourceReleaseRecord.model_validate_json(payload) == record
    assert record.state is EvidenceState.SOURCE_SELECTED
    with pytest.raises(ValidationError, match="Input should be"):
        SourceReleaseRecord.model_validate(
            record.model_dump(mode="json") | {"state": EvidenceState.PRE_SOURCE}
        )
    with pytest.raises(ValidationError, match="Extra inputs"):
        SourceReleaseRecord.model_validate(
            record.model_dump(mode="json") | {"candidate_commit": COMMIT}
        )


def test_release_receipt_is_closed_canonical_and_complete() -> None:
    receipt = ReleaseReceipt(
        contract=ReleaseContractIdentity(),
        source=SourceReleaseIdentity(
            commit=COMMIT,
            tree=TREE,
            archive_sha256=IDENTITY,
            source_date_epoch=1_787_958_400,
        ),
        build=BuildIdentity(
            python_implementation="CPython",
            python_version="3.14.0",
            build_frontend_version="1.6.0",
            build_backend_version="1.32.0",
            platform="macOS-arm64",
            lock_sha256=IDENTITY,
            deterministic_environment=(("SOURCE_DATE_EPOCH", "1787958400"),),
            provenance_sha256=IDENTITY,
        ),
        artifacts=(
            ReleaseArtifactIdentity(
                filename="isanlp_rst-5.0.0-py3-none-any.whl",
                kind="wheel",
                size_bytes=10,
                sha256=IDENTITY,
                wheel_tags=("py3-none-any",),
                build_report_sha256=IDENTITY,
            ),
            ReleaseArtifactIdentity(
                filename="isanlp_rst-5.0.0.tar.gz",
                kind="sdist",
                size_bytes=10,
                sha256=IDENTITY,
                build_report_sha256=IDENTITY,
            ),
        ),
        verification=(_check(),),
    )
    assert canonical_record_bytes(receipt).startswith(b'{"artifacts"')
    with pytest.raises(ValidationError, match="Extra inputs"):
        ReleaseReceipt.model_validate(receipt.model_dump() | {"future": True})


def test_release_receipt_rejects_failed_or_incomplete_verification() -> None:
    failed = _check().model_copy(update={"status": CheckStatus.FAILED})
    with pytest.raises(ValidationError, match="present and passed"):
        ReleaseReceipt(
            contract=ReleaseContractIdentity(),
            source=SourceReleaseIdentity(
                commit=COMMIT,
                tree=TREE,
                archive_sha256=IDENTITY,
                source_date_epoch=1,
            ),
            build=BuildIdentity(
                python_implementation="CPython",
                python_version="3.14",
                build_frontend_version="1.6.0",
                build_backend_version="1.32.0",
                platform="test",
                lock_sha256=IDENTITY,
                deterministic_environment=(),
                provenance_sha256=IDENTITY,
            ),
            artifacts=(
                ReleaseArtifactIdentity(
                    filename="a.whl",
                    kind="wheel",
                    size_bytes=1,
                    sha256=IDENTITY,
                    build_report_sha256=IDENTITY,
                ),
                ReleaseArtifactIdentity(
                    filename="a.tar.gz",
                    kind="sdist",
                    size_bytes=1,
                    sha256=IDENTITY,
                    build_report_sha256=IDENTITY,
                ),
            ),
            verification=(failed,),
        )
