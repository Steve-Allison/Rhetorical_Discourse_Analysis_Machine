"""Strict canonical evidence and release contracts for the production boundary."""

from datetime import datetime
from enum import StrEnum
import hashlib
from pathlib import Path
from pathlib import PurePosixPath
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
import rfc8785

from rdam.rst.model_loading.release import ModelFile, ModelReleaseManifest
from workbench.promotion.contracts import PromotionReceipt


_SHA256_PATTERN = r"^[0-9a-f]{64}$"
_GIT_IDENTITY_PATTERN = r"^[0-9a-f]{40,64}$"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class OwnershipClass(StrEnum):
    PRODUCTION = "production"
    MODEL = "model"
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


class EvidenceState(StrEnum):
    PRE_SOURCE = "pre_source"
    SOURCE_SELECTED = "source_selected"
    ARTIFACT_VERIFIED = "artifact_verified"
    CANDIDATE_VERIFIED = "candidate_verified"
    RELEASE_CERTIFIED = "release_certified"


class CheckStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"


class GateResult(StrictModel):
    check_id: str = Field(pattern=r"^[a-z0-9]+(?:[._-][a-z0-9]+)*$")
    status: CheckStatus
    command: tuple[str, ...] = Field(min_length=1)
    tool_identity: str = Field(min_length=1)
    output_sha256: str = Field(pattern=_SHA256_PATTERN)
    completed_at: datetime
    summary: str = Field(min_length=1)


class PreparationPerformanceCase(StrictModel):
    """One source-size measurement with its warm-up and all retained runs."""

    character_count: int = Field(gt=0)
    threshold_seconds: float = Field(gt=0)
    warmup_seconds: float = Field(ge=0)
    run_seconds: tuple[float, float, float, float, float]

    @field_validator("run_seconds")
    @classmethod
    def non_negative_runs(
        cls,
        value: tuple[float, float, float, float, float],
    ) -> tuple[float, float, float, float, float]:
        if any(run < 0 for run in value):
            raise ValueError("performance runs must be non-negative")
        return value

    @property
    def passed(self) -> bool:
        return all(run < self.threshold_seconds for run in self.run_seconds)


class PreparationPerformanceEvidence(StrictModel):
    """The complete one-warm-up/five-run preparation performance record."""

    warmup_runs: Literal[1] = 1
    measured_runs: Literal[5] = 5
    cases: tuple[PreparationPerformanceCase, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def case_sizes_are_unique(self) -> Self:
        if len({case.character_count for case in self.cases}) != len(self.cases):
            raise ValueError("performance character counts must be unique")
        return self

    @property
    def passed(self) -> bool:
        return all(case.passed for case in self.cases)


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
    preparation_performance: PreparationPerformanceEvidence | None = None

    @model_validator(mode="after")
    def identities_follow_lifecycle(self) -> Self:
        if self.state is EvidenceState.PRE_SOURCE and any(
            (self.source_commit, self.candidate_commit, self.certification_commit)
        ):
            raise ValueError("pre-source evidence cannot name a future commit")
        if self.state is not EvidenceState.PRE_SOURCE and self.source_commit is None:
            raise ValueError("post-source evidence requires the existing source commit")
        if (
            self.state in {EvidenceState.CANDIDATE_VERIFIED, EvidenceState.RELEASE_CERTIFIED}
            and self.candidate_commit is None
        ):
            raise ValueError("candidate verification requires the existing candidate commit")
        if self.state is EvidenceState.RELEASE_CERTIFIED and self.certification_commit is None:
            raise ValueError("release certification requires the existing certification commit")
        if len({check.check_id for check in self.checks}) != len(self.checks):
            raise ValueError("evidence check identifiers must be unique")
        is_performance = self.schema_name == "isanlp_rst.release_evidence.performance"
        if is_performance != (self.preparation_performance is not None):
            raise ValueError("only performance evidence carries complete preparation measurements")
        return self


class SourceReleaseIdentity(StrictModel):
    vcs: Literal["git"] = "git"
    commit: str = Field(pattern=_GIT_IDENTITY_PATTERN)
    tree: str = Field(pattern=_GIT_IDENTITY_PATTERN)
    state: Literal["clean"] = "clean"
    archive_sha256: str = Field(pattern=_SHA256_PATTERN)
    source_date_epoch: int = Field(gt=0)


class SourceReleaseRecord(StrictModel):
    """Canonical evidence selecting one immutable clean source revision."""

    schema_name: Literal["isanlp_rst.release_evidence.source_release"] = "isanlp_rst.release_evidence.source_release"
    schema_version: Literal["1.0.0"] = "1.0.0"
    state: Literal[EvidenceState.SOURCE_SELECTED] = EvidenceState.SOURCE_SELECTED
    source: SourceReleaseIdentity


class BuiltArtifactIdentity(StrictModel):
    filename: str = Field(min_length=1)
    sha256: str = Field(pattern=_SHA256_PATTERN)
    size_bytes: int = Field(gt=0)


class ReproducibleBuildReport(StrictModel):
    """Canonical evidence for one reproducible double build of the release pair."""

    schema_name: Literal["isanlp_rst.release_evidence.reproducible_build"] = (
        "isanlp_rst.release_evidence.reproducible_build"
    )
    schema_version: Literal["1.0.0"] = "1.0.0"
    source_commit: str = Field(pattern=_GIT_IDENTITY_PATTERN)
    source_tree: str = Field(pattern=_GIT_IDENTITY_PATTERN)
    source_tag: str | None
    source_archive_sha256: str = Field(pattern=_SHA256_PATTERN)
    source_date_epoch: int = Field(gt=0)
    build_frontend: str = Field(min_length=1)
    build_backend: str = Field(min_length=1)
    build_reports: tuple[str, str]
    provenance_sha256: str = Field(pattern=_SHA256_PATTERN)
    artifacts: tuple[BuiltArtifactIdentity, BuiltArtifactIdentity]
    reproducible: Literal[True] = True

    @field_validator("build_reports")
    @classmethod
    def build_reports_are_digests(cls, value: tuple[str, str]) -> tuple[str, str]:
        if any(len(item) != 64 or set(item) - set("0123456789abcdef") for item in value):
            raise ValueError("build report identities must be SHA-256 hex digests")
        return value


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
    "BuiltArtifactIdentity",
    "CheckStatus",
    "DependencyRule",
    "EvidenceRecord",
    "EvidenceState",
    "GateResult",
    "ModelFile",
    "ModelReleaseManifest",
    "OwnershipClass",
    "OwnershipRule",
    "PreparationPerformanceCase",
    "PreparationPerformanceEvidence",
    "PromotionReceipt",
    "ReproducibleBuildReport",
    "SourceReleaseIdentity",
    "SourceReleaseRecord",
    "ViolationKind",
    "canonical_record_bytes",
    "sha256_path",
    "write_canonical_record",
]
