"""Typed lifecycle failures, monotonic evidence, and privacy-safe persistence."""

from enum import StrEnum
from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from rdam.rst.contracts import RstAnalysis
from rdam.rst.ingest.contracts.analysis import ProductionAnalysisOutcome, ValidationReceipt
from rdam.rst.ingest.contracts.base import (
    PRODUCTION_CONTRACT,
    WRITE_CONTRACT_VERSION,
    Sha256Identity,
    StrictContractModel,
)
from rdam.rst.ingest.contracts.inference import InferenceEvidence
from rdam.rst.ingest.contracts.preparation import PreparationOutcome
from rdam.rst.ingest.contracts.source import (
    ContentInventoryItem,
    RedactedContentRepresentation,
    SourceContractIdentity,
    SourceSummary,
)
from rdam.rst.ingest.identity import semantic_sha256


class LifecycleStage(StrEnum):
    ACQUISITION = "acquisition"
    CLASSIFICATION = "classification"
    PREPARATION = "preparation"
    PLANNING = "planning"
    INFERENCE = "inference"
    VALIDATION = "validation"
    ASSEMBLY = "assembly"
    PERSISTENCE = "persistence"
    CACHE_RETRIEVAL = "cache_retrieval"


class Retryability(StrEnum):
    RETRYABLE = "retryable"
    NOT_RETRYABLE = "not_retryable"
    UNKNOWN = "unknown"


class FailureCategory(StrEnum):
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    MALFORMED_INPUT = "malformed_input"
    UNSUPPORTED_INPUT = "unsupported_input"
    IDENTITY_CONTRADICTION = "identity_contradiction"
    VALIDATION_FAILURE = "validation_failure"
    INTERNAL_PROCESSING_FAILURE = "internal_processing_failure"
    PERSISTENCE_FAILURE = "persistence_failure"
    CORRUPT_CACHE_ENTRY = "corrupt_cache_entry"


class CountContext(StrictContractModel):
    kind: Literal["counts"] = "counts"
    values: tuple[tuple[str, int], ...]


class IdentifierContext(StrictContractModel):
    kind: Literal["identifiers"] = "identifiers"
    values: tuple[tuple[str, str], ...]


class ContractContext(StrictContractModel):
    kind: Literal["contract_versions"] = "contract_versions"
    expected: str
    actual: str


class MissingDistributionContext(StrictContractModel):
    kind: Literal["missing_distributions"] = "missing_distributions"
    distributions: tuple[str, ...]
    required_extra: str | None = None


class CacheIdentityContext(StrictContractModel):
    kind: Literal["cache_identity"] = "cache_identity"
    cache_identity: Sha256Identity
    request_identity: Sha256Identity | None = None


class SourceDigestContext(StrictContractModel):
    kind: Literal["source_digest"] = "source_digest"
    source_identity: Sha256Identity


type SafeDiagnosticContext = Annotated[
    CountContext
    | IdentifierContext
    | ContractContext
    | MissingDistributionContext
    | CacheIdentityContext
    | SourceDigestContext,
    Field(discriminator="kind"),
]


class SafeCause(StrictContractModel):
    category: FailureCategory
    exception_type: str
    message_template: str = Field(pattern=r"^[a-z0-9]+(?:_[a-z0-9]+)*$")
    nested: SafeCause | None = None


class NoCompletedEvidence(StrictContractModel):
    kind: Literal["none"] = "none"


class AcquisitionCompletedEvidence(StrictContractModel):
    kind: Literal["acquisition"] = "acquisition"
    source: SourceSummary


class InventoryCompletedEvidence(StrictContractModel):
    kind: Literal["inventory"] = "inventory"
    source: SourceSummary
    source_contract: SourceContractIdentity
    inventory: tuple[ContentInventoryItem, ...]


class PreparationCompletedEvidence(StrictContractModel):
    kind: Literal["preparation"] = "preparation"
    preparation: PreparationOutcome


class InferenceCompletedEvidence(StrictContractModel):
    kind: Literal["inference"] = "inference"
    preparation: PreparationOutcome
    inference: InferenceEvidence


class ValidationCompletedEvidence(StrictContractModel):
    kind: Literal["validation"] = "validation"
    preparation: PreparationOutcome
    analysis_draft: RstAnalysis
    validation: ValidationReceipt


class AssemblyCompletedEvidence(StrictContractModel):
    kind: Literal["assembly"] = "assembly"
    outcome: ProductionAnalysisOutcome


type CompletedStageEvidence = Annotated[
    NoCompletedEvidence
    | AcquisitionCompletedEvidence
    | InventoryCompletedEvidence
    | PreparationCompletedEvidence
    | InferenceCompletedEvidence
    | ValidationCompletedEvidence
    | AssemblyCompletedEvidence,
    Field(discriminator="kind"),
]


