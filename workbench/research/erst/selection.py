"""Fail-closed champion freezing, final evaluation, and checkpoint selection."""

from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import secrets

from pydantic import BaseModel, ConfigDict, Field, model_validator

from isanlp_rst.contracts.erst import CorpusPartition
from workbench.research.erst.contracts import (
    ChampionManifest,
    ExperimentProtocol,
    ExperimentRunReceipt,
    ExperimentRunStatus,
    ExperimentStage,
    FinalEvaluationReceipt,
    MandatoryExperimentSystem,
    SelectionDecision,
    SelectionGateName,
    SelectionGateResult,
    SelectionOutcome,
    StatisticalComparison,
)

_SHA256_PATTERN = r"^[0-9a-f]{64}$"


def _canonical_sha256(value: object) -> str:
    encoded = json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode()
    return hashlib.sha256(encoded).hexdigest()


class CpuMpsParityEvidence(BaseModel):
    """Numerical and decoded-graph equivalence measured on identical candidates."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    cpu_receipt_sha256: str = Field(pattern=_SHA256_PATTERN)
    mps_receipt_sha256: str = Field(pattern=_SHA256_PATTERN)
    max_probability_delta: float = Field(ge=0.0)
    decoded_graphs_equal: bool
    tolerance: float = Field(gt=0.0)
    evidence_sha256: str = ""

    @model_validator(mode="after")
    def validate_evidence(self) -> "CpuMpsParityEvidence":
        expected = _canonical_sha256(self.model_dump(mode="json", exclude={"evidence_sha256"}))
        if self.evidence_sha256 and self.evidence_sha256 != expected:
            raise ValueError("CPU/MPS parity evidence hash does not match canonical content")
        object.__setattr__(self, "evidence_sha256", expected)
        return self


class TiedSystemEfficiencyEvidence(BaseModel):
    """Proof that the selected system is fastest/smallest among statistical ties."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    selected_system: MandatoryExperimentSystem
    tied_systems: tuple[MandatoryExperimentSystem, ...] = Field(min_length=1)
    selected_is_fastest_and_smallest: bool
    evidence_sha256: str = ""

    @model_validator(mode="after")
    def validate_evidence(self) -> "TiedSystemEfficiencyEvidence":
        if self.selected_system not in self.tied_systems:
            raise ValueError("selected system must be a member of the measured efficiency tie")
        expected = _canonical_sha256(self.model_dump(mode="json", exclude={"evidence_sha256"}))
        if self.evidence_sha256 and self.evidence_sha256 != expected:
            raise ValueError("efficiency evidence hash does not match canonical content")
        object.__setattr__(self, "evidence_sha256", expected)
        return self


