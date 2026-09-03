"""Pydantic boundaries for private GUM/eRST corpus loading and partitioning."""

from datetime import datetime
from enum import StrEnum
import hashlib
import json
from pathlib import PurePosixPath
import re

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from rdam.rst._version import PACKAGE_VERSION

_SHA256_PATTERN = r"^[0-9a-f]{64}$"
_GIT_REVISION_PATTERN = r"^[0-9a-f]{40}$"

CORPUS_RECEIPT_SCHEMA_VERSION = "1.0"
SPLIT_MANIFEST_SCHEMA_VERSION = "1.0"
CORPUS_AUTHORITY_SCHEMA_VERSION = "1.0"
CANDIDATE_SELECTION_SCHEMA_VERSION = "1.0"
PRIVATE_CORPUS_VERIFICATION_SCHEMA_VERSION = "1.0"
ERST_DECODER_SCHEMA_VERSION = "1.0"
TOKENIZER_PROBE_SCHEMA_VERSION = "1.0"
RAW_RELATION_INVENTORY_SCHEMA_VERSION = "1.0"
ERST_CHECKPOINT_SCHEMA_VERSION = "1.0"


class CorpusPartition(StrEnum):
    """Official GUM document partitions."""

    TRAIN = "train"
    DEV = "dev"
    TEST = "test"
    TEST2 = "test2"


class CorpusLicenseClass(StrEnum):
    """Conservative release-safety class for underlying document text."""

    CC_BY = "cc_by"
    CC_BY_SA = "cc_by_sa"
    NON_COMMERCIAL = "non_commercial"
    RESTRICTED = "restricted"
    UNKNOWN = "unknown"


class CorpusFailureType(StrEnum):
    """Stable machine-readable corpus failure categories."""

    MISSING_CORPUS = "missing_corpus"
    MISSING_AUTHORITY = "missing_authority"
    INVALID_AUTHORITY = "invalid_authority"
    UNAUTHORIZED_DOCUMENT = "unauthorized_document"
    INVALID_RS4 = "invalid_rs4"
    UNSAFE_SOURCE = "unsafe_source"
    ZERO_CANDIDATES = "zero_candidates"
    DUPLICATE_DOCUMENT = "duplicate_document"
    DUPLICATE_SOURCE = "duplicate_source"


class HardNegativeStrategy(StrEnum):
    """Frozen training-negative ranking algorithms."""

    STRUCTURAL_COMPATIBILITY_V1 = "structural_compatibility_v1"


class DecodeRejectionReason(StrEnum):
    """The only formal reasons an above-threshold eRST edge may be rejected."""

    INSUFFICIENT_SIGNAL = "insufficient_signal"
    SELF_LOOP = "self_loop"
    INVENTED_NODE = "invented_node"
    DUPLICATE_DIRECTED_PAIR = "duplicate_directed_pair"


class ErstCheckpointFileRole(StrEnum):
    """Closed inventory of safe eRST completion-bundle member roles."""

    SCORER_STATE = "scorer_state"
    SCORER_CONFIG = "scorer_config"
    ENCODER_CONFIG = "encoder_config"
    TOKENIZER = "tokenizer"
    SIGNAL_CONFIG = "signal_config"
    GRAPH_CONFIG = "graph_config"
    GRAPH_STATE = "graph_state"
    CALIBRATION = "calibration"
    RELATION_INVENTORY = "relation_inventory"
    ONTOLOGY_MAPPING = "ontology_mapping"
    DECODER_CONFIG = "decoder_config"
    TEST_VECTOR = "test_vector"


def _validate_relative_source_path(value: str) -> str:
    path = PurePosixPath(value)
    if not value or path.is_absolute() or ".." in path.parts or "\\" in value:
        raise ValueError("corpus source_path must be a sanitized relative POSIX path")
    return value


def _canonical_model_hash(model: BaseModel, *, exclude: set[str]) -> str:
    payload = model.model_dump(mode="json", exclude=exclude)
    encoded = json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode()
    return hashlib.sha256(encoded).hexdigest()


class CorpusLoadFailure(BaseModel):
    """Sanitized failure for one source or corpus-level load step."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_path: str | None = None
    document_id: str | None = None
    failure_type: CorpusFailureType
    message: str = Field(min_length=1, max_length=500)
    exception_type: str = Field(min_length=1)

    @field_validator("source_path")
    @classmethod
    def validate_source_path(cls, value: str | None) -> str | None:
        return _validate_relative_source_path(value) if value is not None else None


class CorpusAuthorityEntry(BaseModel):
    """One document assignment derived from immutable upstream authority."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    document_id: str = Field(pattern=r"^(?:GUM|GENTLE)_[a-z0-9]+_[a-z0-9]+$")
    partition: CorpusPartition
    license_class: CorpusLicenseClass


