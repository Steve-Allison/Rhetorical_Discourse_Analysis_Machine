"""Model-free production capability discovery contracts."""

from enum import StrEnum
from importlib.metadata import PackageNotFoundError, version
from typing import Literal, Self

from pydantic import Field, model_validator

from isanlp_rst.ingest.contracts.base import (
    PRODUCTION_CONTRACT,
    READABLE_CONTRACT_VERSIONS,
    WRITE_CONTRACT_VERSION,
    SemanticVersion,
    Sha256Identity,
    StrictContractModel,
)
from isanlp_rst.ingest.contracts.inference import EvidenceDetailPolicy, OutputFormalism
from isanlp_rst.ingest.contracts.source import SourceForm
from isanlp_rst.ingest.identity import semantic_sha256


class Availability(StrEnum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"


class ModelIdentityState(StrEnum):
    IMMUTABLE_RELEASE = "immutable_release"
    MUTABLE_INSTANCE = "mutable_instance"
    UNIDENTIFIED = "unidentified"
    NOT_CONFIGURED = "not_configured"


class CacheEligibilityState(StrEnum):
    ELIGIBLE = "eligible"
    INELIGIBLE = "ineligible"


class SourceFormCapability(StrictContractModel):
    source_form: SourceForm
    availability: Availability
    required_extra: str | None
    missing_distributions: tuple[str, ...]
    accepted_media_types: tuple[str, ...]
    preparation_supported: bool


class FormalismCapability(StrictContractModel):
    formalism: OutputFormalism
    availability: Availability
    reason: str


class EvidenceCapability(StrictContractModel):
    detail: EvidenceDetailPolicy
    availability: Availability
    reason: str


class OperationCapability(StrictContractModel):
    operation: str
    success_kinds: tuple[str, ...]
    failure_kind: str


class CacheEligibility(StrictContractModel):
    state: CacheEligibilityState
    reason: str


class ProductionCapabilitiesSemantic(StrictContractModel):
    package_version: str
    write_contract_version: SemanticVersion
    readable_contract_versions: tuple[SemanticVersion, ...]
    source_forms: tuple[SourceFormCapability, ...]
    operations: tuple[OperationCapability, ...]
    parser_identity_state: ModelIdentityState
    active_parser_family: str | None
    canonical_parser_result_supported: bool
    exact_runtime_identity_supported: bool
    formalism_capabilities: tuple[FormalismCapability, ...]
    evidence_capabilities: tuple[EvidenceCapability, ...]
    output_formalisms: tuple[OutputFormalism, ...]
    evidence_detail_levels: tuple[EvidenceDetailPolicy, ...]
    model_free_discovery: Literal[True]
    canonical_serialization: Literal[True]
    persistence_supported: Literal[True]
    cache_eligibility: CacheEligibility


class CapabilityExecution(StrictContractModel):
    execution_id: str = Field(min_length=1)


class ProductionCapabilities(StrictContractModel):
    contract: Literal["isanlp_rst.production"] = PRODUCTION_CONTRACT
    contract_version: Literal["2.0.0"] = WRITE_CONTRACT_VERSION
    kind: Literal["capabilities"] = "capabilities"
    semantic: ProductionCapabilitiesSemantic
    execution: CapabilityExecution
    semantic_digest: Sha256Identity | None = None

    @model_validator(mode="after")
    def complete_semantic_identity(self) -> Self:
        expected = Sha256Identity(
            hex_digest=semantic_sha256(
                {
                    "contract": self.contract,
                    "contract_version": self.contract_version,
                    "kind": self.kind,
                    "semantic": self.semantic,
                }
            )
        )
        if self.semantic_digest is not None and self.semantic_digest != expected:
            raise ValueError("capability semantic digest does not match semantic projection")
        object.__setattr__(self, "semantic_digest", expected)
        return self

    @classmethod
    def discover(cls, *, execution_id: str = "capability-discovery") -> "ProductionCapabilities":
        """Describe the installed boundary without importing optional adapters or models."""

        try:
            package_version = version("isanlp_rst")
        except PackageNotFoundError:
            package_version = "unknown"
        source_forms = tuple(_source_capability(source_form) for source_form in SourceForm)
        semantic = ProductionCapabilitiesSemantic(
            package_version=package_version,
            write_contract_version=SemanticVersion(root=WRITE_CONTRACT_VERSION),
            readable_contract_versions=tuple(
                SemanticVersion(root=item) for item in READABLE_CONTRACT_VERSIONS
            ),
            source_forms=source_forms,
            operations=(
                OperationCapability(
                    operation="prepare",
                    success_kinds=("preparation_outcome",),
                    failure_kind="safe_production_failure",
                ),
                OperationCapability(
                    operation="analyse",
                    success_kinds=("analysed_outcome", "empty_primary_analysis_outcome"),
                    failure_kind="safe_production_failure",
                ),
            ),
            parser_identity_state=ModelIdentityState.NOT_CONFIGURED,
            active_parser_family=None,
            canonical_parser_result_supported=False,
            exact_runtime_identity_supported=False,
            formalism_capabilities=tuple(
                FormalismCapability(
                    formalism=formalism,
                    availability=Availability.UNAVAILABLE,
                    reason="parser_not_configured",
                )
                for formalism in OutputFormalism
            ),
            evidence_capabilities=tuple(
                EvidenceCapability(
                    detail=detail,
                    availability=Availability.UNAVAILABLE,
                    reason="parser_not_configured",
                )
                for detail in EvidenceDetailPolicy
            ),
            output_formalisms=(),
            evidence_detail_levels=(),
            model_free_discovery=True,
            canonical_serialization=True,
            persistence_supported=True,
            cache_eligibility=CacheEligibility(
                state=CacheEligibilityState.INELIGIBLE,
                reason="parser_not_configured",
            ),
        )
        return cls(semantic=semantic, execution=CapabilityExecution(execution_id=execution_id))


def _source_capability(source_form: SourceForm) -> SourceFormCapability:
    requirements = {
        SourceForm.MARKDOWN: ("markdown-it-py", "mdit-py-plugins"),
        SourceForm.DOCLING_JSON: ("docling-core",),
        SourceForm.DOCLANG_XML: ("doclang",),
        SourceForm.DOCLANG_ARCHIVE: ("doclang",),
    }
    required = requirements.get(source_form, ())
    missing = tuple(
        distribution
        for distribution in required
        if not _distribution_installed(distribution)
    )
    media_types = {
        SourceForm.TEXT: ("text/plain; charset=utf-8",),
        SourceForm.EDUS: ("application/vnd.isanlp-rst.edus+json",),
        SourceForm.MARKDOWN: ("text/markdown; charset=utf-8",),
        SourceForm.DOCLING_JSON: ("application/vnd.docling.document+json",),
        SourceForm.DOCLANG_XML: ("application/vnd.doclang+xml",),
        SourceForm.DOCLANG_ARCHIVE: ("application/vnd.doclang.archive+zip",),
    }[source_form]
    return SourceFormCapability(
        source_form=source_form,
        availability=Availability.UNAVAILABLE if missing else Availability.AVAILABLE,
        required_extra="formats" if required else None,
        missing_distributions=missing,
        accepted_media_types=media_types,
        preparation_supported=not missing,
    )


def _distribution_installed(distribution: str) -> bool:
    try:
        version(distribution)
    except PackageNotFoundError:
        return False
    return True


__all__ = [
    "Availability",
    "CacheEligibility",
    "CacheEligibilityState",
    "CapabilityExecution",
    "EvidenceCapability",
    "FormalismCapability",
    "ModelIdentityState",
    "OperationCapability",
    "ProductionCapabilities",
    "ProductionCapabilitiesSemantic",
    "SourceFormCapability",
]
