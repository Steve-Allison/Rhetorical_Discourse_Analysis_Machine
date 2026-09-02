"""Executable, evidence-bearing contracts for the isolated eRST comparison harness."""

from datetime import datetime
from enum import StrEnum
import hashlib
import json

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from rdam.rst._version import PACKAGE_VERSION
from rdam.rst.contracts.erst import CorpusPartition

EXPERIMENT_PROTOCOL_SCHEMA_VERSION = "1.0"
EXPERIMENT_RUN_SCHEMA_VERSION = "1.0"
EXPERIMENT_SELECTION_SCHEMA_VERSION = "1.0"

_GIT_REVISION_PATTERN = r"^[0-9a-f]{40}$"
_SHA256_PATTERN = r"^[0-9a-f]{64}$"
_SCREENING_SEEDS = (17, 42, 73)
_FINALIST_SEEDS = (17, 29, 42, 73, 101)
def _canonical_model_hash(model: BaseModel, *, hash_field: str) -> str:
    payload = model.model_dump(mode="json", exclude={hash_field})
    encoded = json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode()
    return hashlib.sha256(encoded).hexdigest()


class MandatoryExperimentSystem(StrEnum):
    """Complete technology-comparison inventory in protocol order."""

    EXISTING_DUAL_ENCODER = "existing_dual_encoder_bilinear_structural"
    STRUCTURAL_ONLY = "structural_only_calibrated"
    TEXT_ONLY = "text_only_cross_encoder"
    ELECTRA = "electra_signal_aware_cross_encoder"
    SIGNAL_RULE = "signal_plus_rule"
    MODERNBERT_BASE = "modernbert_base_signal_aware"
    MODERNBERT_LARGE = "modernbert_large_signal_aware"
    XLM_R_HIDAC = "xlm_roberta_large_hidac"
    QWEN3_DEDISCO = "qwen3_4b_dedisco_peft"
    EDGE_FEATURED_GAT = "edge_featured_graph_attention"


class ExperimentStage(StrEnum):
    """A run's role and permitted corpus boundary."""

    SCREENING = "screening"
    FINALIST = "finalist"
    ABLATION = "ablation"
    FINAL_EVALUATION = "final_evaluation"


class AblationName(StrEnum):
    """Every mandatory removal study in frozen protocol order."""

    SIGNAL_MARKING = "signal_marking"
    STRUCTURAL_FEATURES = "structural_features"
    PRIMARY_PATH_ENCODING = "primary_path_encoding"
    CONTEXT = "context"
    GRAPH_FUSION = "graph_fusion"
    HARD_NEGATIVES = "hard_negatives"
    CALIBRATION = "calibration"
    RAW_VS_COARSE_LABELS = "raw_vs_coarse_labels"


_ABLATIONS = tuple(AblationName)


class ExperimentRunStatus(StrEnum):
    """Evidence state for one attempted system run."""

    SUCCEEDED = "succeeded"
    FAILED = "failed"
    INCOMPATIBLE = "incompatible"


class EvaluationSetting(StrEnum):
    """Primary-tree and signal inputs used by an eRST evaluation."""

    GOLD_PRIMARY_GOLD_SIGNAL = "gold_primary_gold_signal"
    PREDICTED_PRIMARY_PREDICTED_SIGNAL = "predicted_primary_predicted_signal"


class SelectionOutcome(StrEnum):
    """Result of applying every canonical-checkpoint selection gate."""

    SELECTED = "selected"
    NO_SELECTION = "no_selection"


class SelectionGateName(StrEnum):
    """Every conjunctive checkpoint-selection condition."""

    DEV_FULL_IMPROVEMENT = "dev_full_improvement"
    HOLM_BOOTSTRAP = "holm_bootstrap"
    TEST_FULL_IMPROVEMENT = "test_full_improvement"
    TEST_COMPONENT_REGRESSION = "test_component_regression"
    CALIBRATION = "calibration"
    LONGEST_DOCUMENT = "longest_document"
    PEAK_RSS = "peak_rss"
    MPS_LATENCY = "mps_latency"
    TIED_SYSTEM_EFFICIENCY = "tied_system_efficiency"
    CPU_MPS_PARITY = "cpu_mps_parity"


