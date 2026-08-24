"""Fail-closed research-authority contracts for eRST benchmark reproduction."""

from datetime import date
from enum import StrEnum
import hashlib
import json
from pathlib import PurePosixPath

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from isanlp_rst._version import PACKAGE_VERSION
from isanlp_rst.contracts.erst import CorpusLicenseClass, CorpusPartition

BASELINE_AUTHORITY_SCHEMA_VERSION = "1.0"

_GIT_REVISION_PATTERN = r"^[0-9a-f]{40}$"
_SHA256_PATTERN = r"^[0-9a-f]{64}$"


class BaselineAuthorityBlocker(StrEnum):
    """Reasons the published eRST baseline cannot yet authorize experiments."""

    OFFICIAL_SCORER_UNAVAILABLE = "official_scorer_unavailable"
    SCORER_PARITY_UNVERIFIED = "scorer_parity_unverified"


class BaselineDirection(StrEnum):
    """Direction token used by the released association serialization."""

    LEFT = "left"
    RIGHT = "right"


class BaselineSignalLocation(StrEnum):
    """Span containing the signal targeted by one association example."""

    SOURCE = "source"
    TARGET = "target"


class BaselineEvaluationSetting(StrEnum):
    """Required published-baseline pipeline settings."""

    GOLD_GOLD = "gold_primary_gold_signal"
    PREDICTED_PREDICTED = "predicted_primary_predicted_signal"


class MandatoryResearchSystem(StrEnum):
    """Complete mandatory system inventory; variants remain individually visible."""

    PUBLISHED_ELECTRA = "published_electra_cross_encoder"
    EXISTING_DUAL_ENCODER = "existing_dual_encoder_bilinear_structural"
    STRUCTURAL_ONLY = "structural_only_calibrated"
    TEXT_ONLY = "text_only_cross_encoder"
    MODERNBERT_BASE = "modernbert_base_signal_aware"
    MODERNBERT_LARGE = "modernbert_large_signal_aware"
    XLM_R_HIDAC = "xlm_roberta_large_hidac"
    QWEN3_DEDISCO = "qwen3_4b_dedisco_peft"
    EDGE_FEATURED_GAT = "edge_featured_graph_attention"
    SIGNAL_RULE = "signal_plus_rule"


class ResearchSystemStatus(StrEnum):
    """Execution status for one mandatory research system."""

    BLOCKED_BY_BASELINE_AUTHORITY = "blocked_by_baseline_authority"


class PromotionOutcome(StrEnum):
    """Canonical model-promotion decision."""

    PROMOTE = "promote"
    NO_PROMOTION = "no_promotion"


class PromotionGateName(StrEnum):
    """Every conjunctive promotion threshold in the frozen protocol."""

    DEV_FULL_IMPROVEMENT = "dev_full_improvement"
    PAIRED_BOOTSTRAP = "paired_bootstrap"
    TEST_FULL_IMPROVEMENT = "test_full_improvement"
    TEST_COMPONENT_REGRESSION = "test_component_regression"
    CALIBRATION = "calibration"
    LONGEST_DOCUMENT = "longest_document"
    PEAK_RSS = "peak_rss"
    MPS_LATENCY = "mps_latency"
    TIED_SYSTEM_EFFICIENCY = "tied_system_efficiency"
    CPU_MPS_PARITY = "cpu_mps_parity"


class ResearchArtifact(BaseModel):
    """Immutable identity for one public research artifact."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(min_length=1)
    url: str = Field(pattern=r"^https://")
    sha256: str = Field(pattern=_SHA256_PATTERN)
    revision: str | None = Field(default=None, pattern=_GIT_REVISION_PATTERN)
    license: str = Field(min_length=1)


class ModelRevisionAuthority(BaseModel):
    """Immutable model-hub identity used by the published baseline."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    model_id: str = Field(min_length=3)
    revision: str = Field(pattern=_GIT_REVISION_PATTERN)
    license: str = Field(min_length=1)


class BaselineCorpusSource(BaseModel):
    """Text-free identity for one exact GUM V9.2.0 comparison document."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    document_id: str = Field(pattern=r"^GUM_[a-z0-9]+_[a-z0-9]+$")
    source_path: str
    source_sha256: str = Field(pattern=_SHA256_PATTERN)
    partition: CorpusPartition
    license_class: CorpusLicenseClass

    @field_validator("source_path")
    @classmethod
    def validate_source_path(cls, value: str) -> str:
        path = PurePosixPath(value)
        if not value or path.is_absolute() or ".." in path.parts or "\\" in value:
            raise ValueError("baseline source_path must be a sanitized relative POSIX path")
        return value

    @field_validator("partition")
    @classmethod
    def reject_test2(cls, value: CorpusPartition) -> CorpusPartition:
        if value == CorpusPartition.TEST2:
            raise ValueError("the published GUM V9 baseline has no test2 partition")
        return value


class AuthoritySearchEvidence(BaseModel):
    """One completely inspected public surface and its scorer-resolution result."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    surface_url: str = Field(pattern=r"^https://")
    checked_resource: str = Field(min_length=1)
    result: str = Field(min_length=1)
    checked_on: date