class SafeCompletedStageEvidence(StrictContractModel):
    kind: str
    source_identity: Sha256Identity | None = None
    semantic_identities: tuple[Sha256Identity, ...]
    item_count: int = Field(ge=0)
    anchor_count: int = Field(ge=0)
    redacted_representation_count: int = Field(ge=0)


_STAGE_ORDER = {
    LifecycleStage.ACQUISITION: 0,
    LifecycleStage.CLASSIFICATION: 1,
    LifecycleStage.PREPARATION: 2,
    LifecycleStage.PLANNING: 3,
    LifecycleStage.CACHE_RETRIEVAL: 4,
    LifecycleStage.INFERENCE: 5,
    LifecycleStage.VALIDATION: 6,
    LifecycleStage.ASSEMBLY: 7,
    LifecycleStage.PERSISTENCE: 8,
}
_EVIDENCE_STAGE = {
    "none": -1,
    "acquisition": _STAGE_ORDER[LifecycleStage.ACQUISITION],
    "inventory": _STAGE_ORDER[LifecycleStage.CLASSIFICATION],
    "preparation": _STAGE_ORDER[LifecycleStage.PREPARATION],
    "inference": _STAGE_ORDER[LifecycleStage.INFERENCE],
    "validation": _STAGE_ORDER[LifecycleStage.VALIDATION],
    "assembly": _STAGE_ORDER[LifecycleStage.ASSEMBLY],
}


class ProductionFailure(StrictContractModel):
    failed_stage: LifecycleStage
    category: FailureCategory
    code: str = Field(pattern=r"^[a-z0-9]+(?:_[a-z0-9]+)*$")
    retryability: Retryability
    message_template: str = Field(pattern=r"^[a-z0-9]+(?:_[a-z0-9]+)*$")
    message_parameters: tuple[tuple[str, str], ...] = ()
    diagnostic_context: tuple[SafeDiagnosticContext, ...] = ()
    cause: SafeCause | None = None
    completed: CompletedStageEvidence = NoCompletedEvidence()

    @model_validator(mode="after")
    def completed_evidence_precedes_failure(self) -> Self:
        if _EVIDENCE_STAGE[self.completed.kind] >= _STAGE_ORDER[self.failed_stage]:
            raise ValueError("completed evidence must come from a stage before the failed stage")
        if self.category is FailureCategory.PROVIDER_UNAVAILABLE and self.retryability is Retryability.RETRYABLE:
            raise ValueError("provider unavailability is not retryable without an external state change")
        return self


class FailureExecutionEvidence(StrictContractModel):
    execution_id: str


class SafeFailureSemanticEvidence(StrictContractModel):
    failure: ProductionFailure
    safe_completed: SafeCompletedStageEvidence


class SafeProductionFailureRecord(StrictContractModel):
    contract: Literal["isanlp_rst.production"] = PRODUCTION_CONTRACT
    contract_version: Literal["2.0.0"] = WRITE_CONTRACT_VERSION
    kind: Literal["safe_production_failure"] = "safe_production_failure"
    semantic: SafeFailureSemanticEvidence
    execution: FailureExecutionEvidence
    semantic_digest: Sha256Identity | None = None

    @model_validator(mode="after")
    def complete_identity(self) -> Self:
        return _set_failure_identity(self)


class DiagnosticPolicy(StrictContractModel):
    include_private_content: Literal[True]


class DiagnosticFailureSemanticEvidence(StrictContractModel):
    failure: ProductionFailure
    diagnostic_policy: DiagnosticPolicy


class DiagnosticProductionFailureRecord(StrictContractModel):
    contract: Literal["isanlp_rst.production"] = PRODUCTION_CONTRACT
    contract_version: Literal["2.0.0"] = WRITE_CONTRACT_VERSION
    kind: Literal["diagnostic_production_failure"] = "diagnostic_production_failure"
    semantic: DiagnosticFailureSemanticEvidence
    execution: FailureExecutionEvidence
    semantic_digest: Sha256Identity | None = None

    @model_validator(mode="after")
    def complete_identity(self) -> Self:
        return _set_failure_identity(self)


class ProductionIngestError(RuntimeError):
    """Exception wrapper whose displayed and persisted state is safe by construction."""

    def __init__(self, failure: ProductionFailure) -> None:
        self.failure = failure
        super().__init__(f"{failure.failed_stage.value}/{failure.code}: {failure.message_template}")

    def __repr__(self) -> str:
        failure = self.failure
        return (
            "ProductionIngestError("
            f"stage={failure.failed_stage.value!r}, category={failure.category.value!r}, "
            f"code={failure.code!r}, retryability={failure.retryability.value!r})"
        )

    def safe_record(self, *, execution_id: str) -> SafeProductionFailureRecord:
        """Return the default privacy-preserving persisted projection."""

        return SafeProductionFailureRecord(
            semantic=SafeFailureSemanticEvidence(
                failure=self.failure.model_copy(update={"completed": NoCompletedEvidence()}),
                safe_completed=_safe_completed_evidence(self.failure.completed),
            ),
            execution=FailureExecutionEvidence(execution_id=execution_id),
        )

    def diagnostic_record(
        self,
        *,
        policy: DiagnosticPolicy,
        execution_id: str,
    ) -> DiagnosticProductionFailureRecord:
        """Return full completed evidence only after explicit diagnostic opt-in."""

        return DiagnosticProductionFailureRecord(
            semantic=DiagnosticFailureSemanticEvidence(
                failure=self.failure,
                diagnostic_policy=policy,
            ),
            execution=FailureExecutionEvidence(execution_id=execution_id),
        )


