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

from rdam.rst._version import PACKAGE_NAME, resolve_installed_package_version

MODEL_RELEASE_MANIFEST = "release-manifest.json"
COMPATIBILITY_REDECLARATION_SUFFIX = ".compatibility.json"
COMPATIBILITY_REDECLARATION_SCHEMA = "rdam.rst.model_release_compatibility/v1"
_MAX_MANIFEST_BYTES = 4 * 1024 * 1024
_RELEASE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_PARSER_RUNTIME_CONTRACT_PREFIX = "isanlp_rst.parser/"
_PARSER_FILE_ROLES = {
    "configuration",
    "runtime-configuration",
    "model-weights",
    "legacy-model-weights",
    "encoder_config",
    "parser_state",
    "relation_inventory",
    "relation-inventory",
    "tokenizer",
    "weights",
}


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
    def complete_coherent_manifest(self) -> ModelReleaseManifest:
        paths = [item.path for item in self.files]
        if len(paths) != len(set(paths)):
            raise ValueError("model release file paths must be unique")
        if bool(self.evaluation_evidence) == bool(self.evaluation_unavailable_reason):
            raise ValueError("provide evaluation_evidence or evaluation_unavailable_reason, exactly one")
        try:
            SpecifierSet(self.compatibility_range)
        except InvalidSpecifier as exc:
            raise ValueError("compatibility_range must be a valid Python version specifier") from exc
        if self.runtime_contract.startswith(_PARSER_RUNTIME_CONTRACT_PREFIX):
            _validate_parser_files(self.files)
        return self

    @property
    def manifest_sha256(self) -> str:
        return hashlib.sha256(canonical_json_bytes(self)).hexdigest()


class CompatibilityRedeclaration(_StrictModel):
    """An explicit, evidence-backed re-declaration of a release's package compatibility.

    A release manifest is immutable: its ``compatibility_range`` is the promoter's claim at
    promotion time and cannot be edited without changing the release's identity. When a
    later package version is shown to run the release unchanged — the runtime contract is
    the same and the equivalence procedure passed — that finding is recorded beside the
    release as ``<store>/<release_id>.compatibility.json``, naming the exact manifest it
    re-declares. The loader honours it only for that manifest.
    """

    schema_version: str = COMPATIBILITY_REDECLARATION_SCHEMA
    release_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
    manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    compatibility_range: str = Field(min_length=1)
    declared_at: datetime
    declared_by: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    basis: tuple[str, ...] = Field(min_length=1)

    @field_validator("schema_version")
    @classmethod
    def known_schema(cls, value: str) -> str:
        if value != COMPATIBILITY_REDECLARATION_SCHEMA:
            raise ValueError(f"unsupported compatibility re-declaration schema: {value!r}")
        return value

    @field_validator("compatibility_range")
    @classmethod
    def valid_specifier(cls, value: str) -> str:
        try:
            SpecifierSet(value)
        except InvalidSpecifier as exc:
            raise ValueError("compatibility_range must be a valid Python version specifier") from exc
        return value


class ParserCapacity(_StrictModel):
    """Stable safe unit capacity for recursive production analysis."""

    unit: str = Field(pattern=r"^(edu_count|token_count)$")
    maximum: int = Field(gt=1)
    source: str = Field(min_length=1)


class ModelReleaseIdentity(_StrictModel):
    """Complete released-model identity used by analytical caches."""

    release_id: str = Field(min_length=1)
    manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    runtime_contract: str = Field(min_length=1)
    architecture: str = Field(min_length=1)
    files: tuple[ModelFile, ...] = Field(min_length=1)
    capacity: ParserCapacity

    @property
    def semantic_digest(self) -> str:
        return hashlib.sha256(canonical_json_bytes(self)).hexdigest()


@dataclass(frozen=True, slots=True)
class ValidatedModelRelease:
    """A release directory whose complete byte inventory has been checked."""

    path: Path
    manifest: ModelReleaseManifest
    redeclaration: CompatibilityRedeclaration | None = None

    @property
    def compatibility_range(self) -> str:
        """The range in force: a re-declaration for this exact manifest, else the manifest's own."""

        if self.redeclaration is not None:
            return self.redeclaration.compatibility_range
        return self.manifest.compatibility_range

    def analysis_identity(self, capacity: ParserCapacity) -> ModelReleaseIdentity:
        """Return the immutable identity consumed by production analysis."""

        return ModelReleaseIdentity(
            release_id=self.manifest.release_id,
            manifest_sha256=self.manifest.manifest_sha256,
            runtime_contract=self.manifest.runtime_contract,
            architecture=self.manifest.architecture,
            files=self.manifest.files,
            capacity=capacity,
        )

    def one_file_for_role(self, role: str) -> ModelFile:
        """Return the one declared member for a singleton runtime role."""

        matches = tuple(item for item in self.manifest.files if item.role == role)
        if len(matches) != 1:
            raise ModelReleaseError(f"model release requires exactly one {role!r} member; found {len(matches)}")
        return matches[0]


