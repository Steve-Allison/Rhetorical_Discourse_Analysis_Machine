"""Strict canonical evidence and release contracts for the production boundary."""

from datetime import datetime
from enum import StrEnum
import hashlib
from pathlib import Path
from pathlib import PurePosixPath
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
import rfc8785

from isanlp_rst.model_loading.release import ModelFile, ModelReleaseManifest, PromotionReceipt


_SHA256_PATTERN = r"^[0-9a-f]{64}$"
_GIT_IDENTITY_PATTERN = r"^[0-9a-f]{40,64}$"


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


class EvidenceState(StrEnum):
    PRE_SOURCE = "pre_source"
    SOURCE_SELECTED = "source_selected"
    ARTIFACT_VERIFIED = "artifact_verified"
    CANDIDATE_VERIFIED = "candidate_verified"
    RELEASE_CERTIFIED = "release_certified"


class CheckStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"


class VerificationCheck(StrictModel):
    check_id: str = Field(pattern=r"^[a-z0-9]+(?:[._-][a-z0-9]+)*$")
    status: CheckStatus
    command: tuple[str, ...] = Field(min_length=1)
    tool_identity: str = Field(min_length=1)
    evidence_path: str = Field(min_length=1)
    evidence_sha256: str = Field(pattern=_SHA256_PATTERN)
    completed_at: datetime


class GateResult(StrictModel):
    check_id: str = Field(pattern=r"^[a-z0-9]+(?:[._-][a-z0-9]+)*$")
    status: CheckStatus
    command: tuple[str, ...] = Field(min_length=1)
    tool_identity: str = Field(min_length=1)
    output_sha256: str = Field(pattern=_SHA256_PATTERN)
    completed_at: datetime
    summary: str = Field(min_length=1)


class EvidenceRecord(StrictModel):
    """Canonical lifecycle record used by every Feature 004 JSON evidence file."""

    schema_name: str = Field(pattern=r"^isanlp_rst\.release_evidence\.[a-z0-9_]+$")
    schema_version: Literal["1.0.0"] = "1.0.0"
    state: EvidenceState
    created_at: datetime
    source_commit: str | None = Field(default=None, pattern=_GIT_IDENTITY_PATTERN)
    candidate_commit: str | None = Field(default=None, pattern=_GIT_IDENTITY_PATTERN)
    certification_commit: str | None = Field(default=None, pattern=_GIT_IDENTITY_PATTERN)
    checks: tuple[GateResult, ...]

    @model_validator(mode="after")
    def identities_follow_lifecycle(self) -> Self:
        if self.state is EvidenceState.PRE_SOURCE and any(
            (self.source_commit, self.candidate_commit, self.certification_commit)
        ):
            raise ValueError("pre-source evidence cannot name a future commit")
        if self.state is not EvidenceState.PRE_SOURCE and self.source_commit is None:
            raise ValueError("post-source evidence requires the existing source commit")
        if self.state in {EvidenceState.CANDIDATE_VERIFIED, EvidenceState.RELEASE_CERTIFIED} and self.candidate_commit is None:
            raise ValueError("candidate verification requires the existing candidate commit")
        if self.state is EvidenceState.RELEASE_CERTIFIED and self.certification_commit is None:
            raise ValueError("release certification requires the existing certification commit")
        if len({check.check_id for check in self.checks}) != len(self.checks):
            raise ValueError("evidence check identifiers must be unique")
        return self


class ReleaseContractIdentity(StrictModel):
    package_name: Literal["isanlp_rst"] = "isanlp_rst"
    package_version: Literal["5.0.0"] = "5.0.0"
    production_contract: Literal["isanlp_rst.production"] = "isanlp_rst.production"
    write_contract_version: Literal["2.0.0"] = "2.0.0"
    readable_contract_versions: tuple[Literal["2.0.0"], ...] = ("2.0.0",)


class SourceReleaseIdentity(StrictModel):
    vcs: Literal["git"] = "git"
    commit: str = Field(pattern=_GIT_IDENTITY_PATTERN)
    tree: str = Field(pattern=_GIT_IDENTITY_PATTERN)
    state: Literal["clean"] = "clean"
    archive_sha256: str = Field(pattern=_SHA256_PATTERN)
    source_date_epoch: int = Field(gt=0)