class SelectionMeasurements(BaseModel):
    """All numerical inputs used to evaluate the ten conjunctive gates."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    champion_dev_full_f: float = Field(ge=0.0, le=1.0)
    baseline_dev_full_f: float = Field(ge=0.0, le=1.0)
    champion_test_span_f: float = Field(ge=0.0, le=1.0)
    champion_test_direction_f: float = Field(ge=0.0, le=1.0)
    champion_test_relation_f: float = Field(ge=0.0, le=1.0)
    champion_test_full_f: float = Field(ge=0.0, le=1.0)
    champion_test_ece: float = Field(ge=0.0, le=1.0)
    champion_test_brier: float = Field(ge=0.0, le=1.0)
    baseline_test_span_f: float = Field(ge=0.0, le=1.0)
    baseline_test_direction_f: float = Field(ge=0.0, le=1.0)
    baseline_test_relation_f: float = Field(ge=0.0, le=1.0)
    baseline_test_full_f: float = Field(ge=0.0, le=1.0)
    baseline_test_brier: float = Field(ge=0.0, le=1.0)
    champion_peak_rss_bytes: int = Field(gt=0)
    champion_mps_p95_latency_ms: float = Field(gt=0.0)
    electra_mps_p95_latency_ms: float = Field(gt=0.0)
    measurements_sha256: str = ""

    @model_validator(mode="after")
    def validate_measurements(self) -> "SelectionMeasurements":
        expected = _canonical_sha256(self.model_dump(mode="json", exclude={"measurements_sha256"}))
        if self.measurements_sha256 and self.measurements_sha256 != expected:
            raise ValueError("selection measurement hash does not match canonical content")
        object.__setattr__(self, "measurements_sha256", expected)
        return self


class CheckpointSelectionCandidateManifest(BaseModel):
    """Exact dev-selected source artifacts from which a production bundle can be built."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    protocol_sha256: str = Field(pattern=_SHA256_PATTERN)
    champion_sha256: str = Field(pattern=_SHA256_PATTERN)
    system: MandatoryExperimentSystem
    source_receipt_sha256: str = Field(pattern=_SHA256_PATTERN)
    source_checkpoint_sha256: str = Field(pattern=_SHA256_PATTERN)
    calibration_sha256: str = Field(pattern=_SHA256_PATTERN)
    raw_relation_inventory_sha256: str = Field(pattern=_SHA256_PATTERN)
    manifest_sha256: str = ""

    @model_validator(mode="after")
    def validate_manifest(self) -> "CheckpointSelectionCandidateManifest":
        expected = _canonical_sha256(self.model_dump(mode="json", exclude={"manifest_sha256"}))
        if self.manifest_sha256 and self.manifest_sha256 != expected:
            raise ValueError("checkpoint selection candidate hash does not match canonical content")
        object.__setattr__(self, "manifest_sha256", expected)
        return self


def validate_screening_completeness(
    protocol: ExperimentProtocol,
    receipts: tuple[ExperimentRunReceipt, ...],
) -> None:
    """Require one durable disposition for every mandatory system and screening seed."""

    observed: dict[MandatoryExperimentSystem, set[int]] = {
        system: set() for system in MandatoryExperimentSystem
    }
    for receipt in receipts:
        if receipt.protocol_sha256 != protocol.protocol_sha256:
            raise ValueError("screening receipt belongs to a different protocol")
        if receipt.stage != ExperimentStage.SCREENING:
            continue
        if receipt.seed in observed[receipt.system]:
            raise ValueError("duplicate screening disposition for a system and seed")
        observed[receipt.system].add(receipt.seed)
    required = set(protocol.screening_seeds)
    incomplete = {
        system.value: sorted(required.difference(seeds))
        for system, seeds in observed.items()
        if seeds != required
    }
    if incomplete:
        raise ValueError(f"mandatory screening dispositions are incomplete: {incomplete}")