class SignalLocation(StrEnum):
    """Node containing the signal marked in a pairwise example."""

    SOURCE = "source"
    TARGET = "target"


class EdgeDirection(StrEnum):
    """Directed ordering token for pairwise serialization."""

    LEFT = "left"
    RIGHT = "right"


class SignalMarkedExample(BaseModel):
    """One model-neutral signal-aware pairwise candidate."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    relation_raw: str = Field(min_length=1)
    same_path_relation_raw: str | None = None
    direction: EdgeDirection
    head_edu_distance: int = Field(ge=0)
    source_text: str = Field(min_length=1)
    target_text: str = Field(min_length=1)
    signal_location: SignalLocation
    signal_start: int = Field(ge=0)
    signal_end: int = Field(gt=0)
    label: bool | None = None

    @field_validator("relation_raw", "same_path_relation_raw")
    @classmethod
    def validate_relation(cls, value: str | None) -> str | None:
        if value is not None and (not value.strip() or any(char in value for char in "\t\r\n")):
            raise ValueError("relation labels must be non-empty single-line values")
        return value

    @field_validator("source_text", "target_text")
    @classmethod
    def validate_text(cls, value: str) -> str:
        if any(char in value for char in "\t\r\n"):
            raise ValueError("candidate text must be a single tab-free line")
        return value

    @model_validator(mode="after")
    def validate_signal_span(self) -> "SignalMarkedExample":
        text = self.source_text if self.signal_location == SignalLocation.SOURCE else self.target_text
        if self.signal_start >= self.signal_end or self.signal_end > len(text):
            raise ValueError("signal span must be non-empty and contained by its selected text")
        return self


class ExperimentSystemSpec(BaseModel):
    """Frozen implementation and upstream model identity for one system."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    system: MandatoryExperimentSystem
    implementation: str = Field(min_length=1)
    model_id: str | None = None
    model_revision: str | None = Field(default=None, pattern=_GIT_REVISION_PATTERN)
    model_license: str = Field(min_length=1)
    config_sha256: str = Field(pattern=_SHA256_PATTERN)

    @model_validator(mode="after")
    def validate_model_identity(self) -> "ExperimentSystemSpec":
        if (self.model_id is None) != (self.model_revision is None):
            raise ValueError("model ID and immutable revision must be supplied together")
        return self