class SourceReleaseRecord(StrictModel):
    """Canonical evidence selecting one immutable clean source revision."""

    schema_name: Literal["isanlp_rst.release_evidence.source_release"] = (
        "isanlp_rst.release_evidence.source_release"
    )
    schema_version: Literal["1.0.0"] = "1.0.0"
    state: Literal[EvidenceState.SOURCE_SELECTED] = EvidenceState.SOURCE_SELECTED
    source: SourceReleaseIdentity


class BuildIdentity(StrictModel):
    python_implementation: str = Field(min_length=1)
    python_version: str = Field(min_length=1)
    build_frontend: Literal["build"] = "build"
    build_frontend_version: str = Field(min_length=1)
    build_backend: Literal["hatchling.build"] = "hatchling.build"
    build_backend_version: str = Field(min_length=1)
    platform: str = Field(min_length=1)
    lock_sha256: str = Field(pattern=_SHA256_PATTERN)
    deterministic_environment: tuple[tuple[str, str], ...]
    provenance_sha256: str = Field(pattern=_SHA256_PATTERN)


class ReleaseArtifactIdentity(StrictModel):
    filename: str = Field(min_length=1)
    kind: Literal["wheel", "sdist"]
    size_bytes: int = Field(gt=0)
    sha256: str = Field(pattern=_SHA256_PATTERN)
    wheel_tags: tuple[str, ...] = ()
    build_report_sha256: str = Field(pattern=_SHA256_PATTERN)
    package_name: Literal["isanlp_rst"] = "isanlp_rst"
    package_version: Literal["5.0.0"] = "5.0.0"


class ReleaseReceipt(StrictModel):
    schema_name: Literal["isanlp_rst.release_receipt"] = "isanlp_rst.release_receipt"
    schema_version: Literal["1.0.0"] = "1.0.0"
    contract: ReleaseContractIdentity
    source: SourceReleaseIdentity
    build: BuildIdentity
    artifacts: tuple[ReleaseArtifactIdentity, ReleaseArtifactIdentity]
    verification: tuple[VerificationCheck, ...]

    @model_validator(mode="after")
    def complete_release(self) -> Self:
        if {artifact.kind for artifact in self.artifacts} != {"wheel", "sdist"}:
            raise ValueError("release receipt requires exactly one wheel and one sdist")
        if len({artifact.filename for artifact in self.artifacts}) != 2:
            raise ValueError("release artifact filenames must be unique")
        if not self.verification or any(
            check.status is not CheckStatus.PASSED for check in self.verification
        ):
            raise ValueError("every required release verification must be present and passed")
        return self


def canonical_record_bytes(value: BaseModel) -> bytes:
    """Return RFC 8785 bytes for one strict release/evidence record."""

    return rfc8785.dumps(value.model_dump(mode="json", exclude_none=False))


def sha256_path(path: Path) -> str:
    """Hash one file without reading it all into memory."""

    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_canonical_record(path: Path, value: BaseModel) -> str:
    """Atomically write one canonical record and return its SHA-256 identity."""

    payload = canonical_record_bytes(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_bytes(payload)
    temporary.replace(path)
    return hashlib.sha256(payload).hexdigest()


__all__ = [
    "ArtifactReceipt",
    "BoundaryReport",
    "BoundaryViolation",
    "BuildIdentity",
    "CheckStatus",
    "DependencyRule",
    "EvidenceRecord",
    "EvidenceState",
    "GateResult",
    "ModelFile",
    "ModelReleaseManifest",
    "OwnershipClass",
    "OwnershipRule",
    "ParityCase",
    "PromotionReceipt",
    "ReleaseArtifactIdentity",
    "ReleaseContractIdentity",
    "ReleaseReceipt",
    "SourceReleaseIdentity",
    "SourceReleaseRecord",
    "VerificationCheck",
    "ViolationKind",
    "canonical_record_bytes",
    "sha256_path",
    "write_canonical_record",
]