class GumCorpusAuthority(BaseModel):
    """Hashed interpretation of pinned GUM split and licence authorities."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = CORPUS_AUTHORITY_SCHEMA_VERSION
    corpus_revision: str = Field(pattern=_GIT_REVISION_PATTERN)
    splits_sha256: str = Field(pattern=_SHA256_PATTERN)
    license_inventory_sha256: str = Field(pattern=_SHA256_PATTERN)
    gentle_license_revision: str = Field(pattern=_GIT_REVISION_PATTERN)
    entries: tuple[CorpusAuthorityEntry, ...] = Field(min_length=1)
    authority_sha256: str = ""

    @model_validator(mode="after")
    def validate_authority(self) -> GumCorpusAuthority:
        seen: set[str] = set()
        for entry in self.entries:
            if entry.document_id in seen:
                raise ValueError(f"duplicate document in split authority: {entry.document_id}")
            seen.add(entry.document_id)
        expected = _canonical_model_hash(self, exclude={"authority_sha256"})
        if self.authority_sha256 and self.authority_sha256 != expected:
            raise ValueError("corpus authority SHA-256 does not match its canonical content")
        object.__setattr__(self, "authority_sha256", expected)
        return self

    def entry_for(self, document_id: str) -> CorpusAuthorityEntry | None:
        """Return the upstream authority entry for one exact document ID."""

        return next((entry for entry in self.entries if entry.document_id == document_id), None)


class CorpusDocumentReceipt(BaseModel):
    """Private-text-free receipt for one accepted GUM document."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    document_id: str = Field(min_length=1)
    source_path: str
    source_sha256: str = Field(pattern=_SHA256_PATTERN)
    corpus_revision: str = Field(pattern=_GIT_REVISION_PATTERN)
    partition: CorpusPartition
    license_class: CorpusLicenseClass
    node_count: int = Field(gt=0)
    edu_count: int = Field(gt=0)
    primary_edge_count: int = Field(ge=0)
    candidate_count: int = Field(gt=0)
    secondary_edge_count: int = Field(ge=0)
    signal_count: int = Field(gt=0)
    raw_relation_inventory: tuple[str, ...]
    succeeded: bool = True

    @field_validator("source_path")
    @classmethod
    def validate_source_path(cls, value: str) -> str:
        return _validate_relative_source_path(value)

    @field_validator("raw_relation_inventory")
    @classmethod
    def validate_relation_inventory(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if any(not relation for relation in value):
            raise ValueError("raw relation inventory cannot contain empty labels")
        if len(value) != len(set(value)) or value != tuple(sorted(value)):
            raise ValueError("raw relation inventory must be unique and sorted")
        return value

    @model_validator(mode="after")
    def validate_success(self) -> CorpusDocumentReceipt:
        if not self.succeeded:
            raise ValueError("accepted document receipts must be successful")
        return self


class CorpusLoadReceipt(BaseModel):
    """Reconciled receipt for a complete or explicitly partial corpus load."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = CORPUS_RECEIPT_SCHEMA_VERSION
    package_version: str = PACKAGE_VERSION
    corpus_revision: str = Field(pattern=_GIT_REVISION_PATTERN)
    corpus_root_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    fail_on_error: bool
    documents: tuple[CorpusDocumentReceipt, ...]
    failures: tuple[CorpusLoadFailure, ...]
    document_count: int = Field(ge=0)
    candidate_count: int = Field(ge=0)
    secondary_edge_count: int = Field(ge=0)
    signal_count: int = Field(ge=0)
    succeeded: bool
    receipt_sha256: str = ""

    @model_validator(mode="after")
    def validate_reconciliation(self) -> CorpusLoadReceipt:
        expected_counts = {
            "document_count": len(self.documents),
            "candidate_count": sum(document.candidate_count for document in self.documents),
            "secondary_edge_count": sum(document.secondary_edge_count for document in self.documents),
            "signal_count": sum(document.signal_count for document in self.documents),
        }
        for field_name, expected_value in expected_counts.items():
            if getattr(self, field_name) != expected_value:
                raise ValueError(f"{field_name} does not reconcile with document receipts")
        expected_success = bool(self.documents) and self.candidate_count > 0 and not self.failures
        if self.succeeded != expected_success:
            raise ValueError("corpus receipt succeeded flag does not reflect documents, candidates, and failures")
        if any(document.corpus_revision != self.corpus_revision for document in self.documents):
            raise ValueError("document corpus revisions must match the load receipt")
        expected_hash = _canonical_model_hash(self, exclude={"receipt_sha256"})
        if self.receipt_sha256 and self.receipt_sha256 != expected_hash:
            raise ValueError("corpus receipt SHA-256 does not match its canonical content")
        object.__setattr__(self, "receipt_sha256", expected_hash)
        return self


class SplitManifest(BaseModel):
    """Document-level split evidence with leakage prevention."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = SPLIT_MANIFEST_SCHEMA_VERSION
    corpus_revision: str = Field(pattern=_GIT_REVISION_PATTERN)
    split_authority_sha256: str = Field(pattern=_SHA256_PATTERN)
    documents: tuple[CorpusDocumentReceipt, ...] = Field(min_length=1)
    partition_document_ids: dict[CorpusPartition, tuple[str, ...]] = Field(
        default_factory=lambda: dict[CorpusPartition, tuple[str, ...]]()
    )
    partition_source_sha256: dict[CorpusPartition, tuple[str, ...]] = Field(
        default_factory=lambda: dict[CorpusPartition, tuple[str, ...]]()
    )
    partition_counts: dict[CorpusPartition, int] = Field(default_factory=lambda: dict[CorpusPartition, int]())
    manifest_sha256: str = ""

    @model_validator(mode="after")
    def validate_disjointness(self) -> SplitManifest:
        document_ids: set[str] = set()
        source_hashes: set[str] = set()
        for document in self.documents:
            if document.corpus_revision != self.corpus_revision:
                raise ValueError("split document corpus revisions must match the manifest")
            if document.document_id in document_ids:
                raise ValueError(f"document ID is present in multiple partitions: {document.document_id}")
            if document.source_sha256 in source_hashes:
                raise ValueError(f"source SHA-256 is present in multiple partitions: {document.source_sha256}")
            document_ids.add(document.document_id)
            source_hashes.add(document.source_sha256)

        expected_ids = {
            partition: tuple(
                sorted(document.document_id for document in self.documents if document.partition == partition)
            )
            for partition in CorpusPartition
        }
        expected_hashes = {
            partition: tuple(
                sorted(document.source_sha256 for document in self.documents if document.partition == partition)
            )
            for partition in CorpusPartition
        }
        expected_counts = {partition: len(expected_ids[partition]) for partition in CorpusPartition}
        for field_name, actual, expected in (
            ("partition_document_ids", self.partition_document_ids, expected_ids),
            ("partition_source_sha256", self.partition_source_sha256, expected_hashes),
            ("partition_counts", self.partition_counts, expected_counts),
        ):
            if actual and actual != expected:
                raise ValueError(f"{field_name} does not reconcile with document receipts")
            object.__setattr__(self, field_name, expected)

        expected_hash = _canonical_model_hash(self, exclude={"manifest_sha256"})
        if self.manifest_sha256 and self.manifest_sha256 != expected_hash:
            raise ValueError("split manifest SHA-256 does not match its canonical content")
        object.__setattr__(self, "manifest_sha256", expected_hash)
        return self

    def documents_for(self, partition: CorpusPartition) -> tuple[CorpusDocumentReceipt, ...]:
        """Return documents in one official partition without flattening candidates."""

        return tuple(document for document in self.documents if document.partition == partition)


class HardNegativeSamplingConfig(BaseModel):
    """Deterministic training-only hard-negative selection configuration."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = CANDIDATE_SELECTION_SCHEMA_VERSION
    strategy: HardNegativeStrategy = HardNegativeStrategy.STRUCTURAL_COMPATIBILITY_V1
    negative_to_positive_ratio: float = Field(gt=0)
    seed: int = Field(ge=0)
    config_sha256: str = ""

    @model_validator(mode="after")
    def validate_config_hash(self) -> HardNegativeSamplingConfig:
        expected = _canonical_model_hash(self, exclude={"config_sha256"})
        if self.config_sha256 and self.config_sha256 != expected:
            raise ValueError("hard-negative config SHA-256 does not match its canonical content")
        object.__setattr__(self, "config_sha256", expected)
        return self


class CandidateDocumentSelection(BaseModel):
    """Complete-versus-selected counts for one already-partitioned document."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    document_id: str = Field(min_length=1)
    complete_count: int = Field(ge=0)
    selected_count: int = Field(ge=0)
    positive_count: int = Field(ge=0)
    selected_positive_count: int = Field(ge=0)
    negative_count: int = Field(ge=0)
    selected_negative_count: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_counts(self) -> CandidateDocumentSelection:
        if self.complete_count != self.positive_count + self.negative_count:
            raise ValueError("complete candidate count does not reconcile")
        if self.selected_count != self.selected_positive_count + self.selected_negative_count:
            raise ValueError("selected candidate count does not reconcile")
        if self.selected_positive_count != self.positive_count:
            raise ValueError("hard-negative sampling cannot remove positive candidates")
        if self.selected_negative_count > self.negative_count:
            raise ValueError("selected negatives cannot exceed complete negatives")
        return self


class CandidateSelectionReceipt(BaseModel):
    """Hashed evidence that only train candidates were sampled."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = CANDIDATE_SELECTION_SCHEMA_VERSION
    partition: CorpusPartition
    sampling_applied: bool
    config_sha256: str | None = None
    documents: tuple[CandidateDocumentSelection, ...]
    complete_count: int = Field(ge=0)
    selected_count: int = Field(ge=0)
    selected_identity_sha256: str = Field(pattern=_SHA256_PATTERN)

    @model_validator(mode="after")
    def validate_selection(self) -> CandidateSelectionReceipt:
        if self.complete_count != sum(document.complete_count for document in self.documents):
            raise ValueError("complete selection count does not reconcile with documents")
        if self.selected_count != sum(document.selected_count for document in self.documents):
            raise ValueError("selected selection count does not reconcile with documents")
        if self.sampling_applied != (self.partition == CorpusPartition.TRAIN):
            raise ValueError("hard-negative sampling is permitted only for the train partition")
        if self.sampling_applied and self.config_sha256 is None:
            raise ValueError("train selection receipt requires a sampling config SHA-256")
        if not self.sampling_applied and self.config_sha256 is not None:
            raise ValueError("evaluation selection receipts cannot carry sampling configuration")
        if not self.sampling_applied and self.selected_count != self.complete_count:
            raise ValueError("dev/test/test2 must retain the complete candidate space")
        return self


class CorpusSourceIdentity(BaseModel):
    """Text-free identity for one source in a private corpus checkout."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    document_id: str = Field(min_length=1)
    source_path: str
    source_sha256: str = Field(pattern=_SHA256_PATTERN)
    partition: CorpusPartition
    license_class: CorpusLicenseClass

    @field_validator("source_path")
    @classmethod
    def validate_source_path(cls, value: str) -> str:
        return _validate_relative_source_path(value)


class CandidateIdentityProbe(BaseModel):
    """Determinism evidence for one private document without candidate text."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    document_id: str = Field(min_length=1)
    partition: CorpusPartition
    candidate_count: int = Field(gt=0)
    candidate_identity_sha256: str = Field(pattern=_SHA256_PATTERN)


class PrivateCorpusVerificationReceipt(BaseModel):
    """Full-source and sampled-candidate verification for the private corpus."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = PRIVATE_CORPUS_VERIFICATION_SCHEMA_VERSION
    corpus_revision: str = Field(pattern=_GIT_REVISION_PATTERN)
    authority_sha256: str = Field(pattern=_SHA256_PATTERN)
    corpus_root_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    sources: tuple[CorpusSourceIdentity, ...] = Field(min_length=1)
    partition_counts: dict[CorpusPartition, int]
    candidate_probes: tuple[CandidateIdentityProbe, ...]
    succeeded: bool
    receipt_sha256: str = ""

    @model_validator(mode="after")
    def validate_private_corpus(self) -> PrivateCorpusVerificationReceipt:
        document_ids = [source.document_id for source in self.sources]
        source_hashes = [source.source_sha256 for source in self.sources]
        if len(document_ids) != len(set(document_ids)):
            raise ValueError("private corpus source document IDs are not disjoint")
        if len(source_hashes) != len(set(source_hashes)):
            raise ValueError("private corpus source hashes are not disjoint")
        expected_counts = {
            partition: sum(source.partition == partition for source in self.sources) for partition in CorpusPartition
        }
        if self.partition_counts != expected_counts:
            raise ValueError("private corpus partition counts do not reconcile")
        probe_partitions = {probe.partition for probe in self.candidate_probes}
        if probe_partitions != set(CorpusPartition):
            raise ValueError("private corpus requires one candidate probe for every partition")
        if any(probe.document_id not in document_ids for probe in self.candidate_probes):
            raise ValueError("candidate probe document is absent from private corpus sources")
        if not self.succeeded:
            raise ValueError("a private corpus verification receipt cannot claim an unsuccessful result")
        expected_hash = _canonical_model_hash(self, exclude={"receipt_sha256"})
        if self.receipt_sha256 and self.receipt_sha256 != expected_hash:
            raise ValueError("private corpus receipt SHA-256 does not match its canonical content")
        object.__setattr__(self, "receipt_sha256", expected_hash)
        return self


class ErstDecoderConfig(BaseModel):
    """Immutable threshold and raw-relation inventory for eRST decoding."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = ERST_DECODER_SCHEMA_VERSION
    edge_threshold: float = Field(ge=0.0, le=1.0)
    raw_relation_inventory: tuple[str, ...] = Field(min_length=1)
    config_sha256: str = ""

    @field_validator("raw_relation_inventory")
    @classmethod
    def validate_raw_relations(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if any(not relation.strip() for relation in value):
            raise ValueError("decoder raw relations must be non-empty")
        if len(value) != len(set(value)):
            raise ValueError("decoder raw relation inventory must be unique")
        return value

    @model_validator(mode="after")
    def validate_config_hash(self) -> ErstDecoderConfig:
        expected = _canonical_model_hash(self, exclude={"config_sha256"})
        if self.config_sha256 and self.config_sha256 != expected:
            raise ValueError("decoder config SHA-256 does not match its canonical content")
        object.__setattr__(self, "config_sha256", expected)
        return self


class ErstDecodeReceipt(BaseModel):
    """Reconciled proof of threshold selection and formal eRST constraints."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = ERST_DECODER_SCHEMA_VERSION
    candidate_count: int = Field(ge=0)
    streamed_batch_count: int = Field(ge=0)
    below_threshold_count: int = Field(ge=0)
    accepted_count: int = Field(ge=0)
    formal_rejections: dict[DecodeRejectionReason, int]
    output_edge_ids: tuple[str, ...]
    decoder_config_sha256: str = Field(pattern=_SHA256_PATTERN)

    @model_validator(mode="after")
    def validate_decode_counts(self) -> ErstDecodeReceipt:
        if set(self.formal_rejections) != set(DecodeRejectionReason):
            raise ValueError("decode receipt must enumerate every formal rejection reason")
        if any(count < 0 for count in self.formal_rejections.values()):
            raise ValueError("formal rejection counts cannot be negative")
        accounted = self.below_threshold_count + self.accepted_count + sum(self.formal_rejections.values())
        if accounted != self.candidate_count:
            raise ValueError("decode receipt counts do not reconcile")
        if self.accepted_count != len(self.output_edge_ids):
            raise ValueError("accepted decode count does not match output edge IDs")
        if self.candidate_count and self.streamed_batch_count < 1:
            raise ValueError("non-empty decoding requires at least one streamed batch")
        return self


class TokenizerProbeResult(BaseModel):
    """One pinned tokenizer's fast/parity/MPS compatibility evidence."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    model_id: str = Field(min_length=1)
    revision: str = Field(pattern=_GIT_REVISION_PATTERN)
    tokenizer_class: str | None = None
    is_fast: bool
    encoding_sha256: str | None = Field(default=None, pattern=_SHA256_PATTERN)
    local_reload_sha256: str | None = Field(default=None, pattern=_SHA256_PATTERN)
    local_reload_equal: bool
    mps_tensor_roundtrip: bool
    succeeded: bool
    failure_type: str | None = None
    failure_message: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def validate_probe(self) -> TokenizerProbeResult:
        success_evidence = (
            self.is_fast
            and self.encoding_sha256 is not None
            and self.local_reload_sha256 == self.encoding_sha256
            and self.local_reload_equal
            and self.mps_tensor_roundtrip
            and self.failure_type is None
            and self.failure_message is None
        )
        if self.succeeded != success_evidence:
            raise ValueError("tokenizer probe success does not reflect compatibility evidence")
        if not self.succeeded and (self.failure_type is None or self.failure_message is None):
            raise ValueError("failed tokenizer probes require typed failure evidence")
        return self


class TokenizerCompatibilityReceipt(BaseModel):
    """Hashed Python/Transformers/MPS compatibility receipt for mandatory tokenizers."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = TOKENIZER_PROBE_SCHEMA_VERSION
    package_version: str = PACKAGE_VERSION
    python_version: str = Field(min_length=1)
    transformers_version: str = Field(min_length=1)
    tokenizers_version: str = Field(min_length=1)
    mps_available: bool
    probes: tuple[TokenizerProbeResult, ...] = Field(min_length=1)
    succeeded: bool
    receipt_sha256: str = ""

    @model_validator(mode="after")
    def validate_compatibility(self) -> TokenizerCompatibilityReceipt:
        model_revisions = {(probe.model_id, probe.revision) for probe in self.probes}
        if len(model_revisions) != len(self.probes):
            raise ValueError("tokenizer probes must have unique model/revision identities")
        if self.succeeded != (self.mps_available and all(probe.succeeded for probe in self.probes)):
            raise ValueError("tokenizer compatibility success does not reflect probe evidence")
        expected_hash = _canonical_model_hash(self, exclude={"receipt_sha256"})
        if self.receipt_sha256 and self.receipt_sha256 != expected_hash:
            raise ValueError("tokenizer receipt SHA-256 does not match its canonical content")
        object.__setattr__(self, "receipt_sha256", expected_hash)
        return self


class ErstCheckpointFile(BaseModel):
    """One declared, content-addressed file in an eRST completion bundle."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str
    role: ErstCheckpointFileRole
    size_bytes: int = Field(gt=0)
    sha256: str = Field(pattern=_SHA256_PATTERN)

    @field_validator("path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        normalized = _validate_relative_source_path(value)
        if normalized == "manifest.json":
            raise ValueError("manifest.json cannot inventory itself")
        if PurePosixPath(normalized).suffix.casefold() in {
            ".bin",
            ".ckpt",
            ".joblib",
            ".pickle",
            ".pkl",
            ".pt",
            ".pth",
        }:
            raise ValueError("pickle-capable model artifacts are forbidden")
        return normalized


class ErstCheckpointComponent(BaseModel):
    """Reload contract for one explicit eRST completion component."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    component_id: str = Field(min_length=1)
    architecture: str = Field(min_length=1)
    config_file: str
    state_file: str | None

    @field_validator("config_file", "state_file")
    @classmethod
    def validate_component_path(cls, value: str | None) -> str | None:
        return _validate_relative_source_path(value) if value is not None else None


class ErstFeatureSchema(BaseModel):
    """Content identities for every feature and decoding contract."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    signal_detector_sha256: str = Field(pattern=_SHA256_PATTERN)
    candidate_schema_sha256: str = Field(pattern=_SHA256_PATTERN)
    structural_feature_sha256: str = Field(pattern=_SHA256_PATTERN)
    raw_relation_inventory_sha256: str = Field(pattern=_SHA256_PATTERN)
    ontology_mapping_sha256: str = Field(pattern=_SHA256_PATTERN)
    decoder_config_sha256: str = Field(pattern=_SHA256_PATTERN)


class ErstCheckpointResearchEvidence(BaseModel):
    """Immutable experiment evidence used to construct a checkpoint."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    corpus_revision: str = Field(pattern=_GIT_REVISION_PATTERN)
    corpus_receipt_sha256: str = Field(pattern=_SHA256_PATTERN)
    split_manifest_sha256: str = Field(pattern=_SHA256_PATTERN)
    experiment_protocol_sha256: str = Field(pattern=_SHA256_PATTERN)
    champion_manifest_sha256: str | None = Field(default=None, pattern=_SHA256_PATTERN)
    run_receipt_sha256: str = Field(pattern=_SHA256_PATTERN)
    final_evaluation_sha256: str | None = Field(default=None, pattern=_SHA256_PATTERN)
    selection_decision_sha256: str | None = Field(default=None, pattern=_SHA256_PATTERN)


class ErstCheckpointMetrics(BaseModel):
    """Official secondary, calibration, runtime, and parity evidence."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    span_f: float = Field(ge=0.0, le=1.0)
    direction_f: float = Field(ge=0.0, le=1.0)
    relation_f: float = Field(ge=0.0, le=1.0)
    full_f: float = Field(ge=0.0, le=1.0)
    ece: float = Field(ge=0.0, le=1.0)
    brier: float = Field(ge=0.0, le=1.0)
    mps_p95_latency_ms: float | None = Field(default=None, gt=0.0)
    peak_rss_bytes: int | None = Field(default=None, gt=0)
    cpu_mps_graphs_equivalent: bool | None = None


class ErstCalibrationState(BaseModel):
    """Dev-fitted edge calibration and decision threshold."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0"
    temperature: float = Field(gt=0.0)
    edge_threshold: float = Field(ge=0.0, le=1.0)
    calibrated: bool
    fitted_partition: CorpusPartition

    @model_validator(mode="after")
    def require_dev_calibration(self) -> ErstCalibrationState:
        if self.fitted_partition != CorpusPartition.DEV:
            raise ValueError("eRST calibration may be fitted on dev only")
        return self


class ErstScorerConfig(BaseModel):
    """Architecture fields required to reconstruct a scorer without network access."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0"
    model_type: str = Field(min_length=1)
    num_struct_features: int = Field(gt=0)
    projection_dimension: int = Field(gt=0)
    parameter_dtype: str = Field(pattern=r"^float(?:16|32|64)$|^bfloat16$")
    raw_relation_inventory: tuple[str, ...] = Field(min_length=1)

    @field_validator("raw_relation_inventory")
    @classmethod
    def validate_scorer_relations(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)) or any(not relation for relation in value):
            raise ValueError("scorer raw relation inventory must be non-empty and unique")
        return value


class ErstGraphComponentConfig(BaseModel):
    """Explicit graph-component declaration, including the state-free case."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0"
    architecture: str = Field(min_length=1)
    feature_schema_sha256: str = Field(pattern=_SHA256_PATTERN)
    has_learned_state: bool


class ErstCheckpointTestVector(BaseModel):
    """Synthetic end-to-end reload vector bundled without private corpus text."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0"
    vector_id: str = Field(min_length=1)
    document_json: str = Field(min_length=2)
    primary_analysis_json: str = Field(min_length=2)
    expected_analysis_json: str = Field(min_length=2)

    @field_validator("document_json", "primary_analysis_json", "expected_analysis_json")
    @classmethod
    def require_json_object(cls, value: str) -> str:
        parsed = json.loads(value)
        if not isinstance(parsed, dict):
            raise ValueError("checkpoint test-vector payloads must be JSON objects")
        return value


class ErstCheckpointVerificationReceipt(BaseModel):
    """Machine-readable proof that a bundle reloaded and passed its graph vector."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = ERST_CHECKPOINT_SCHEMA_VERSION
    package_version: str = PACKAGE_VERSION
    manifest_sha256: str = Field(pattern=_SHA256_PATTERN)
    device: str = Field(min_length=1)
    signal_count: int = Field(gt=0)
    secondary_edge_count: int = Field(gt=0)
    raw_relations: tuple[str, ...] = Field(min_length=1)
    verified: bool

    @model_validator(mode="after")
    def require_verified(self) -> ErstCheckpointVerificationReceipt:
        if not self.verified:
            raise ValueError("checkpoint verification receipt cannot represent an unverified bundle")
        if any(not relation for relation in self.raw_relations):
            raise ValueError("checkpoint verification receipt requires raw relation labels")
        return self


class ErstCheckpointLicenses(BaseModel):
    """Licence and release-policy evidence carried by every bundle."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    code_license: str = Field(min_length=1)
    base_model_license: str = Field(min_length=1)
    annotation_license: str = Field(min_length=1)
    underlying_text_policy: str = Field(min_length=1)
    private_only: bool

    @model_validator(mode="after")
    def require_private_bundle(self) -> ErstCheckpointLicenses:
        if not self.private_only:
            raise ValueError("mixed GUM underlying-text licences require a private eRST bundle")
        return self


class ErstCheckpointProvenance(BaseModel):
    """Producer and immutable source identity for one bundle construction."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    producer: str = Field(min_length=1)
    producer_version: str = Field(min_length=1)
    source_revision: str = Field(pattern=_GIT_REVISION_PATTERN)
    created_at: datetime
    private_hf_repository: str = Field(min_length=1)
    private_hf_revision: str | None = Field(default=None, pattern=_GIT_REVISION_PATTERN)

    @field_validator("created_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("checkpoint provenance timestamp must be timezone-aware")
        return value


class ErstCheckpointBuildSpec(BaseModel):
    """Authoritative inputs used to construct an eRST completion bundle."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    architecture: str = Field(min_length=1)
    upstream_revisions: dict[str, str] = Field(min_length=1)
    feature_schema: ErstFeatureSchema
    research: ErstCheckpointResearchEvidence
    metrics: ErstCheckpointMetrics
    licenses: ErstCheckpointLicenses
    provenance: ErstCheckpointProvenance
    release_eligible: bool = False

    @field_validator("upstream_revisions")
    @classmethod
    def validate_upstream_revisions(cls, value: dict[str, str]) -> dict[str, str]:
        if any(
            not name.strip() or re.fullmatch(_GIT_REVISION_PATTERN, revision) is None
            for name, revision in value.items()
        ):
            raise ValueError("upstream revisions require non-empty names and immutable Git revisions")
        return value

    @model_validator(mode="after")
    def validate_release_evidence(self) -> ErstCheckpointBuildSpec:
        if self.provenance.producer_version != PACKAGE_VERSION:
            raise ValueError("checkpoint producer version must equal the package version")
        if self.release_eligible:
            required = (
                self.research.champion_manifest_sha256,
                self.research.final_evaluation_sha256,
                self.research.selection_decision_sha256,
                self.metrics.mps_p95_latency_ms,
                self.metrics.peak_rss_bytes,
                self.metrics.cpu_mps_graphs_equivalent,
            )
            if any(item is None for item in required) or self.metrics.cpu_mps_graphs_equivalent is not True:
                raise ValueError("release-eligible checkpoints require complete selection and runtime evidence")
        return self


class ErstCheckpointManifest(BaseModel):
    """Complete, content-addressed authority for a reloadable eRST bundle."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = ERST_CHECKPOINT_SCHEMA_VERSION
    package_version: str = PACKAGE_VERSION
    architecture: str = Field(min_length=1)
    upstream_revisions: dict[str, str] = Field(min_length=1)
    files: tuple[ErstCheckpointFile, ...] = Field(min_length=1)
    components: tuple[ErstCheckpointComponent, ...] = Field(min_length=1)
    feature_schema: ErstFeatureSchema
    research: ErstCheckpointResearchEvidence
    metrics: ErstCheckpointMetrics
    licenses: ErstCheckpointLicenses
    provenance: ErstCheckpointProvenance
    release_eligible: bool
    manifest_sha256: str = ""

    @model_validator(mode="after")
    def validate_manifest(self) -> ErstCheckpointManifest:
        if self.package_version != PACKAGE_VERSION:
            raise ValueError("checkpoint package version does not match the installed package")
        paths = tuple(file.path for file in self.files)
        if len(paths) != len(set(paths)):
            raise ValueError("checkpoint file inventory contains duplicate paths")
        component_ids = tuple(component.component_id for component in self.components)
        if len(component_ids) != len(set(component_ids)):
            raise ValueError("checkpoint component inventory contains duplicate IDs")
        inventory = set(paths)
        for component in self.components:
            if component.config_file not in inventory:
                raise ValueError(f"component config is absent from the file inventory: {component.component_id}")
            if component.state_file is not None and component.state_file not in inventory:
                raise ValueError(f"component state is absent from the file inventory: {component.component_id}")
        build_spec = ErstCheckpointBuildSpec(
            architecture=self.architecture,
            upstream_revisions=self.upstream_revisions,
            feature_schema=self.feature_schema,
            research=self.research,
            metrics=self.metrics,
            licenses=self.licenses,
            provenance=self.provenance,
            release_eligible=self.release_eligible,
        )
        del build_spec
        expected_hash = _canonical_model_hash(self, exclude={"manifest_sha256"})
        if self.manifest_sha256 and self.manifest_sha256 != expected_hash:
            raise ValueError("checkpoint manifest SHA-256 does not match its canonical content")
        object.__setattr__(self, "manifest_sha256", expected_hash)
        return self


class RawRelationInventory(BaseModel):
    """Train-derived raw eRST labels with explicit ontology projections."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = RAW_RELATION_INVENTORY_SCHEMA_VERSION
    corpus_revision: str = Field(pattern=_GIT_REVISION_PATTERN)
    partition: CorpusPartition
    source_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    ontology_digest: str = Field(pattern=_SHA256_PATTERN)
    labels: tuple[str, ...] = Field(min_length=1)
    label_counts: dict[str, int]
    concept_by_raw: dict[str, str]
    edge_count: int = Field(gt=0)
    inventory_sha256: str = ""

    @model_validator(mode="after")
    def validate_inventory(self) -> RawRelationInventory:
        if self.partition != CorpusPartition.TRAIN:
            raise ValueError("raw relation inventory must be derived from train only")
        if self.labels != tuple(sorted(set(self.labels))):
            raise ValueError("raw relation inventory labels must be unique and sorted")
        label_set = set(self.labels)
        if set(self.label_counts) != label_set or set(self.concept_by_raw) != label_set:
            raise ValueError("raw relation counts and concepts must cover the exact label inventory")
        if any(count <= 0 for count in self.label_counts.values()):
            raise ValueError("raw relation label counts must be positive")
        if any(not concept for concept in self.concept_by_raw.values()):
            raise ValueError("raw relation concepts must be non-empty")
        if self.edge_count != sum(self.label_counts.values()):
            raise ValueError("raw relation edge count does not reconcile")
        expected_hash = _canonical_model_hash(self, exclude={"inventory_sha256"})
        if self.inventory_sha256 and self.inventory_sha256 != expected_hash:
            raise ValueError("raw relation inventory SHA-256 does not match its canonical content")
        object.__setattr__(self, "inventory_sha256", expected_hash)
        return self

    def index_for(self, raw_relation: str) -> int:
        """Return the exact class index for a raw GUM relation."""

        try:
            return self.labels.index(raw_relation)
        except ValueError as error:
            raise KeyError(f"raw eRST relation is absent from train inventory: {raw_relation}") from error


__all__ = [
    "CANDIDATE_SELECTION_SCHEMA_VERSION",
    "CORPUS_AUTHORITY_SCHEMA_VERSION",
    "CORPUS_RECEIPT_SCHEMA_VERSION",
    "ERST_CHECKPOINT_SCHEMA_VERSION",
    "ERST_DECODER_SCHEMA_VERSION",
    "PRIVATE_CORPUS_VERIFICATION_SCHEMA_VERSION",
    "RAW_RELATION_INVENTORY_SCHEMA_VERSION",
    "SPLIT_MANIFEST_SCHEMA_VERSION",
    "TOKENIZER_PROBE_SCHEMA_VERSION",
    "CandidateDocumentSelection",
    "CandidateIdentityProbe",
    "CandidateSelectionReceipt",
    "CorpusAuthorityEntry",
    "CorpusDocumentReceipt",
    "CorpusFailureType",
    "CorpusLicenseClass",
    "CorpusLoadFailure",
    "CorpusLoadReceipt",
    "CorpusPartition",
    "CorpusSourceIdentity",
    "DecodeRejectionReason",
    "ErstCalibrationState",
    "ErstCheckpointBuildSpec",
    "ErstCheckpointComponent",
    "ErstCheckpointFile",
    "ErstCheckpointFileRole",
    "ErstCheckpointLicenses",
    "ErstCheckpointManifest",
    "ErstCheckpointMetrics",
    "ErstCheckpointProvenance",
    "ErstCheckpointResearchEvidence",
    "ErstCheckpointTestVector",
    "ErstCheckpointVerificationReceipt",
    "ErstDecodeReceipt",
    "ErstDecoderConfig",
    "ErstFeatureSchema",
    "ErstGraphComponentConfig",
    "ErstScorerConfig",
    "GumCorpusAuthority",
    "HardNegativeSamplingConfig",
    "HardNegativeStrategy",
    "PrivateCorpusVerificationReceipt",
    "RawRelationInventory",
    "SplitManifest",
    "TokenizerCompatibilityReceipt",
    "TokenizerProbeResult",
]