class PublishedBaselineExample(BaseModel):
    """One exact association-classifier input before deterministic serialization."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    relation_raw: str = Field(min_length=1)
    same_path_relation_raw: str | None = None
    direction: BaselineDirection
    head_edu_distance: int = Field(ge=0)
    source_text: str = Field(min_length=1)
    target_text: str = Field(min_length=1)
    signal_location: BaselineSignalLocation
    signal_start: int = Field(ge=0)
    signal_end: int = Field(gt=0)
    label: bool | None = None

    @field_validator("relation_raw", "same_path_relation_raw")
    @classmethod
    def validate_relation(cls, value: str | None) -> str | None:
        if value is not None and (not value.strip() or any(character in value for character in "\t\r\n")):
            raise ValueError("baseline relation labels must be non-empty single-line values")
        return value

    @field_validator("source_text", "target_text")
    @classmethod
    def validate_text(cls, value: str) -> str:
        if any(character in value for character in "\t\r\n"):
            raise ValueError("baseline span text must be a single tab-free line")
        return value

    @model_validator(mode="after")
    def validate_signal_span(self) -> "PublishedBaselineExample":
        selected_text = self.source_text if self.signal_location == BaselineSignalLocation.SOURCE else self.target_text
        if self.signal_start >= self.signal_end or self.signal_end > len(selected_text):
            raise ValueError("baseline signal span must be non-empty and contained by its selected text")
        return self


def _canonical_hash(model: BaseModel) -> str:
    payload = model.model_dump(mode="json", exclude={"receipt_sha256"})
    encoded = json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode()
    return hashlib.sha256(encoded).hexdigest()


class ErstBaselineAuthorityReceipt(BaseModel):
    """Hashed authority and blocker evidence for the published eRST baseline."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = BASELINE_AUTHORITY_SCHEMA_VERSION
    package_version: str = PACKAGE_VERSION
    assessed_on: date
    paper: ResearchArtifact
    baseline_code: ResearchArtifact
    baseline_model: ModelRevisionAuthority
    corpus_tag: str = "V9.2.0"
    corpus_revision: str = Field(pattern=_GIT_REVISION_PATTERN)
    corpus_tree: str = Field(pattern=_GIT_REVISION_PATTERN)
    splits_sha256: str = Field(pattern=_SHA256_PATTERN)
    license_inventory_sha256: str = Field(pattern=_SHA256_PATTERN)
    sources: tuple[BaselineCorpusSource, ...] = Field(min_length=1)
    partition_counts: dict[CorpusPartition, int]
    official_scorer: ResearchArtifact | None
    scorer_parity_receipt_sha256: str | None = Field(default=None, pattern=_SHA256_PATTERN)
    released_checkpoint: ResearchArtifact | None
    released_environment_pins: tuple[str, ...]
    searched_surfaces: tuple[AuthoritySearchEvidence, ...] = Field(min_length=1)
    discrepancies: tuple[str, ...]
    blockers: tuple[BaselineAuthorityBlocker, ...]
    ready_for_reproduction: bool
    receipt_sha256: str = ""

    @model_validator(mode="after")
    def validate_authority(self) -> "ErstBaselineAuthorityReceipt":
        document_ids = [source.document_id for source in self.sources]
        source_hashes = [source.source_sha256 for source in self.sources]
        if len(document_ids) != len(set(document_ids)):
            raise ValueError("baseline source document IDs must be unique")
        if len(source_hashes) != len(set(source_hashes)):
            raise ValueError("baseline source hashes must be unique")

        expected_counts = {
            CorpusPartition.TRAIN: 165,
            CorpusPartition.DEV: 24,
            CorpusPartition.TEST: 24,
        }
        observed_counts = {
            partition: sum(source.partition == partition for source in self.sources)
            for partition in expected_counts
        }
        if observed_counts != expected_counts or self.partition_counts != expected_counts:
            raise ValueError("GUM V9.2.0 baseline partitions must contain exactly 165/24/24 documents")

        blocker_set = set(self.blockers)
        if self.official_scorer is None:
            if BaselineAuthorityBlocker.OFFICIAL_SCORER_UNAVAILABLE not in blocker_set:
                raise ValueError("a missing official scorer requires an explicit unavailable blocker")
            if self.scorer_parity_receipt_sha256 is not None:
                raise ValueError("scorer parity cannot be claimed without an official scorer artifact")
        if self.scorer_parity_receipt_sha256 is None:
            if BaselineAuthorityBlocker.SCORER_PARITY_UNVERIFIED not in blocker_set:
                raise ValueError("missing scorer parity requires an explicit unverified blocker")

        expected_ready = (
            self.official_scorer is not None
            and self.scorer_parity_receipt_sha256 is not None
            and not self.blockers
        )
        if self.ready_for_reproduction != expected_ready:
            raise ValueError("ready_for_reproduction does not reflect scorer authority and parity")

        expected_hash = _canonical_hash(self)
        if self.receipt_sha256 and self.receipt_sha256 != expected_hash:
            raise ValueError("baseline authority receipt SHA-256 does not match canonical content")
        object.__setattr__(self, "receipt_sha256", expected_hash)
        return self


