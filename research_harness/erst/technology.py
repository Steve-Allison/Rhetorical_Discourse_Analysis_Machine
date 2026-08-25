"""Frozen practical technology matrix for the isolated eRST comparison."""

from enum import StrEnum
import hashlib
from importlib.metadata import version
import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from isanlp_rst._version import PACKAGE_VERSION
from isanlp_rst.contracts.erst import TokenizerCompatibilityReceipt
from research_harness.erst.contracts import MandatoryExperimentSystem

TECHNOLOGY_MATRIX_SCHEMA_VERSION = "1.0"
_GIT_REVISION_PATTERN = r"^[0-9a-f]{40}$"
_SHA256_PATTERN = r"^[0-9a-f]{64}$"


def _canonical_model_hash(model: BaseModel, *, hash_field: str) -> str:
    payload = model.model_dump(mode="json", exclude={hash_field})
    encoded = json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode()
    return hashlib.sha256(encoded).hexdigest()


def system_config_sha256(system: "TechnologySystem") -> str:
    """Return the immutable architecture/config identity used by runner adapters."""

    encoded = json.dumps(
        system.model_dump(mode="json"),
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


class SystemRole(StrEnum):
    """Declared purpose of one required system in the comparison."""

    REPOSITORY_REFERENCE = "repository_reference"
    CONTROL = "control"
    CANDIDATE = "candidate"
    FUSION_CANDIDATE = "fusion_candidate"


class TechnologyConstraint(StrEnum):
    """Known implementation constraint that must be resolved or measured by a run."""

    TOKENIZER_CONVERSION_REQUIRED = "tokenizer_conversion_required"
    MEMORY_MEASUREMENT_REQUIRED = "memory_measurement_required"
    TEXT_CHAMPION_REQUIRED = "text_champion_required"


class TechnologySystem(BaseModel):
    """One immutable, non-substitutable comparison implementation identity."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    system: MandatoryExperimentSystem
    role: SystemRole
    implementation_module: str = Field(pattern=r"^research_harness\.erst\.systems\.[a-z0-9_]+$")
    model_id: str | None = None
    model_revision: str | None = Field(default=None, pattern=_GIT_REVISION_PATTERN)
    model_license: str = Field(min_length=1)
    tokenizer_probe_succeeded: bool | None = None
    tokenizer_encoding_sha256: str | None = Field(default=None, pattern=_SHA256_PATTERN)
    mps_tokenizer_probe_succeeded: bool | None = None
    weight_file_bytes: int | None = Field(default=None, gt=0)
    constraints: tuple[TechnologyConstraint, ...] = ()
    product_role: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_identity(self) -> "TechnologySystem":
        has_model = self.model_id is not None
        model_evidence = (
            self.model_revision,
            self.tokenizer_probe_succeeded,
            self.mps_tokenizer_probe_succeeded,
        )
        if has_model != all(item is not None for item in model_evidence):
            raise ValueError("model-backed systems require revision and tokenizer/MPS probe evidence")
        if not has_model and any(item is not None for item in (*model_evidence, self.tokenizer_encoding_sha256)):
            raise ValueError("model-free systems cannot carry tokenizer or model revision evidence")
        if self.tokenizer_probe_succeeded is True and self.tokenizer_encoding_sha256 is None:
            raise ValueError("successful tokenizer probes require an encoding SHA-256")
        if self.tokenizer_probe_succeeded is False and TechnologyConstraint.TOKENIZER_CONVERSION_REQUIRED not in self.constraints:
            raise ValueError("failed tokenizer probe requires an explicit conversion constraint")
        return self


class HubModelEvidence(BaseModel):
    """Live Hub evidence resolved at the matrix's immutable revision."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    model_id: str = Field(min_length=1)
    revision: str = Field(pattern=_GIT_REVISION_PATTERN)
    model_license: str = Field(min_length=1)
    weight_file_bytes: int = Field(gt=0)


class TechnologyMatrix(BaseModel):
    """Complete practical implementation matrix frozen before system execution."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = TECHNOLOGY_MATRIX_SCHEMA_VERSION
    package_version: str = PACKAGE_VERSION
    python_version: str = Field(min_length=1)
    torch_version: str = Field(min_length=1)
    transformers_version: str = Field(min_length=1)
    tokenizer_receipt_sha256: str = Field(pattern=_SHA256_PATTERN)
    peak_rss_limit_bytes: int = 24 * 1024**3
    systems: tuple[TechnologySystem, ...]
    matrix_sha256: str = ""

    @model_validator(mode="after")
    def validate_matrix(self) -> "TechnologyMatrix":
        if tuple(system.system for system in self.systems) != tuple(MandatoryExperimentSystem):
            raise ValueError("technology matrix must retain every mandatory system exactly once in order")
        expected_hash = _canonical_model_hash(self, hash_field="matrix_sha256")
        if self.matrix_sha256 and self.matrix_sha256 != expected_hash:
            raise ValueError("technology matrix SHA-256 does not match canonical content")
        object.__setattr__(self, "matrix_sha256", expected_hash)
        return self


def _model_system(
    *,
    receipt: TokenizerCompatibilityReceipt,
    system: MandatoryExperimentSystem,
    role: SystemRole,
    module: str,
    model_id: str,
    model_license: str,
    constraints: tuple[TechnologyConstraint, ...] = (),
    product_role: str,
) -> TechnologySystem:
    probe = next((item for item in receipt.probes if item.model_id == model_id), None)
    if probe is None:
        raise ValueError(f"tokenizer receipt is missing required model: {model_id}")
    return TechnologySystem(
        system=system,
        role=role,
        implementation_module=module,
        model_id=model_id,
        model_revision=probe.revision,
        model_license=model_license,
        tokenizer_probe_succeeded=probe.succeeded,
        tokenizer_encoding_sha256=probe.encoding_sha256,
        mps_tokenizer_probe_succeeded=probe.mps_tensor_roundtrip,
        constraints=constraints,
        product_role=product_role,
    )


def build_technology_matrix(tokenizer_receipt_path: Path) -> TechnologyMatrix:
    """Build the exact ten-system matrix from the verified tokenizer receipt."""

    receipt = TokenizerCompatibilityReceipt.model_validate_json(
        tokenizer_receipt_path.read_text(encoding="utf-8")
    )
    systems = (
        _model_system(
            receipt=receipt,
            system=MandatoryExperimentSystem.EXISTING_DUAL_ENCODER,
            role=SystemRole.REPOSITORY_REFERENCE,
            module="research_harness.erst.systems.dual_encoder",
            model_id="microsoft/deberta-v3-base",
            model_license="MIT",
            constraints=(TechnologyConstraint.TOKENIZER_CONVERSION_REQUIRED,),
            product_role="Current repository neural scorer reference",
        ),
        TechnologySystem(
            system=MandatoryExperimentSystem.STRUCTURAL_ONLY,
            role=SystemRole.CONTROL,
            implementation_module="research_harness.erst.systems.structural",
            model_license="MIT",
            product_role="Calibrated structural-feature control",
        ),
        _model_system(
            receipt=receipt,
            system=MandatoryExperimentSystem.TEXT_ONLY,
            role=SystemRole.CONTROL,
            module="research_harness.erst.systems.cross_encoder",
            model_id="google/electra-base-discriminator",
            model_license="Apache-2.0",
            product_role="Text-only cross-encoder control",
        ),
        _model_system(
            receipt=receipt,
            system=MandatoryExperimentSystem.ELECTRA,
            role=SystemRole.REPOSITORY_REFERENCE,
            module="research_harness.erst.systems.cross_encoder",
            model_id="google/electra-base-discriminator",
            model_license="Apache-2.0",
            product_role="Signal-aware cross-encoder reference",
        ),
        TechnologySystem(
            system=MandatoryExperimentSystem.SIGNAL_RULE,
            role=SystemRole.CONTROL,
            implementation_module="research_harness.erst.systems.signal_rule",
            model_license="MIT",
            product_role="Deterministic signal-plus-rule control",
        ),
        _model_system(
            receipt=receipt,
            system=MandatoryExperimentSystem.MODERNBERT_BASE,
            role=SystemRole.CANDIDATE,
            module="research_harness.erst.systems.cross_encoder",
            model_id="answerdotai/ModernBERT-base",
            model_license="Apache-2.0",
            product_role="Compact signal-aware production candidate",
        ),
        _model_system(
            receipt=receipt,
            system=MandatoryExperimentSystem.MODERNBERT_LARGE,
            role=SystemRole.CANDIDATE,
            module="research_harness.erst.systems.cross_encoder",
            model_id="answerdotai/ModernBERT-large",
            model_license="Apache-2.0",
            constraints=(TechnologyConstraint.MEMORY_MEASUREMENT_REQUIRED,),
            product_role="High-capacity signal-aware candidate",
        ),
        _model_system(
            receipt=receipt,
            system=MandatoryExperimentSystem.XLM_R_HIDAC,
            role=SystemRole.CANDIDATE,
            module="research_harness.erst.systems.hierarchical_adapter",
            model_id="FacebookAI/xlm-roberta-large",
            model_license="MIT",
            constraints=(TechnologyConstraint.MEMORY_MEASUREMENT_REQUIRED,),
            product_role="Hierarchical contrastive adapter candidate",
        ),
        _model_system(
            receipt=receipt,
            system=MandatoryExperimentSystem.QWEN3_DEDISCO,
            role=SystemRole.CANDIDATE,
            module="research_harness.erst.systems.generative_decoder",
            model_id="Qwen/Qwen3-4B",
            model_license="Apache-2.0",
            constraints=(TechnologyConstraint.MEMORY_MEASUREMENT_REQUIRED,),
            product_role="PEFT generative edge/no-edge candidate",
        ),
        TechnologySystem(
            system=MandatoryExperimentSystem.EDGE_FEATURED_GAT,
            role=SystemRole.FUSION_CANDIDATE,
            implementation_module="research_harness.erst.systems.graph_attention",
            model_license="inherits selected text model",
            constraints=(TechnologyConstraint.TEXT_CHAMPION_REQUIRED,),
            product_role="Primary-tree graph fusion candidate",
        ),
    )
    return TechnologyMatrix(
        python_version=receipt.python_version,
        torch_version=version("torch"),
        transformers_version=receipt.transformers_version,
        tokenizer_receipt_sha256=receipt.receipt_sha256,
        systems=systems,
    )


def enrich_technology_matrix(
    matrix: TechnologyMatrix,
    hub_evidence: tuple[HubModelEvidence, ...],
) -> TechnologyMatrix:
    """Bind model-backed rows to live immutable-revision licence and file-size evidence."""

    by_model = {item.model_id: item for item in hub_evidence}
    if len(by_model) != len(hub_evidence):
        raise ValueError("Hub model evidence contains duplicate model IDs")
    enriched: list[TechnologySystem] = []
    required_models = {system.model_id for system in matrix.systems if system.model_id is not None}
    if set(by_model) != required_models:
        raise ValueError("Hub model evidence must cover every model-backed matrix row exactly once")
    for system in matrix.systems:
        if system.model_id is None:
            enriched.append(system)
            continue
        evidence = by_model[system.model_id]
        if evidence.revision != system.model_revision:
            raise ValueError(f"Hub revision changed for {system.model_id}")
        if evidence.model_license.casefold() != system.model_license.casefold():
            raise ValueError(f"Hub licence does not match the frozen matrix for {system.model_id}")
        enriched.append(system.model_copy(update={"weight_file_bytes": evidence.weight_file_bytes}))
    return TechnologyMatrix.model_validate(
        {**matrix.model_dump(), "systems": tuple(enriched), "matrix_sha256": ""}
    )


__all__ = [
    "TECHNOLOGY_MATRIX_SCHEMA_VERSION",
    "SystemRole",
    "HubModelEvidence",
    "TechnologyConstraint",
    "TechnologyMatrix",
    "TechnologySystem",
    "build_technology_matrix",
    "enrich_technology_matrix",
    "system_config_sha256",
]