def freeze_champion(
    *,
    protocol: ExperimentProtocol,
    system: MandatoryExperimentSystem,
    selected_config_sha256: str,
    finalist_receipts: tuple[ExperimentRunReceipt, ...],
    baseline_receipts: tuple[ExperimentRunReceipt, ...],
    electra_receipts: tuple[ExperimentRunReceipt, ...],
    comparison: StatisticalComparison,
) -> ChampionManifest:
    """Freeze one dev-only champion after all five finalist seeds succeed."""

    if tuple(sorted(receipt.seed for receipt in finalist_receipts)) != tuple(
        sorted(protocol.finalist_seeds)
    ):
        raise ValueError("champion requires every frozen finalist seed exactly once")
    for receipt in finalist_receipts:
        if (
            receipt.protocol_sha256 != protocol.protocol_sha256
            or receipt.system != system
            or receipt.stage != ExperimentStage.FINALIST
            or receipt.status != ExperimentRunStatus.SUCCEEDED
            or receipt.metrics is None
        ):
            raise ValueError("champion accepts only successful matching dev finalist receipts")
    if comparison.protocol_sha256 != protocol.protocol_sha256 or comparison.candidate_system != system:
        raise ValueError("champion comparison does not identify the selected system")
    mean_full_f = sum(receipt.metrics.full_f for receipt in finalist_receipts if receipt.metrics) / len(
        finalist_receipts
    )
    selected_checkpoint = max(
        finalist_receipts,
        key=lambda receipt: (
            receipt.metrics.full_f if receipt.metrics is not None else -1.0,
            -receipt.seed,
        ),
    )
    if tuple(sorted(receipt.seed for receipt in baseline_receipts)) != tuple(
        sorted(protocol.finalist_seeds)
    ):
        raise ValueError("champion requires every strongest-baseline finalist seed")
    if any(
        receipt.status != ExperimentRunStatus.SUCCEEDED
        or receipt.system != comparison.baseline_system
        or receipt.stage != ExperimentStage.FINALIST
        for receipt in baseline_receipts
    ):
        raise ValueError("champion baseline receipts are not complete successful finalists")
    baseline_checkpoint = max(
        baseline_receipts,
        key=lambda receipt: (
            receipt.metrics.full_f if receipt.metrics is not None else -1.0,
            -receipt.seed,
        ),
    )
    if tuple(sorted(receipt.seed for receipt in electra_receipts)) != tuple(
        sorted(protocol.finalist_seeds)
    ) or any(
        receipt.system != MandatoryExperimentSystem.ELECTRA
        or receipt.status != ExperimentRunStatus.SUCCEEDED
        or receipt.stage != ExperimentStage.FINALIST
        for receipt in electra_receipts
    ):
        raise ValueError("champion requires every ELECTRA finalist seed")
    electra_checkpoint = max(
        electra_receipts,
        key=lambda receipt: (
            receipt.metrics.full_f if receipt.metrics is not None else -1.0,
            -receipt.seed,
        ),
    )
    return ChampionManifest(
        protocol_sha256=protocol.protocol_sha256,
        champion_system=system,
        baseline_system=comparison.baseline_system,
        selected_config_sha256=selected_config_sha256,
        dev_run_receipts=tuple(receipt.receipt_sha256 for receipt in finalist_receipts),
        selected_checkpoint_receipt_sha256=selected_checkpoint.receipt_sha256,
        baseline_dev_run_receipts=tuple(receipt.receipt_sha256 for receipt in baseline_receipts),
        baseline_checkpoint_receipt_sha256=baseline_checkpoint.receipt_sha256,
        electra_dev_run_receipts=tuple(receipt.receipt_sha256 for receipt in electra_receipts),
        electra_checkpoint_receipt_sha256=electra_checkpoint.receipt_sha256,
        comparison_sha256=comparison.comparison_sha256,
        mean_dev_full_f=mean_full_f,
        created_at=datetime.now(UTC),
        test_data_accessed=False,
    )


