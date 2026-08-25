"""Strict contracts and validation for immutable production model releases."""

from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
from pathlib import Path, PurePosixPath
import re

from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.version import InvalidVersion, Version
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from isanlp_rst._version import resolve_installed_package_version

MODEL_RELEASE_MANIFEST = "release-manifest.json"
_MAX_MANIFEST_BYTES = 4 * 1024 * 1024
_RELEASE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class ModelReleaseError(RuntimeError):
    """A model release is incomplete, unsafe, corrupt, or incompatible."""


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ModelFile(_StrictModel):
    """One immutable file in a released model."""

    path: PurePosixPath
    role: str = Field(min_length=1)
    size_bytes: int = Field(gt=0)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @field_validator("path")
    @classmethod
    def relative_safe_path(cls, value: PurePosixPath) -> PurePosixPath:
        if value.is_absolute() or not value.parts or ".." in value.parts:
            raise ValueError("model file paths must be safe and relative")
        if value.name == MODEL_RELEASE_MANIFEST:
            raise ValueError("the release manifest cannot inventory itself")
        return value


class ModelReleaseManifest(_StrictModel):
    """Complete identity, compatibility, provenance, and byte inventory."""

    schema_version: str = "isanlp_rst_model_release/v1"
    release_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
    model_task: str = Field(min_length=1)
    architecture: str = Field(min_length=1)
    runtime_contract: str = Field(min_length=1)
    compatibility_range: str = Field(min_length=1)
    source_model_identity: str = Field(min_length=1)
    source_revision: str = Field(min_length=1)
    licence: str = Field(min_length=1)
    use_restrictions: tuple[str, ...]
    evaluation_evidence: str | None = None
    evaluation_unavailable_reason: str | None = None
    created_at: datetime
    producer_version: str = Field(min_length=1)
    files: tuple[ModelFile, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def complete_coherent_manifest(self) -> "ModelReleaseManifest":
        paths = [item.path for item in self.files]
        if len(paths) != len(set(paths)):
            raise ValueError("model release file paths must be unique")
        if bool(self.evaluation_evidence) == bool(self.evaluation_unavailable_reason):
            raise ValueError(
                "provide evaluation_evidence or evaluation_unavailable_reason, exactly one"
            )
        try:
            SpecifierSet(self.compatibility_range)
        except InvalidSpecifier as exc:
            raise ValueError("compatibility_range must be a valid Python version specifier") from exc
        return self

    @property
    def manifest_sha256(self) -> str:
        return hashlib.sha256(canonical_json_bytes(self)).hexdigest()


class PromotionReceipt(_StrictModel):
    """Immutable evidence for one successful local promotion."""

    candidate_path: str
    candidate_manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    release_path: str
    release_manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    verified_files: int = Field(gt=0)
    promoted_at: datetime
    producer_version: str = Field(min_length=1)
    succeeded: bool
    failure_code: str | None = None
    failure_detail: str | None = None

    @model_validator(mode="after")
    def success_fields_are_coherent(self) -> "PromotionReceipt":
        if self.succeeded and (self.failure_code is not None or self.failure_detail is not None):
            raise ValueError("successful promotion cannot contain failure fields")
        if not self.succeeded and not self.failure_code:
            raise ValueError("failed promotion requires failure_code")
        return self


@dataclass(frozen=True, slots=True)
class ValidatedModelRelease:
    """A release directory whose complete byte inventory has been checked."""

    path: Path
    manifest: ModelReleaseManifest


def canonical_json_bytes(value: BaseModel | dict[str, object]) -> bytes:
    payload = value.model_dump(mode="json") if isinstance(value, BaseModel) else value
    return json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode("utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_model_release(
    root: Path | str,
    *,
    expected_runtime_contract: str | None = None,
    package_version: str | None = None,
    require_release_name: bool = True,
) -> ValidatedModelRelease:
    """Validate exact membership, regular files, hashes, and runtime compatibility."""

    release = Path(root).resolve()
    if not release.is_dir() or release.is_symlink():
        raise ModelReleaseError("model release must be a real local directory")
    manifest_path = release / MODEL_RELEASE_MANIFEST
    if not manifest_path.is_file() or manifest_path.is_symlink():
        raise ModelReleaseError(f"model release is missing a regular {MODEL_RELEASE_MANIFEST}")
    if manifest_path.stat().st_size > _MAX_MANIFEST_BYTES:
        raise ModelReleaseError("model release manifest exceeds the 4 MiB control-file limit")
    try:
        manifest = ModelReleaseManifest.model_validate_json(manifest_path.read_bytes())
    except Exception as exc:
        raise ModelReleaseError("model release manifest is invalid") from exc

    if require_release_name and release.name != manifest.release_id:
        raise ModelReleaseError(
            f"release directory {release.name!r} does not match release_id {manifest.release_id!r}"
        )
    if expected_runtime_contract is not None and manifest.runtime_contract != expected_runtime_contract:
        raise ModelReleaseError(
            f"runtime contract mismatch: expected {expected_runtime_contract!r}, "
            f"found {manifest.runtime_contract!r}"
        )
    current_version = package_version or resolve_installed_package_version()
    try:
        compatible = Version(current_version) in SpecifierSet(manifest.compatibility_range)
    except InvalidVersion as exc:
        raise ModelReleaseError(f"installed package version is invalid: {current_version!r}") from exc
    if not compatible:
        raise ModelReleaseError(
            f"isanlp_rst {current_version} is outside model compatibility range "
            f"{manifest.compatibility_range}"
        )

    declared = {str(item.path): item for item in manifest.files}
    actual: set[str] = set()
    for path in release.rglob("*"):
        if path.is_symlink():
            raise ModelReleaseError(f"model release contains a symlink: {path.relative_to(release)}")
        if path.is_file() and path != manifest_path:
            actual.add(path.relative_to(release).as_posix())
    if actual != set(declared):
        missing = sorted(set(declared) - actual)
        unlisted = sorted(actual - set(declared))
        raise ModelReleaseError(f"model release membership mismatch; missing={missing}, unlisted={unlisted}")
    for relative, record in declared.items():
        path = release / relative
        if not path.is_file() or path.is_symlink():
            raise ModelReleaseError(f"model release member is not a regular file: {relative}")
        if path.stat().st_size != record.size_bytes:
            raise ModelReleaseError(f"model release size mismatch: {relative}")
        if sha256_file(path) != record.sha256:
            raise ModelReleaseError(f"model release SHA-256 mismatch: {relative}")
    return ValidatedModelRelease(path=release, manifest=manifest)


def load_model_release(
    store: Path | str,
    release_id: str,
    *,
    expected_runtime_contract: str,
) -> ValidatedModelRelease:
    """Resolve and validate one promoted child of the configured production store."""

    if _RELEASE_ID.fullmatch(release_id) is None:
        raise ModelReleaseError(f"unsafe release_id: {release_id!r}")
    root = Path(store).resolve()
    release = (root / release_id).resolve()
    if release.parent != root:
        raise ModelReleaseError(f"release_id escapes the production store: {release_id!r}")
    return validate_model_release(release, expected_runtime_contract=expected_runtime_contract)


__all__ = [
    "MODEL_RELEASE_MANIFEST",
    "ModelFile",
    "ModelReleaseError",
    "ModelReleaseManifest",
    "PromotionReceipt",
    "ValidatedModelRelease",
    "canonical_json_bytes",
    "load_model_release",
    "sha256_file",
    "validate_model_release",
]