def canonical_json_bytes(value: BaseModel | dict[str, object]) -> bytes:
    payload = value.model_dump(mode="json") if isinstance(value, BaseModel) else value
    return json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode("utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def compatibility_redeclaration_path(release: Path) -> Path:
    """Where a release's compatibility re-declaration lives: beside, never inside, the release."""

    return release.parent / f"{release.name}{COMPATIBILITY_REDECLARATION_SUFFIX}"


def load_compatibility_redeclaration(
    release: Path,
    manifest: ModelReleaseManifest,
) -> CompatibilityRedeclaration | None:
    """The re-declaration beside ``release`` if it names exactly this manifest; ``None`` if absent."""

    path = compatibility_redeclaration_path(release)
    if not path.is_file() or path.is_symlink():
        return None
    if path.stat().st_size > _MAX_MANIFEST_BYTES:
        raise ModelReleaseError("compatibility re-declaration exceeds the 4 MiB control-file limit")
    try:
        redeclaration = CompatibilityRedeclaration.model_validate_json(path.read_bytes())
    except Exception as exc:
        raise ModelReleaseError("compatibility re-declaration is invalid") from exc
    if redeclaration.release_id != manifest.release_id or redeclaration.manifest_sha256 != manifest.manifest_sha256:
        raise ModelReleaseError(
            f"compatibility re-declaration beside {release.name!r} does not name this release's manifest"
        )
    return redeclaration


def validate_model_release(
    root: Path | str,
    *,
    expected_runtime_contract: str | None = None,
    package_version: str | None = None,
    require_release_name: bool = True,
) -> ValidatedModelRelease:
    """Validate exact membership, regular files, hashes, and runtime compatibility.

    Compatibility is judged against the manifest's range, or against a re-declaration
    beside the release that names this exact manifest (``CompatibilityRedeclaration``).
    """

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
        raise ModelReleaseError(f"release directory {release.name!r} does not match release_id {manifest.release_id!r}")
    if expected_runtime_contract is not None and manifest.runtime_contract != expected_runtime_contract:
        raise ModelReleaseError(
            f"runtime contract mismatch: expected {expected_runtime_contract!r}, found {manifest.runtime_contract!r}"
        )
    redeclaration = load_compatibility_redeclaration(release, manifest)
    compatibility_range = (
        redeclaration.compatibility_range if redeclaration is not None else manifest.compatibility_range
    )
    current_version = package_version or resolve_installed_package_version()
    try:
        compatible = Version(current_version) in SpecifierSet(compatibility_range)
    except InvalidVersion as exc:
        raise ModelReleaseError(f"installed package version is invalid: {current_version!r}") from exc
    if not compatible:
        source = "re-declared" if redeclaration is not None else "declared"
        raise ModelReleaseError(
            f"{PACKAGE_NAME} {current_version} is outside the {source} model compatibility range {compatibility_range}"
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
    return ValidatedModelRelease(path=release, manifest=manifest, redeclaration=redeclaration)


def load_model_release(
    store: Path | str,
    release_id: str,
    *,
    expected_runtime_contract: str | None = None,
) -> ValidatedModelRelease:
    """Resolve and validate one promoted child of the configured production store."""

    if _RELEASE_ID.fullmatch(release_id) is None:
        raise ModelReleaseError(f"unsafe release_id: {release_id!r}")
    root = Path(store).resolve()
    release = (root / release_id).resolve()
    if release.parent != root:
        raise ModelReleaseError(f"release_id escapes the production store: {release_id!r}")
    return validate_model_release(release, expected_runtime_contract=expected_runtime_contract)


def peek_runtime_contract(release_dir: Path | str) -> str:
    """Safely inspect a release directory to read its runtime_contract without full validation."""
    manifest_path = Path(release_dir) / MODEL_RELEASE_MANIFEST
    if not manifest_path.is_file():
        raise ModelReleaseError(f"Missing {MODEL_RELEASE_MANIFEST} in {release_dir}")
    try:
        data = json.loads(manifest_path.read_bytes())
        contract = data.get("runtime_contract")
        if not isinstance(contract, str):
            raise ModelReleaseError(f"Invalid or missing runtime_contract in {manifest_path}")
        return contract
    except (OSError, ValueError) as exc:
        raise ModelReleaseError(f"Failed to read runtime contract from {manifest_path}") from exc


def _validate_parser_files(files: tuple[ModelFile, ...]) -> None:
    roles = [item.role for item in files]
    unknown = set(roles) - _PARSER_FILE_ROLES
    if unknown:
        raise ValueError(f"Parser release contains unsupported runtime roles: {sorted(unknown)}")
    if not any(r in roles for r in ("parser_state", "weights", "model-weights", "legacy-model-weights")):
        raise ValueError("Parser release requires at least one parser_state, weights, or model-weights file")


__all__ = [
    "COMPATIBILITY_REDECLARATION_SCHEMA",
    "COMPATIBILITY_REDECLARATION_SUFFIX",
    "MODEL_RELEASE_MANIFEST",
    "CompatibilityRedeclaration",
    "ModelFile",
    "ModelReleaseError",
    "ModelReleaseIdentity",
    "ModelReleaseManifest",
    "ParserCapacity",
    "ValidatedModelRelease",
    "canonical_json_bytes",
    "compatibility_redeclaration_path",
    "load_compatibility_redeclaration",
    "load_model_release",
    "peek_runtime_contract",
    "sha256_file",
    "validate_model_release",
]
