"""Contract tests for executable eRST comparison evidence."""

from datetime import UTC, datetime
from pathlib import Path

from pydantic import ValidationError
import pytest

from isanlp_rst.contracts.erst import CorpusPartition
from research_harness.erst.contracts import (
    ChampionManifest,
    DocumentScore,
    EdgeDirection,
    EvaluationSetting,
    ExperimentMetrics,
    ExperimentProtocol,
    ExperimentRunReceipt,
    ExperimentRunStatus,
    ExperimentStage,
    ExperimentSystemSpec,
    MandatoryExperimentSystem,
    ResourceEvidence,
    RunFailure,
    SelectionDecision,
    SelectionGateName,
    SelectionGateResult,
    SelectionOutcome,
    SignalLocation,
    SignalMarkedExample,
)
from research_harness.erst.serialization import serialize_signal_marked_example

_HASH = "a" * 64
_REVISION = "b" * 40
_NOW = datetime(2026, 8, 25, 12, tzinfo=UTC)


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
                implementation=f"isanlp_rst.erst.systems.{system.value}",
                model_license="MIT" if system == MandatoryExperimentSystem.SIGNAL_RULE else "model-card",
                config_sha256=f"{index:x}" * 64,
            )
            for index, system in enumerate(MandatoryExperimentSystem, start=1)
        ),
    )


def _resource_evidence() -> ResourceEvidence:
    return ResourceEvidence(
        machine="Mac",
        operating_system="macOS",
        processor="Apple M5 Max",
        physical_memory_bytes=48 * 1024**3,
        device="mps",
        torch_version="2.13.0",
        transformers_version="5.15.1",
        thread_count=1,
        p50_latency_ms=10.0,
        p95_latency_ms=12.0,
        peak_rss_bytes=1024,
        mps_peak_allocated_bytes=512,
    )


def _successful_run(protocol: ExperimentProtocol) -> ExperimentRunReceipt:
    return ExperimentRunReceipt(
        run_id="structural-only-seed-17",
        protocol_sha256=protocol.protocol_sha256,
        system=MandatoryExperimentSystem.STRUCTURAL_ONLY,
        stage=ExperimentStage.SCREENING,
        status=ExperimentRunStatus.SUCCEEDED,
        seed=17,
        setting=EvaluationSetting.PREDICTED_PRIMARY_PREDICTED_SIGNAL,
        partitions=(CorpusPartition.DEV,),
        architecture_config_sha256="7" * 64,
        candidate_selection_sha256="8" * 64,
        split_manifest_sha256=protocol.split_manifest_sha256,
        started_at=_NOW,
        completed_at=_NOW,
        document_count=1,
        scored_document_count=1,
        candidate_count=8,
        execution_steps=3,
        checkpoint_sha256="9" * 64,
        predictions_sha256="a" * 64,
        scorer_output_sha256="b" * 64,
        metrics=ExperimentMetrics(
            span_f=0.4,
            direction_f=0.3,
            relation_f=0.2,
            full_f=0.18,
            ece=0.04,
            brier=0.2,
        ),
        document_scores=(DocumentScore(document_id="GUM_test", source_sha256="c" * 64, full_f=0.18),),
        resources=_resource_evidence(),
    )


def test_protocol_is_complete_hashed_and_test_isolated() -> None:
    protocol = _protocol()

    assert tuple(spec.system for spec in protocol.systems) == tuple(MandatoryExperimentSystem)
    assert protocol.training_partitions == (CorpusPartition.TRAIN, CorpusPartition.DEV)
    assert len(protocol.protocol_sha256) == 64
    assert ExperimentProtocol.model_validate_json(protocol.model_dump_json()) == protocol


def test_protocol_rejects_silently_dropped_system() -> None:
    protocol = _protocol()

    with pytest.raises(ValidationError, match="every mandatory system"):
        ExperimentProtocol.model_validate({**protocol.model_dump(), "systems": protocol.systems[:-1]})


def test_successful_run_requires_positive_complete_evidence() -> None:
    protocol = _protocol()
    receipt = _successful_run(protocol)

    assert len(receipt.receipt_sha256) == 64
    with pytest.raises(ValidationError, match="non-zero work"):
        ExperimentRunReceipt.model_validate({**receipt.model_dump(), "execution_steps": 0})
    with pytest.raises(ValidationError, match="artifact evidence"):
        ExperimentRunReceipt.model_validate({**receipt.model_dump(), "predictions_sha256": None})