def write_final_evaluation_receipt(
    *,
    path: Path,
    protocol: ExperimentProtocol,
    champion: ChampionManifest,
    test_receipts: tuple[ExperimentRunReceipt, ...],
    test2_receipts: tuple[ExperimentRunReceipt, ...],
    baseline_test_receipts: tuple[ExperimentRunReceipt, ...],
    baseline_test2_receipts: tuple[ExperimentRunReceipt, ...],
    electra_test_receipts: tuple[ExperimentRunReceipt, ...],
    electra_test2_receipts: tuple[ExperimentRunReceipt, ...],
    longest_document_completed: bool,
    candidate_truncation_occurred: bool,
    out_of_memory_occurred: bool,
) -> FinalEvaluationReceipt:
    """Atomically create the single allowed final-evaluation receipt."""

    if path.exists() or path.with_suffix(f"{path.suffix}.tmp").exists():
        raise RuntimeError("final evaluation receipt already exists; test evaluation is one-time")
    champion_receipts = (*test_receipts, *test2_receipts)
    baseline_receipts = (*baseline_test_receipts, *baseline_test2_receipts)
    if not all(
        (
            test_receipts,
            test2_receipts,
            baseline_test_receipts,
            baseline_test2_receipts,
            electra_test_receipts,
            electra_test2_receipts,
        )
    ):
        raise ValueError("final evaluation requires champion, strongest baseline, and ELECTRA test/test2 receipts")
    for receipt in champion_receipts:
        if (
            receipt.protocol_sha256 != protocol.protocol_sha256
            or receipt.system != champion.champion_system
            or receipt.stage != ExperimentStage.FINAL_EVALUATION
            or receipt.status != ExperimentRunStatus.SUCCEEDED
        ):
            raise ValueError("final evaluation contains an invalid champion test receipt")
    for receipt in baseline_receipts:
        if (
            receipt.protocol_sha256 != protocol.protocol_sha256
            or receipt.system != champion.baseline_system
            or receipt.stage != ExperimentStage.FINAL_EVALUATION
            or receipt.status != ExperimentRunStatus.SUCCEEDED
        ):
            raise ValueError("final evaluation contains an invalid baseline test receipt")
    for receipt in (*electra_test_receipts, *electra_test2_receipts):
        if (
            receipt.protocol_sha256 != protocol.protocol_sha256
            or receipt.system != MandatoryExperimentSystem.ELECTRA
            or receipt.stage != ExperimentStage.FINAL_EVALUATION
            or receipt.status != ExperimentRunStatus.SUCCEEDED
        ):
            raise ValueError("final evaluation contains an invalid ELECTRA test receipt")
    if any(receipt.partitions != (CorpusPartition.TEST,) for receipt in test_receipts):
        raise ValueError("test receipt family contains a non-test partition")
    if any(receipt.partitions != (CorpusPartition.TEST2,) for receipt in test2_receipts):
        raise ValueError("test2 receipt family contains a non-test2 partition")
    if any(receipt.partitions != (CorpusPartition.TEST,) for receipt in baseline_test_receipts):
        raise ValueError("baseline test receipt family contains a non-test partition")
    if any(receipt.partitions != (CorpusPartition.TEST2,) for receipt in baseline_test2_receipts):
        raise ValueError("baseline test2 receipt family contains a non-test2 partition")
    if any(receipt.partitions != (CorpusPartition.TEST,) for receipt in electra_test_receipts):
        raise ValueError("ELECTRA test receipt family contains a non-test partition")
    if any(receipt.partitions != (CorpusPartition.TEST2,) for receipt in electra_test2_receipts):
        raise ValueError("ELECTRA test2 receipt family contains a non-test2 partition")
    receipt = FinalEvaluationReceipt(
        protocol_sha256=protocol.protocol_sha256,
        champion_sha256=champion.champion_sha256,
        test_run_receipts=tuple(item.receipt_sha256 for item in test_receipts),
        test2_run_receipts=tuple(item.receipt_sha256 for item in test2_receipts),
        baseline_test_run_receipts=tuple(item.receipt_sha256 for item in baseline_test_receipts),
        baseline_test2_run_receipts=tuple(item.receipt_sha256 for item in baseline_test2_receipts),
        electra_test_run_receipts=tuple(item.receipt_sha256 for item in electra_test_receipts),
        electra_test2_run_receipts=tuple(item.receipt_sha256 for item in electra_test2_receipts),
        longest_document_completed=longest_document_completed,
        candidate_truncation_occurred=candidate_truncation_occurred,
        out_of_memory_occurred=out_of_memory_occurred,
        evaluated_at=datetime.now(UTC),
        evaluation_nonce=secrets.token_hex(16),
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    temporary.write_text(receipt.model_dump_json(indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)
    return receipt


def build_selection_decision(
    *,
    protocol: ExperimentProtocol,
    champion: ChampionManifest,
    final_evaluation: FinalEvaluationReceipt,
    comparison: StatisticalComparison,
    measurements: SelectionMeasurements,
    parity: CpuMpsParityEvidence,
    efficiency: TiedSystemEfficiencyEvidence,
    canonical_checkpoint_manifest_sha256: str,
) -> SelectionDecision:
    """Evaluate every promotion gate from typed measured evidence, fail closed."""

    thresholds = protocol.thresholds
    checks = {
        SelectionGateName.DEV_FULL_IMPROVEMENT: (
            measurements.champion_dev_full_f - measurements.baseline_dev_full_f
            >= thresholds.dev_full_improvement
        ),
        SelectionGateName.HOLM_BOOTSTRAP: (
            comparison.ci_lower > 0.0 and comparison.holm_adjusted_p_value <= 0.05
        ),
        SelectionGateName.TEST_FULL_IMPROVEMENT: (
            measurements.champion_test_full_f - measurements.baseline_test_full_f
            >= thresholds.test_full_improvement
        ),
        SelectionGateName.TEST_COMPONENT_REGRESSION: all(
            champion_value >= baseline_value - thresholds.max_component_regression
            for champion_value, baseline_value in (
                (measurements.champion_test_span_f, measurements.baseline_test_span_f),
                (measurements.champion_test_direction_f, measurements.baseline_test_direction_f),
                (measurements.champion_test_relation_f, measurements.baseline_test_relation_f),
            )
        ),
        SelectionGateName.CALIBRATION: (
            measurements.champion_test_ece <= thresholds.max_ece
            and measurements.champion_test_brier <= measurements.baseline_test_brier
        ),
        SelectionGateName.LONGEST_DOCUMENT: (
            final_evaluation.longest_document_completed
            and not final_evaluation.candidate_truncation_occurred
            and not final_evaluation.out_of_memory_occurred
        ),
        SelectionGateName.PEAK_RSS: (
            measurements.champion_peak_rss_bytes <= thresholds.max_peak_rss_bytes
        ),
        SelectionGateName.MPS_LATENCY: (
            measurements.champion_mps_p95_latency_ms
            <= thresholds.max_mps_latency_ratio * measurements.electra_mps_p95_latency_ms
        ),
        SelectionGateName.TIED_SYSTEM_EFFICIENCY: efficiency.selected_is_fastest_and_smallest,
        SelectionGateName.CPU_MPS_PARITY: (
            parity.decoded_graphs_equal
            and parity.max_probability_delta <= thresholds.cpu_mps_probability_tolerance
        ),
    }
    evidence_hashes = {
        SelectionGateName.HOLM_BOOTSTRAP: comparison.comparison_sha256,
        SelectionGateName.LONGEST_DOCUMENT: final_evaluation.receipt_sha256,
        SelectionGateName.TIED_SYSTEM_EFFICIENCY: efficiency.evidence_sha256,
        SelectionGateName.CPU_MPS_PARITY: parity.evidence_sha256,
    }
    gates = tuple(
        SelectionGateResult(
            gate=gate,
            passed=checks[gate],
            evidence_sha256=evidence_hashes.get(gate, measurements.measurements_sha256),
            reason=("measured gate passed" if checks[gate] else "measured gate failed"),
        )
        for gate in SelectionGateName
    )
    selected = all(result.passed for result in gates)
    return SelectionDecision(
        outcome=SelectionOutcome.SELECTED if selected else SelectionOutcome.NO_SELECTION,
        protocol_sha256=protocol.protocol_sha256,
        champion_sha256=champion.champion_sha256,
        final_evaluation_sha256=final_evaluation.receipt_sha256,
        gates=gates,
        canonical_checkpoint_manifest_sha256=(
            canonical_checkpoint_manifest_sha256 if selected else None
        ),
    )


__all__ = [
    "CheckpointSelectionCandidateManifest",
    "CpuMpsParityEvidence",
    "SelectionMeasurements",
    "TiedSystemEfficiencyEvidence",
    "build_selection_decision",
    "freeze_champion",
    "validate_screening_completeness",
    "write_final_evaluation_receipt",
]