class BaselineReproductionDiagnosis(BaseModel):
    """Hashed evidence that no baseline or architecture run was permitted."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0"
    package_version: str = PACKAGE_VERSION
    authority_receipt_sha256: str = Field(pattern=_SHA256_PATTERN)
    planned_seeds: tuple[int, ...] = (17, 29, 42, 73, 101)
    planned_settings: tuple[BaselineEvaluationSetting, ...] = (
        BaselineEvaluationSetting.GOLD_GOLD,
        BaselineEvaluationSetting.PREDICTED_PREDICTED,
    )
    blockers: tuple[BaselineAuthorityBlocker, ...] = Field(min_length=1)
    runs_started: int = 0
    training_data_accessed: bool = False
    test_data_accessed: bool = False
    architecture_screening_allowed: bool = False
    canonical_checkpoint: None = None
    allowed_claims: tuple[str, ...] = (
        "corrected eRST interfaces",
        "paper-defined scorer adapter",
        "no benchmark reproduction claim",
        "no SOTA claim",
    )
    receipt_sha256: str = ""

    @model_validator(mode="after")
    def validate_blocked_diagnosis(self) -> "BaselineReproductionDiagnosis":
        if self.planned_seeds != (17, 29, 42, 73, 101):
            raise ValueError("baseline diagnosis must retain all five required seeds")
        expected_settings = (
            BaselineEvaluationSetting.GOLD_GOLD,
            BaselineEvaluationSetting.PREDICTED_PREDICTED,
        )
        if self.planned_settings != expected_settings:
            raise ValueError("baseline diagnosis must retain both required evaluation settings")
        if self.runs_started != 0:
            raise ValueError("a blocked baseline diagnosis cannot report started runs")
        if self.training_data_accessed or self.test_data_accessed or self.architecture_screening_allowed:
            raise ValueError("blocked baseline diagnosis cannot report data access or architecture permission")
        if self.canonical_checkpoint is not None:
            raise ValueError("blocked baseline diagnosis cannot name a canonical checkpoint")
        expected_hash = _canonical_hash(self)
        if self.receipt_sha256 and self.receipt_sha256 != expected_hash:
            raise ValueError("baseline diagnosis SHA-256 does not match canonical content")
        object.__setattr__(self, "receipt_sha256", expected_hash)
        return self


class MandatorySystemDisposition(BaseModel):
    """No-run status for one system that remains mandatory in the frozen protocol."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    system: MandatoryResearchSystem
    status: ResearchSystemStatus = ResearchSystemStatus.BLOCKED_BY_BASELINE_AUTHORITY
    implementation_started: bool = False
    screening_runs_started: int = 0

    @model_validator(mode="after")
    def validate_no_run(self) -> "MandatorySystemDisposition":
        if self.implementation_started or self.screening_runs_started != 0:
            raise ValueError("baseline-blocked systems cannot report implementation or screening")
        return self