def test_screening_run_cannot_access_test_partitions() -> None:
    receipt = _successful_run(_protocol())

    with pytest.raises(ValidationError, match="corpus boundary"):
        ExperimentRunReceipt.model_validate({**receipt.model_dump(), "partitions": (CorpusPartition.TEST,)})


def test_failed_run_retains_typed_evidence_without_blocking_other_systems() -> None:
    protocol = _protocol()
    receipt = ExperimentRunReceipt(
        run_id="qwen-incompatible",
        protocol_sha256=protocol.protocol_sha256,
        system=MandatoryExperimentSystem.QWEN3_DEDISCO,
        stage=ExperimentStage.SCREENING,
        status=ExperimentRunStatus.INCOMPATIBLE,
        seed=17,
        setting=EvaluationSetting.PREDICTED_PRIMARY_PREDICTED_SIGNAL,
        partitions=(CorpusPartition.TRAIN, CorpusPartition.DEV),
        architecture_config_sha256="d" * 64,
        candidate_selection_sha256="e" * 64,
        split_manifest_sha256=protocol.split_manifest_sha256,
        started_at=_NOW,
        completed_at=_NOW,
        document_count=1,
        scored_document_count=0,
        candidate_count=8,
        execution_steps=1,
        failure=RunFailure(
            failure_type="RuntimeCompatibilityError",
            message="Measured incompatibility",
            evidence_sha256="f" * 64,
            retryable=False,
        ),
    )

    assert receipt.status == ExperimentRunStatus.INCOMPATIBLE
    assert receipt.failure is not None


def test_champion_manifest_rejects_test_access() -> None:
    protocol = _protocol()

    with pytest.raises(ValidationError, match="cannot access test"):
        ChampionManifest(
            protocol_sha256=protocol.protocol_sha256,
            champion_system=MandatoryExperimentSystem.STRUCTURAL_ONLY,
            baseline_system=MandatoryExperimentSystem.ELECTRA,
            selected_config_sha256=_HASH,
            dev_run_receipts=(_HASH,),
            selected_checkpoint_receipt_sha256=_HASH,
            baseline_dev_run_receipts=("b" * 64,),
            baseline_checkpoint_receipt_sha256="b" * 64,
            electra_dev_run_receipts=("d" * 64,),
            electra_checkpoint_receipt_sha256="d" * 64,
            comparison_sha256=_HASH,
            mean_dev_full_f=0.2,
            created_at=_NOW,
            test_data_accessed=True,
        )


def test_selection_is_conjunctive_and_names_no_checkpoint_on_failure() -> None:
    gates = tuple(
        SelectionGateResult(
            gate=gate,
            passed=gate != SelectionGateName.DEV_FULL_IMPROVEMENT,
            evidence_sha256=_HASH,
            reason="measured result",
        )
        for gate in SelectionGateName
    )
    decision = SelectionDecision(
        outcome=SelectionOutcome.NO_SELECTION,
        protocol_sha256=_HASH,
        champion_sha256=_HASH,
        final_evaluation_sha256=_HASH,
        gates=gates,
    )

    assert decision.canonical_checkpoint_manifest_sha256 is None
    assert len(decision.decision_sha256) == 64


def test_signal_marked_serialization_is_model_neutral() -> None:
    example = SignalMarkedExample(
        relation_raw="elaboration-additional",
        same_path_relation_raw="joint-list",
        direction=EdgeDirection.RIGHT,
        head_edu_distance=2,
        source_text="because it rained",
        target_text="the match stopped",
        signal_location=SignalLocation.SOURCE,
        signal_start=0,
        signal_end=7,
        label=True,
    )

    assert serialize_signal_marked_example(example) == (
        "__label__True\telaboration additional ( joint-list ) right 2 : "
        "the match stopped << **because** it rained"
    )


def test_production_package_does_not_import_research_harness() -> None:
    production_root = Path(__file__).resolve().parents[2] / "isanlp_rst"
    importers = tuple(
        path.relative_to(production_root)
        for path in production_root.rglob("*.py")
        if "research_harness" in path.read_text(encoding="utf-8")
    )

    assert importers == ()
