"""Strict evidence contracts for the production boundary."""

from enum import StrEnum
from pathlib import PurePosixPath

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from isanlp_rst.model_loading.release import ModelFile, ModelReleaseManifest, PromotionReceipt

__all__ = ["ModelFile", "ModelReleaseManifest", "PromotionReceipt"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class OwnershipClass(StrEnum):
    PRODUCTION = "production"
    OFFLINE = "offline"
    REPOSITORY = "repository"
    GENERATED = "generated"


class ViolationKind(StrEnum):
    UNMATCHED_OWNERSHIP = "unmatched_ownership"
    AMBIGUOUS_OWNERSHIP = "ambiguous_ownership"
    FORBIDDEN_IMPORT = "forbidden_import"
    FORBIDDEN_DEPENDENCY = "forbidden_dependency"
    FORBIDDEN_ARTIFACT_MEMBER = "forbidden_artifact_member"
    MISSING_RUNTIME_MEMBER = "missing_runtime_member"


class OwnershipRule(StrictModel):
    rule_id: str = Field(min_length=1)
    prefix: PurePosixPath
    ownership: OwnershipClass
    reason: str = Field(min_length=1)
    publishable: bool = False

    @model_validator(mode="after")
    def publication_matches_ownership(self) -> "OwnershipRule":
        if self.publishable != (self.ownership == OwnershipClass.PRODUCTION):
            raise ValueError("publishable is true exactly for production ownership")
        return self


class DependencyRule(StrictModel):
    distribution: str = Field(min_length=1)
    ownership: OwnershipClass
    reason: str = Field(min_length=1)
    optional_capability: str | None = None


class BoundaryViolation(StrictModel):
    kind: ViolationKind
    root: str = Field(min_length=1)
    path: tuple[str, ...] = Field(min_length=1)
    detail: str = Field(min_length=1)


class ArtifactReceipt(StrictModel):
    artifact_path: str
    artifact_kind: str
    artifact_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    member_count: int = Field(ge=0)
    production_members: tuple[str, ...]
    forbidden_members: tuple[str, ...]
    declared_dependencies: tuple[str, ...]

    @field_validator("artifact_kind")
    @classmethod
    def supported_kind(cls, value: str) -> str:
        if value not in {"wheel", "sdist"}:
            raise ValueError("artifact_kind must be wheel or sdist")
        return value

    @property
    def valid(self) -> bool:
        return not self.forbidden_members


class BoundaryReport(StrictModel):
    scanned_files: int = Field(ge=0)
    production_modules: int = Field(ge=0)
    elapsed_ms: float = Field(ge=0)
    artifact_receipts: tuple[ArtifactReceipt, ...] = ()
    violations: tuple[BoundaryViolation, ...] = ()

    @property
    def valid(self) -> bool:
        return not self.violations and all(receipt.valid for receipt in self.artifact_receipts)


class ParityCase(StrictModel):
    case_id: str
    model_identity: str
    route: str
    input_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    result_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    device: str
    tolerance: float = Field(default=0.0, ge=0.0)