class SelectionThresholds(BaseModel):
    """Frozen numerical checkpoint-selection thresholds."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    dev_full_improvement: float = 0.02
    test_full_improvement: float = 0.01
    max_component_regression: float = 0.005
    max_ece: float = 0.05
    max_peak_rss_bytes: int = 24 * 1024**3
    max_mps_latency_ratio: float = 2.0
    efficiency_tie_full_delta: float = 0.005
    cpu_mps_probability_tolerance: float = 1e-5


class ExperimentProtocol(BaseModel):
    """Immutable authority for comparable eRST implementation and execution."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = EXPERIMENT_PROTOCOL_SCHEMA_VERSION
    package_version: str = PACKAGE_VERSION
    corpus_revision: str = Field(pattern=_GIT_REVISION_PATTERN)
    environment_lock_sha256: str = Field(pattern=_SHA256_PATTERN)
    harness_source_sha256: str = Field(pattern=_SHA256_PATTERN)
    production_source_sha256: str = Field(pattern=_SHA256_PATTERN)
    corpus_receipt_sha256: str = Field(pattern=_SHA256_PATTERN)
    split_manifest_sha256: str = Field(pattern=_SHA256_PATTERN)
    candidate_schema_sha256: str = Field(pattern=_SHA256_PATTERN)
    signal_detector_sha256: str = Field(pattern=_SHA256_PATTERN)
    raw_relation_inventory_sha256: str = Field(pattern=_SHA256_PATTERN)
    ontology_mapping_sha256: str = Field(pattern=_SHA256_PATTERN)
    decoder_config_sha256: str = Field(pattern=_SHA256_PATTERN)
    systems: tuple[ExperimentSystemSpec, ...]
    screening_seeds: tuple[int, ...] = _SCREENING_SEEDS
    finalist_seeds: tuple[int, ...] = _FINALIST_SEEDS
    ablations: tuple[AblationName, ...] = _ABLATIONS
    finalist_delta: float = 0.02
    bootstrap_resamples: int = 10_000
    bootstrap_seed: int = 20260825
    calibration_bins: int = 10
    thresholds: SelectionThresholds = SelectionThresholds()
    training_partitions: tuple[CorpusPartition, ...] = (CorpusPartition.TRAIN, CorpusPartition.DEV)
    final_evaluation_partitions: tuple[CorpusPartition, ...] = (
        CorpusPartition.TEST,
        CorpusPartition.TEST2,
    )
    protocol_sha256: str = ""

    @model_validator(mode="after")
    def validate_protocol(self) -> "ExperimentProtocol":
        observed = tuple(spec.system for spec in self.systems)
        if observed != tuple(MandatoryExperimentSystem):
            raise ValueError("protocol must contain every mandatory system exactly once in protocol order")
        if self.screening_seeds != _SCREENING_SEEDS or self.finalist_seeds != _FINALIST_SEEDS:
            raise ValueError("protocol seeds do not match the frozen comparison design")
        if self.ablations != _ABLATIONS:
            raise ValueError("protocol must retain all eight frozen ablations in order")
        if self.bootstrap_resamples != 10_000:
            raise ValueError("protocol requires exactly 10,000 paired bootstrap resamples")
        if self.training_partitions != (CorpusPartition.TRAIN, CorpusPartition.DEV):
            raise ValueError("training boundary must contain train and dev only")
        if self.final_evaluation_partitions != (CorpusPartition.TEST, CorpusPartition.TEST2):
            raise ValueError("final evaluation boundary must contain test and test2 only")
        expected_hash = _canonical_model_hash(self, hash_field="protocol_sha256")
        if self.protocol_sha256 and self.protocol_sha256 != expected_hash:
            raise ValueError("experiment protocol SHA-256 does not match canonical content")
        object.__setattr__(self, "protocol_sha256", expected_hash)
        return self


class ExperimentMetrics(BaseModel):
    """Repository-scorer, calibration, and loss results for one run."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    span_f: float = Field(ge=0.0, le=1.0)
    direction_f: float = Field(ge=0.0, le=1.0)
    relation_f: float = Field(ge=0.0, le=1.0)
    full_f: float = Field(ge=0.0, le=1.0)
    ece: float = Field(ge=0.0, le=1.0)
    brier: float = Field(ge=0.0, le=1.0)
    loss: float | None = Field(default=None, ge=0.0)


class DocumentScore(BaseModel):
    """Paired document-level scorer result used by statistical comparison."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    document_id: str = Field(min_length=1)
    source_sha256: str = Field(pattern=_SHA256_PATTERN)
    full_f: float = Field(ge=0.0, le=1.0)


class ResourceEvidence(BaseModel):
    """Comparable local hardware and runtime measurements."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    machine: str = Field(min_length=1)
    operating_system: str = Field(min_length=1)
    processor: str = Field(min_length=1)
    physical_memory_bytes: int = Field(gt=0)
    device: str = Field(min_length=1)
    torch_version: str = Field(min_length=1)
    transformers_version: str = Field(min_length=1)
    thread_count: int = Field(gt=0)
    p50_latency_ms: float = Field(gt=0.0)
    p95_latency_ms: float = Field(gt=0.0)
    peak_rss_bytes: int = Field(gt=0)
    mps_peak_allocated_bytes: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_percentiles(self) -> "ResourceEvidence":
        if self.p95_latency_ms < self.p50_latency_ms:
            raise ValueError("p95 latency cannot be lower than p50 latency")
        return self


class RunFailure(BaseModel):
    """Typed durable evidence for a failed or incompatible run."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    failure_type: str = Field(min_length=1)
    message: str = Field(min_length=1, max_length=2_000)
    evidence_sha256: str = Field(pattern=_SHA256_PATTERN)
    retryable: bool


