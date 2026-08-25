"""Execution-path tests for the isolated eRST technology-comparison harness."""

from pathlib import Path

import pytest

from isanlp_rst.contracts.erst import CorpusPartition
from research_harness.erst.contracts import (
    DocumentScore,
    EvaluationSetting,
    ExperimentDataIdentity,
    ExperimentDocumentIdentity,
    ExperimentMetrics,
    ExperimentProtocol,
    ExperimentRunStatus,
    ExperimentStage,
    ExperimentSystemSpec,
    MandatoryExperimentSystem,
)
from research_harness.erst.runner import (
    ExperimentExecutionError,
    ExperimentRunRequest,
    ExperimentRunner,
    PreparedExperimentData,
    SystemExecutionResult,
    SystemRunContext,
)

_HASH = "a" * 64
_REVISION = "b" * 40


def _protocol() -> ExperimentProtocol:
    return ExperimentProtocol(
        corpus_revision=_REVISION,
        environment_lock_sha256="e" * 64,
        harness_source_sha256="0" * 64,
        production_source_sha256="f" * 64,
        corpus_receipt_sha256=_HASH,
        split_manifest_sha256="1" * 64,
        candidate_schema_sha256="2" * 64,
        signal_detector_sha256="3" * 64,
        raw_relation_inventory_sha256="4" * 64,
        ontology_mapping_sha256="5" * 64,
        decoder_config_sha256="6" * 64,
        systems=tuple(
            ExperimentSystemSpec(
                system=system,
                implementation=f"research_harness.erst.systems.{system.value}",
                model_license="test",
                config_sha256=f"{index:x}" * 64,
            )
            for index, system in enumerate(MandatoryExperimentSystem, start=1)
        ),
    )


def _data(protocol: ExperimentProtocol) -> PreparedExperimentData[tuple[str, ...]]:
    identity = ExperimentDataIdentity(
        split_manifest_sha256=protocol.split_manifest_sha256,
        candidate_selection_sha256="7" * 64,
        partitions=(CorpusPartition.DEV,),
        documents=(
            ExperimentDocumentIdentity(
                document_id="GUM_test_document",
                source_sha256="8" * 64,
                partition=CorpusPartition.DEV,
                candidate_count=2,
            ),
        ),
        scored_document_ids=("GUM_test_document",),
        candidate_count=2,
    )
    return PreparedExperimentData(identity=identity, payload=("candidate-1", "candidate-2"))


def _request(run_id: str) -> ExperimentRunRequest:
    return ExperimentRunRequest(
        run_id=run_id,
        system=MandatoryExperimentSystem.STRUCTURAL_ONLY,
        stage=ExperimentStage.SCREENING,
        seed=17,
        setting=EvaluationSetting.PREDICTED_PRIMARY_PREDICTED_SIGNAL,
        partitions=(CorpusPartition.DEV,),
        device="cpu",
    )


class SuccessfulAdapter:
    """Synthetic system proving the shared runner without private corpus access."""

    system = MandatoryExperimentSystem.STRUCTURAL_ONLY
    architecture_config_sha256 = "2" * 64

    def execute(self, context: SystemRunContext[tuple[str, ...]]) -> SystemExecutionResult:
        (context.run_directory / "checkpoint.bin").write_bytes(b"checkpoint")
        (context.run_directory / "predictions.json").write_text("{}\n", encoding="utf-8")
        (context.run_directory / "scores.json").write_text("{}\n", encoding="utf-8")
        return SystemExecutionResult(
            execution_steps=2,
            checkpoint_path="checkpoint.bin",
            predictions_path="predictions.json",
            scorer_output_path="scores.json",
            metrics=ExperimentMetrics(
                span_f=0.4,
                direction_f=0.3,
                relation_f=0.2,
                full_f=0.18,
                ece=0.04,
                brier=0.2,
            ),
            document_scores=(
                DocumentScore(
                    document_id="GUM_test_document",
                    source_sha256="8" * 64,
                    full_f=0.18,
                ),
            ),
            latency_samples_ms=(4.0, 5.0, 6.0),
        )


class IncompatibleAdapter:
    """Synthetic measured incompatibility proving durable unsuccessful evidence."""

    system = MandatoryExperimentSystem.STRUCTURAL_ONLY
    architecture_config_sha256 = "2" * 64

    def execute(self, context: SystemRunContext[tuple[str, ...]]) -> SystemExecutionResult:
        del context
        raise ExperimentExecutionError(
            failure_type="DeviceCompatibilityError",
            message="measured device incompatibility",
            evidence=b"verified incompatible",
            incompatible=True,
            execution_steps=1,
        )


def test_runner_persists_success_and_failure_in_one_verified_index(tmp_path: Path) -> None:
    protocol = _protocol()
    data = _data(protocol)
    runner = ExperimentRunner[tuple[str, ...]](protocol, tmp_path / "experiment")

    succeeded = runner.run(SuccessfulAdapter(), _request("success-17"), data)
    incompatible = runner.run(IncompatibleAdapter(), _request("incompatible-17"), data)
    index = runner.index_store.load_verified()

    assert succeeded.status == ExperimentRunStatus.SUCCEEDED
    assert incompatible.status == ExperimentRunStatus.INCOMPATIBLE
    assert tuple(entry.status for entry in index.entries) == (
        ExperimentRunStatus.SUCCEEDED,
        ExperimentRunStatus.INCOMPATIBLE,
    )
    assert len(index.index_sha256) == 64


def test_runner_rejects_data_from_a_different_split(tmp_path: Path) -> None:
    protocol = _protocol()
    data = _data(protocol)
    wrong_identity = ExperimentDataIdentity.model_validate(
        {**data.identity.model_dump(), "split_manifest_sha256": "9" * 64, "identity_sha256": ""}
    )
    runner = ExperimentRunner[tuple[str, ...]](protocol, tmp_path / "experiment")

    with pytest.raises(ValueError, match="different split manifest"):
        runner.run(
            SuccessfulAdapter(),
            _request("wrong-split-17"),
            PreparedExperimentData(identity=wrong_identity, payload=data.payload),
        )


def test_index_verification_detects_receipt_tampering(tmp_path: Path) -> None:
    protocol = _protocol()
    runner = ExperimentRunner[tuple[str, ...]](protocol, tmp_path / "experiment")
    runner.run(SuccessfulAdapter(), _request("tamper-17"), _data(protocol))
    receipt_path = tmp_path / "experiment" / "receipts" / "tamper-17.json"
    receipt_path.write_text("{}\n", encoding="utf-8")

    with pytest.raises(ValueError):
        runner.index_store.load_verified()