def _safe_completed_evidence(completed: CompletedStageEvidence) -> SafeCompletedStageEvidence:
    source_identity: Sha256Identity | None = None
    identities: list[Sha256Identity] = []
    items: tuple[ContentInventoryItem, ...] = ()
    if isinstance(completed, AcquisitionCompletedEvidence):
        source_identity = Sha256Identity(hex_digest=completed.source.source_id)
    elif isinstance(completed, InventoryCompletedEvidence):
        source_identity = Sha256Identity(hex_digest=completed.source.source_id)
        identities.append(Sha256Identity(hex_digest=completed.source_contract.semantic_digest))
        items = completed.inventory
    elif isinstance(
        completed,
        PreparationCompletedEvidence | InferenceCompletedEvidence | ValidationCompletedEvidence,
    ):
        preparation = completed.preparation
        source_identity = Sha256Identity(hex_digest=preparation.semantic.source.source_id)
        identities.extend(_preparation_identities(preparation))
        items = preparation.semantic.inventory
        if isinstance(completed, InferenceCompletedEvidence):
            identities.append(Sha256Identity(hex_digest=semantic_sha256(completed.inference)))
        elif isinstance(completed, ValidationCompletedEvidence):
            identities.extend(
                (
                    Sha256Identity(hex_digest=semantic_sha256(completed.analysis_draft)),
                    _required_identity(completed.validation.semantic_digest, "validation"),
                )
            )
    elif isinstance(completed, AssemblyCompletedEvidence):
        outcome = completed.outcome
        source_identity = Sha256Identity(hex_digest=outcome.semantic.preparation.semantic.source.source_id)
        identities.append(_required_identity(outcome.semantic_digest, "analysis outcome"))
        items = outcome.semantic.preparation.semantic.inventory
    anchor_count = sum(len(item.anchors) for item in items)
    redacted = sum(isinstance(item.representation, RedactedContentRepresentation) for item in items)
    return SafeCompletedStageEvidence(
        kind=completed.kind,
        source_identity=source_identity,
        semantic_identities=tuple(identities),
        item_count=len(items),
        anchor_count=anchor_count,
        redacted_representation_count=redacted,
    )


def _preparation_identities(preparation: PreparationOutcome) -> tuple[Sha256Identity, ...]:
    return (
        _required_identity(preparation.semantic_digest, "preparation"),
        _required_identity(preparation.semantic.prepared_document.semantic_digest, "prepared document"),
        _required_identity(preparation.semantic.analysis_plan.semantic_digest, "analysis plan"),
    )


def _required_identity(
    identity: Sha256Identity | None,
    label: str,
) -> Sha256Identity:
    if identity is None:
        raise ValueError(f"{label} has no semantic identity")
    return identity


def _set_failure_identity[
    T: SafeProductionFailureRecord | DiagnosticProductionFailureRecord,
](value: T) -> T:
    expected = Sha256Identity(
        hex_digest=semantic_sha256(
            {
                "contract": value.contract,
                "contract_version": value.contract_version,
                "kind": value.kind,
                "semantic": value.semantic,
            }
        )
    )
    if value.semantic_digest is not None and value.semantic_digest != expected:
        raise ValueError("failure record semantic digest mismatch")
    object.__setattr__(value, "semantic_digest", expected)
    return value


__all__ = [
    "AcquisitionCompletedEvidence",
    "AssemblyCompletedEvidence",
    "CacheIdentityContext",
    "CompletedStageEvidence",
    "ContractContext",
    "CountContext",
    "DiagnosticPolicy",
    "DiagnosticProductionFailureRecord",
    "FailureCategory",
    "FailureExecutionEvidence",
    "IdentifierContext",
    "InferenceCompletedEvidence",
    "InventoryCompletedEvidence",
    "LifecycleStage",
    "MissingDistributionContext",
    "NoCompletedEvidence",
    "PreparationCompletedEvidence",
    "ProductionFailure",
    "ProductionIngestError",
    "Retryability",
    "SafeCause",
    "SafeCompletedStageEvidence",
    "SafeDiagnosticContext",
    "SafeFailureSemanticEvidence",
    "SafeProductionFailureRecord",
    "SourceDigestContext",
    "ValidationCompletedEvidence",
]