class ExperimentRunReceipt(BaseModel):
    """Immutable success or failure evidence for one attempted system run."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = EXPERIMENT_RUN_SCHEMA_VERSION
    package_version: str = PACKAGE_VERSION
    run_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]*$")
    protocol_sha256: str = Field(pattern=_SHA256_PATTERN)
    system: MandatoryExperimentSystem
    stage: ExperimentStage
    ablation: AblationName | None = None
    status: ExperimentRunStatus
    seed: int
    setting: EvaluationSetting
    partitions: tuple[CorpusPartition, ...]
    architecture_config_sha256: str = Field(pattern=_SHA256_PATTERN)
    candidate_selection_sha256: str = Field(pattern=_SHA256_PATTERN)
    split_manifest_sha256: str = Field(pattern=_SHA256_PATTERN)
    started_at: datetime
    completed_at: datetime
    document_count: int = Field(ge=0)
    scored_document_count: int = Field(ge=0)
    candidate_count: int = Field(ge=0)
    execution_steps: int = Field(ge=0)
    checkpoint_sha256: str | None = Field(default=None, pattern=_SHA256_PATTERN)
    predictions_sha256: str | None = Field(default=None, pattern=_SHA256_PATTERN)
    scorer_output_sha256: str | None = Field(default=None, pattern=_SHA256_PATTERN)
    metrics: ExperimentMetrics | None = None
    document_scores: tuple[DocumentScore, ...] = ()
    resources: ResourceEvidence | None = None
    failure: RunFailure | None = None
    receipt_sha256: str = ""

    @field_validator("started_at", "completed_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("experiment timestamps must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_run(self) -> "ExperimentRunReceipt":
        if self.completed_at < self.started_at:
            raise ValueError("experiment completion precedes its start")
        if (self.stage == ExperimentStage.ABLATION) != (self.ablation is not None):
            raise ValueError("ablation identity is required exactly for ablation-stage runs")
        allowed = (
            {CorpusPartition.TRAIN, CorpusPartition.DEV}
            if self.stage != ExperimentStage.FINAL_EVALUATION
            else {CorpusPartition.TEST, CorpusPartition.TEST2}
        )
        if not self.partitions or not set(self.partitions).issubset(allowed):
            raise ValueError("run partitions violate the stage's corpus boundary")
        if self.status == ExperimentRunStatus.SUCCEEDED:
            required_positive = (self.document_count, self.candidate_count, self.execution_steps)
            required_evidence = (
                self.checkpoint_sha256,
                self.predictions_sha256,
                self.scorer_output_sha256,
                self.metrics,
                self.resources,
            )
            if any(value <= 0 for value in required_positive) or any(value is None for value in required_evidence):
                raise ValueError("successful runs require non-zero work and complete artifact evidence")
            if not self.document_scores or len(self.document_scores) != self.scored_document_count:
                raise ValueError("successful runs require one scorer result per document")
            if self.failure is not None:
                raise ValueError("successful runs cannot carry failure evidence")
        elif self.failure is None:
            raise ValueError("failed and incompatible runs require typed failure evidence")
        expected_hash = _canonical_model_hash(self, hash_field="receipt_sha256")
        if self.receipt_sha256 and self.receipt_sha256 != expected_hash:
            raise ValueError("experiment run SHA-256 does not match canonical content")
        object.__setattr__(self, "receipt_sha256", expected_hash)
        return self


class ExperimentDocumentIdentity(BaseModel):
    """Text-free identity and candidate count for one governed document."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    document_id: str = Field(min_length=1)
    source_sha256: str = Field(pattern=_SHA256_PATTERN)
    partition: CorpusPartition
    candidate_count: int = Field(gt=0)