class ResearchProgramDiagnosis(BaseModel):
    """Hashed proof that all mandatory systems were retained and none was run."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0"
    package_version: str = PACKAGE_VERSION
    authority_receipt_sha256: str = Field(pattern=_SHA256_PATTERN)
    baseline_diagnosis_sha256: str = Field(pattern=_SHA256_PATTERN)
    systems: tuple[MandatorySystemDisposition, ...]
    test_data_accessed: bool = False
    test2_data_accessed: bool = False
    ablation_runs_started: int = 0
    bootstrap_resamples_run: int = 0
    calibration_fitted: bool = False
    receipt_sha256: str = ""

    @model_validator(mode="after")
    def validate_blocked_program(self) -> "ResearchProgramDiagnosis":
        observed = tuple(disposition.system for disposition in self.systems)
        expected = tuple(MandatoryResearchSystem)
        if observed != expected:
            raise ValueError("research diagnosis must retain every mandatory system exactly once in protocol order")
        if (
            self.test_data_accessed
            or self.test2_data_accessed
            or self.ablation_runs_started != 0
            or self.bootstrap_resamples_run != 0
            or self.calibration_fitted
        ):
            raise ValueError("baseline-blocked research cannot access evaluation data or report analyses")
        expected_hash = _canonical_hash(self)
        if self.receipt_sha256 and self.receipt_sha256 != expected_hash:
            raise ValueError("research diagnosis SHA-256 does not match canonical content")
        object.__setattr__(self, "receipt_sha256", expected_hash)
        return self


class PromotionGateResult(BaseModel):
    """One promotion threshold and the evidence that determined it."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    gate: PromotionGateName
    passed: bool
    evidence_sha256: str = Field(pattern=_SHA256_PATTERN)
    reason: str = Field(min_length=1)


class PromotionDecision(BaseModel):
    """Conjunctive, fail-closed canonical-checkpoint promotion decision."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0"
    package_version: str = PACKAGE_VERSION
    outcome: PromotionOutcome
    authority_receipt_sha256: str = Field(pattern=_SHA256_PATTERN)
    baseline_diagnosis_sha256: str = Field(pattern=_SHA256_PATTERN)
    research_diagnosis_sha256: str = Field(pattern=_SHA256_PATTERN)
    gates: tuple[PromotionGateResult, ...]
    champion_manifest_sha256: str | None = Field(default=None, pattern=_SHA256_PATTERN)
    canonical_checkpoint_manifest_sha256: str | None = Field(default=None, pattern=_SHA256_PATTERN)
    test_data_accessed: bool
    test2_data_accessed: bool
    upload_permitted: bool
    allowed_claims: tuple[str, ...]
    receipt_sha256: str = ""

    @model_validator(mode="after")
    def validate_promotion(self) -> "PromotionDecision":
        observed = tuple(result.gate for result in self.gates)
        expected = tuple(PromotionGateName)
        if observed != expected:
            raise ValueError("promotion decision must evaluate every gate exactly once in protocol order")
        all_passed = all(result.passed for result in self.gates)
        if self.outcome == PromotionOutcome.PROMOTE:
            if not all_passed:
                raise ValueError("promotion requires every gate to pass")
            if self.champion_manifest_sha256 is None or self.canonical_checkpoint_manifest_sha256 is None:
                raise ValueError("promotion requires champion and checkpoint manifests")
            if not self.test_data_accessed or not self.upload_permitted:
                raise ValueError("promotion requires final test evidence and upload permission")
        else:
            if all_passed:
                raise ValueError("no-promotion requires at least one failed gate")
            if self.champion_manifest_sha256 is not None or self.canonical_checkpoint_manifest_sha256 is not None:
                raise ValueError("no-promotion cannot name a champion or canonical checkpoint")
            if self.upload_permitted:
                raise ValueError("no-promotion cannot permit model upload")
            forbidden_claim_fragments = ("sota", "state of the art", "champion", "best")
            if any(
                fragment in claim.casefold()
                for claim in self.allowed_claims
                for fragment in forbidden_claim_fragments
            ):
                raise ValueError("no-promotion allowed claims cannot imply benchmark leadership")
        expected_hash = _canonical_hash(self)
        if self.receipt_sha256 and self.receipt_sha256 != expected_hash:
            raise ValueError("promotion decision SHA-256 does not match canonical content")
        object.__setattr__(self, "receipt_sha256", expected_hash)
        return self


__all__ = [
    "BASELINE_AUTHORITY_SCHEMA_VERSION",
    "AuthoritySearchEvidence",
    "BaselineAuthorityBlocker",
    "BaselineCorpusSource",
    "BaselineDirection",
    "BaselineEvaluationSetting",
    "BaselineReproductionDiagnosis",
    "BaselineSignalLocation",
    "ErstBaselineAuthorityReceipt",
    "MandatoryResearchSystem",
    "MandatorySystemDisposition",
    "ModelRevisionAuthority",
    "PromotionDecision",
    "PromotionGateName",
    "PromotionGateResult",
    "PromotionOutcome",
    "PublishedBaselineExample",
    "ResearchProgramDiagnosis",
    "ResearchArtifact",
    "ResearchSystemStatus",
]