class ExperimentDataIdentity(BaseModel):
    """Shared candidate and split identity supplied unchanged to comparable runs."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    split_manifest_sha256: str = Field(pattern=_SHA256_PATTERN)
    candidate_selection_sha256: str = Field(pattern=_SHA256_PATTERN)
    partitions: tuple[CorpusPartition, ...] = Field(min_length=1)
    documents: tuple[ExperimentDocumentIdentity, ...] = Field(min_length=1)
    scored_document_ids: tuple[str, ...] = Field(min_length=1)
    candidate_count: int = Field(gt=0)
    identity_sha256: str = ""

    @model_validator(mode="after")
    def validate_data_identity(self) -> "ExperimentDataIdentity":
        document_ids = tuple(document.document_id for document in self.documents)
        source_hashes = tuple(document.source_sha256 for document in self.documents)
        if len(set(document_ids)) != len(document_ids):
            raise ValueError("experiment data document IDs must be unique")
        if len(set(source_hashes)) != len(source_hashes):
            raise ValueError("experiment data source hashes must be unique")
        if self.candidate_count != sum(document.candidate_count for document in self.documents):
            raise ValueError("experiment data candidate count does not reconcile")
        if len(set(self.scored_document_ids)) != len(self.scored_document_ids):
            raise ValueError("scored experiment document IDs must be unique")
        if not set(self.scored_document_ids).issubset(document_ids):
            raise ValueError("scored experiment documents must exist in the governed input")
        expected_hash = _canonical_model_hash(self, hash_field="identity_sha256")
        if self.identity_sha256 and self.identity_sha256 != expected_hash:
            raise ValueError("experiment data SHA-256 does not match canonical content")
        object.__setattr__(self, "identity_sha256", expected_hash)
        return self


class ExperimentIndexEntry(BaseModel):
    """Content-addressed location of one retained run receipt."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]*$")
    system: MandatoryExperimentSystem
    stage: ExperimentStage
    status: ExperimentRunStatus
    seed: int
    receipt_path: str = Field(pattern=r"^receipts/[a-z0-9][a-z0-9._-]*\.json$")
    receipt_sha256: str = Field(pattern=_SHA256_PATTERN)


class ExperimentIndex(BaseModel):
    """Immutable, append-only inventory of successful and unsuccessful runs."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = EXPERIMENT_RUN_SCHEMA_VERSION
    protocol_sha256: str = Field(pattern=_SHA256_PATTERN)
    entries: tuple[ExperimentIndexEntry, ...]
    index_sha256: str = ""

    @model_validator(mode="after")
    def validate_index(self) -> "ExperimentIndex":
        run_ids = tuple(entry.run_id for entry in self.entries)
        receipt_hashes = tuple(entry.receipt_sha256 for entry in self.entries)
        if len(set(run_ids)) != len(run_ids):
            raise ValueError("experiment index run IDs must be unique")
        if len(set(receipt_hashes)) != len(receipt_hashes):
            raise ValueError("experiment index receipt hashes must be unique")
        expected_hash = _canonical_model_hash(self, hash_field="index_sha256")
        if self.index_sha256 and self.index_sha256 != expected_hash:
            raise ValueError("experiment index SHA-256 does not match canonical content")
        object.__setattr__(self, "index_sha256", expected_hash)
        return self


class StatisticalComparison(BaseModel):
    """Reproducible paired-bootstrap and Holm-corrected comparison."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = EXPERIMENT_SELECTION_SCHEMA_VERSION
    protocol_sha256: str = Field(pattern=_SHA256_PATTERN)
    candidate_system: MandatoryExperimentSystem
    baseline_system: MandatoryExperimentSystem
    candidate_run_receipts: tuple[str, ...] = Field(min_length=1)
    baseline_run_receipts: tuple[str, ...] = Field(min_length=1)
    paired_document_ids: tuple[str, ...] = Field(min_length=1)
    paired_differences: tuple[float, ...] = Field(min_length=1)
    mean_difference: float
    bootstrap_resamples: int = 10_000
    bootstrap_seed: int
    confidence_level: float = 0.95
    ci_lower: float
    ci_upper: float
    raw_p_value: float = Field(ge=0.0, le=1.0)
    holm_adjusted_p_value: float = Field(ge=0.0, le=1.0)
    comparison_sha256: str = ""

    @field_validator("candidate_run_receipts", "baseline_run_receipts")
    @classmethod
    def validate_receipt_hashes(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if any(len(item) != 64 or any(char not in "0123456789abcdef" for char in item) for item in value):
            raise ValueError("comparison run receipts require SHA-256 identities")
        return value

    @model_validator(mode="after")
    def validate_comparison(self) -> "StatisticalComparison":
        if self.bootstrap_resamples != 10_000 or self.confidence_level != 0.95:
            raise ValueError("comparison must use the frozen 10,000-resample 95% design")
        if len(self.paired_document_ids) != len(self.paired_differences):
            raise ValueError("paired document IDs and score differences must align")
        if len(set(self.paired_document_ids)) != len(self.paired_document_ids):
            raise ValueError("paired comparison document IDs must be unique")
        if self.ci_lower > self.ci_upper:
            raise ValueError("comparison confidence interval is inverted")
        expected_hash = _canonical_model_hash(self, hash_field="comparison_sha256")
        if self.comparison_sha256 and self.comparison_sha256 != expected_hash:
            raise ValueError("statistical comparison SHA-256 does not match canonical content")
        object.__setattr__(self, "comparison_sha256", expected_hash)
        return self


class ChampionManifest(BaseModel):
    """Dev-only finalist selection fixed before any test evaluation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = EXPERIMENT_SELECTION_SCHEMA_VERSION
    protocol_sha256: str = Field(pattern=_SHA256_PATTERN)
    champion_system: MandatoryExperimentSystem
    baseline_system: MandatoryExperimentSystem
    selected_config_sha256: str = Field(pattern=_SHA256_PATTERN)
    dev_run_receipts: tuple[str, ...] = Field(min_length=1)
    selected_checkpoint_receipt_sha256: str = Field(pattern=_SHA256_PATTERN)
    baseline_dev_run_receipts: tuple[str, ...] = Field(min_length=1)
    baseline_checkpoint_receipt_sha256: str = Field(pattern=_SHA256_PATTERN)
    electra_dev_run_receipts: tuple[str, ...] = Field(min_length=1)
    electra_checkpoint_receipt_sha256: str = Field(pattern=_SHA256_PATTERN)
    comparison_sha256: str = Field(pattern=_SHA256_PATTERN)
    mean_dev_full_f: float = Field(ge=0.0, le=1.0)
    created_at: datetime
    test_data_accessed: bool = False
    champion_sha256: str = ""

    @model_validator(mode="after")
    def validate_champion(self) -> "ChampionManifest":
        if self.created_at.tzinfo is None or self.created_at.utcoffset() is None:
            raise ValueError("champion timestamp must be timezone-aware")
        if self.test_data_accessed:
            raise ValueError("champion selection cannot access test or test2 data")
        if any(len(item) != 64 for item in self.dev_run_receipts):
            raise ValueError("champion run receipts require SHA-256 identities")
        if self.selected_checkpoint_receipt_sha256 not in self.dev_run_receipts:
            raise ValueError("selected checkpoint receipt must be one of the champion dev runs")
        if self.baseline_checkpoint_receipt_sha256 not in self.baseline_dev_run_receipts:
            raise ValueError("baseline checkpoint receipt must be one of the baseline dev runs")
        if self.electra_checkpoint_receipt_sha256 not in self.electra_dev_run_receipts:
            raise ValueError("ELECTRA checkpoint receipt must be one of its dev runs")
        if self.baseline_system == self.champion_system:
            raise ValueError("champion and strongest baseline must be different systems")
        expected_hash = _canonical_model_hash(self, hash_field="champion_sha256")
        if self.champion_sha256 and self.champion_sha256 != expected_hash:
            raise ValueError("champion manifest SHA-256 does not match canonical content")
        object.__setattr__(self, "champion_sha256", expected_hash)
        return self


class FinalEvaluationReceipt(BaseModel):
    """One-time untouched test evaluation bound to a frozen champion."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = EXPERIMENT_SELECTION_SCHEMA_VERSION
    protocol_sha256: str = Field(pattern=_SHA256_PATTERN)
    champion_sha256: str = Field(pattern=_SHA256_PATTERN)
    test_run_receipts: tuple[str, ...] = Field(min_length=1)
    test2_run_receipts: tuple[str, ...] = Field(min_length=1)
    baseline_test_run_receipts: tuple[str, ...] = Field(min_length=1)
    baseline_test2_run_receipts: tuple[str, ...] = Field(min_length=1)
    electra_test_run_receipts: tuple[str, ...] = Field(min_length=1)
    electra_test2_run_receipts: tuple[str, ...] = Field(min_length=1)
    longest_document_completed: bool
    candidate_truncation_occurred: bool
    out_of_memory_occurred: bool
    evaluated_at: datetime
    evaluation_nonce: str = Field(min_length=16)
    receipt_sha256: str = ""

    @model_validator(mode="after")
    def validate_final_evaluation(self) -> "FinalEvaluationReceipt":
        if self.evaluated_at.tzinfo is None or self.evaluated_at.utcoffset() is None:
            raise ValueError("final evaluation timestamp must be timezone-aware")
        receipt_hashes = (
            self.test_run_receipts
            + self.test2_run_receipts
            + self.baseline_test_run_receipts
            + self.baseline_test2_run_receipts
            + self.electra_test_run_receipts
            + self.electra_test2_run_receipts
        )
        if any(len(item) != 64 for item in receipt_hashes):
            raise ValueError("final evaluation run receipts require SHA-256 identities")
        expected_hash = _canonical_model_hash(self, hash_field="receipt_sha256")
        if self.receipt_sha256 and self.receipt_sha256 != expected_hash:
            raise ValueError("final evaluation SHA-256 does not match canonical content")
        object.__setattr__(self, "receipt_sha256", expected_hash)
        return self


class SelectionGateResult(BaseModel):
    """One checkpoint-selection threshold and its immutable evidence."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    gate: SelectionGateName
    passed: bool
    evidence_sha256: str = Field(pattern=_SHA256_PATTERN)
    reason: str = Field(min_length=1)


class SelectionDecision(BaseModel):
    """Conjunctive decision to name, or not name, a canonical checkpoint."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = EXPERIMENT_SELECTION_SCHEMA_VERSION
    package_version: str = PACKAGE_VERSION
    outcome: SelectionOutcome
    protocol_sha256: str = Field(pattern=_SHA256_PATTERN)
    champion_sha256: str = Field(pattern=_SHA256_PATTERN)
    final_evaluation_sha256: str = Field(pattern=_SHA256_PATTERN)
    gates: tuple[SelectionGateResult, ...]
    canonical_checkpoint_manifest_sha256: str | None = Field(default=None, pattern=_SHA256_PATTERN)
    decision_sha256: str = ""

    @model_validator(mode="after")
    def validate_decision(self) -> "SelectionDecision":
        if tuple(result.gate for result in self.gates) != tuple(SelectionGateName):
            raise ValueError("selection decision must evaluate every gate exactly once in protocol order")
        all_passed = all(result.passed for result in self.gates)
        if self.outcome == SelectionOutcome.SELECTED:
            if not all_passed or self.canonical_checkpoint_manifest_sha256 is None:
                raise ValueError("selection requires every gate and a canonical checkpoint manifest")
        elif all_passed or self.canonical_checkpoint_manifest_sha256 is not None:
            raise ValueError("no-selection requires a failed gate and no canonical checkpoint")
        expected_hash = _canonical_model_hash(self, hash_field="decision_sha256")
        if self.decision_sha256 and self.decision_sha256 != expected_hash:
            raise ValueError("selection decision SHA-256 does not match canonical content")
        object.__setattr__(self, "decision_sha256", expected_hash)
        return self


__all__ = [
    "AblationName",
    "EXPERIMENT_PROTOCOL_SCHEMA_VERSION",
    "EXPERIMENT_RUN_SCHEMA_VERSION",
    "EXPERIMENT_SELECTION_SCHEMA_VERSION",
    "ChampionManifest",
    "DocumentScore",
    "EdgeDirection",
    "EvaluationSetting",
    "ExperimentMetrics",
    "ExperimentDataIdentity",
    "ExperimentDocumentIdentity",
    "ExperimentIndex",
    "ExperimentIndexEntry",
    "ExperimentProtocol",
    "ExperimentRunReceipt",
    "ExperimentRunStatus",
    "ExperimentStage",
    "ExperimentSystemSpec",
    "FinalEvaluationReceipt",
    "MandatoryExperimentSystem",
    "ResourceEvidence",
    "RunFailure",
    "SelectionDecision",
    "SelectionGateName",
    "SelectionGateResult",
    "SelectionOutcome",
    "SelectionThresholds",
    "SignalLocation",
    "SignalMarkedExample",
    "StatisticalComparison",
]
