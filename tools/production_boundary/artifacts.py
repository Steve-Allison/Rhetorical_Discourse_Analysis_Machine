"""Wheel and source-distribution boundary inspection."""

import base64
import csv
import hashlib
import io
import json
from email.parser import BytesParser
from pathlib import Path, PurePosixPath
import re
import tarfile
import zipfile

import rfc8785

from rdam.rst._provenance import PROVENANCE_FIELDS
from rdam.rst._version import TOOL_NAME
from tools.production_boundary.contracts import (
    ArtifactReceipt,
)
from tools.production_boundary.identity import ReleaseIdentity


_FORBIDDEN_PARTS = frozenset({"workbench", "workbench.research", "tests", "scripts", "specs", "corpora", "experiments", "__pycache__", ".pytest_cache", ".ruff_cache", ".pixi", "graphify-out"})
_FORBIDDEN_SUFFIXES = frozenset(
    {".pem", ".key", ".p12", ".pfx", ".pickle", ".pkl", ".pyc", ".pt", ".pth", ".safetensors"}
)
_METADATA_MARKERS = (".dist-info/", ".egg-info/")
# The one import root a production wheel may carry: the machine package, with every
# technique as a sub-package (owner ruling 2026-09-02). Anything else in a wheel is
# outside the boundary (FR-006, research D5 check b).
_PRODUCTION_IMPORT_ROOTS = ("rdam/",)
_REQUIREMENT_NAME = re.compile(rb"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)")
_EXTRA_MARKER = re.compile(r"\bextra\s*==\s*['\"]([^'\"]+)['\"]")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _archive_members(path: Path) -> tuple[str, tuple[str, ...]]:
    if path.suffix == ".whl":
        with zipfile.ZipFile(path) as archive:
            return "wheel", tuple(sorted(name for name in archive.namelist() if not name.endswith("/")))
    if path.name.endswith(".tar.gz"):
        with tarfile.open(path, mode="r:gz") as archive:
            return "sdist", tuple(sorted(member.name for member in archive.getmembers() if member.isfile() or member.issym() or member.islnk()))
    raise ValueError(f"unsupported production artifact: {path}")


def _declared_dependencies(path: Path, kind: str) -> tuple[str, ...]:
    if kind == "wheel":
        with zipfile.ZipFile(path) as archive:
            metadata_names = tuple(name for name in archive.namelist() if name.endswith(".dist-info/METADATA"))
            if len(metadata_names) != 1:
                raise ValueError(f"wheel must contain exactly one METADATA file: {path}")
            payload = archive.read(metadata_names[0])
    else:
        with tarfile.open(path, mode="r:gz") as archive:
            metadata = tuple(
                member
                for member in archive.getmembers()
                if member.name.endswith("/PKG-INFO") and len(PurePosixPath(member.name).parts) == 2
            )
            if len(metadata) != 1:
                raise ValueError(f"sdist must contain exactly one root PKG-INFO file: {path}")
            stream = archive.extractfile(metadata[0])
            if stream is None:
                raise ValueError(f"cannot read sdist PKG-INFO: {path}")
            payload = stream.read()
    message = BytesParser().parsebytes(payload)
    names: set[str] = set()
    for requirement in message.get_all("Requires-Dist", ()):
        marker = requirement.partition(";")[2]
        extras = set(_EXTRA_MARKER.findall(marker))
        if extras and "formats" not in extras:
            continue
        match = _REQUIREMENT_NAME.match(requirement.encode("utf-8"))
        if match is None:
            raise ValueError(f"cannot determine dependency name from artifact requirement {requirement!r}")
        names.add(match.group(1).decode("ascii").casefold().replace("_", "-"))
    return tuple(sorted(names))


def _logical_member(kind: str, name: str) -> PurePosixPath:
    member = PurePosixPath(name)
    if kind == "sdist" and len(member.parts) > 1:
        return PurePosixPath(*member.parts[1:])
    return member


def _forbidden(kind: str, name: str) -> bool:
    member = _logical_member(kind, name)
    if any(part in _FORBIDDEN_PARTS or part.startswith(".") and part not in {".dist-info", ".egg-info"} for part in member.parts):
        return True
    if member.suffix.casefold() in _FORBIDDEN_SUFFIXES:
        return True
    lower = member.as_posix().casefold()
    if re.search(r"(^|/)(\.env|id_rsa|credentials|secrets?)(\.|/|$)", lower):
        return True
    if kind == "wheel":
        return not (lower.startswith(_PRODUCTION_IMPORT_ROOTS) or any(marker in lower for marker in _METADATA_MARKERS))
    allowed_root = {
        "pyproject.toml",
        "pixi.lock",
        "manifest.in",
        "readme.md",
        "license",
        "license_models",
        "license.txt",
        "license.md",
        "notice",
        "pkg-info",
        "setup.cfg",
    }
    return not (lower.startswith(_PRODUCTION_IMPORT_ROOTS) or lower in allowed_root or any(marker in lower for marker in _METADATA_MARKERS))


def inspect_artifact(path: Path, declared_dependencies: tuple[str, ...] = ()) -> ArtifactReceipt:
    artifact = path.resolve()
    kind, members = _archive_members(artifact)
    forbidden = tuple(member for member in members if _forbidden(kind, member))
    production = tuple(member for member in members if member not in forbidden)
    dependencies = declared_dependencies or _declared_dependencies(artifact, kind)
    return ArtifactReceipt(artifact_path=str(artifact), artifact_kind=kind, artifact_sha256=_sha256(artifact), member_count=len(members), production_members=production, forbidden_members=forbidden, declared_dependencies=dependencies)


def validate_release_artifacts(
    wheel: Path,
    sdist: Path,
    identity: ReleaseIdentity,
    *,
    expected_source_commit: str | None = None,
) -> dict[str, object]:
    """Validate the release's exact package pair and return machine-readable evidence."""

    wheel_receipt = inspect_artifact(wheel)
    sdist_receipt = inspect_artifact(sdist)
    if wheel_receipt.artifact_kind != "wheel" or sdist_receipt.artifact_kind != "sdist":
        raise ValueError("release artifact pair must be ordered as wheel then sdist")
    if not wheel_receipt.valid or not sdist_receipt.valid:
        raise ValueError("release artifacts contain forbidden members")
    wheel_evidence = _validate_wheel(wheel.resolve(), expected_source_commit, identity)
    sdist_evidence = _validate_sdist(sdist.resolve(), expected_source_commit, identity)
    if wheel_evidence["provenance"] != sdist_evidence["provenance"]:
        raise ValueError("wheel and sdist package different build provenance")
    return {
        "schema_name": "isanlp_rst.release_evidence.artifact_validation",
        "schema_version": "1.0.0",
        "wheel": wheel_receipt.model_dump(mode="json"),
        "sdist": sdist_receipt.model_dump(mode="json"),
        "wheel_validation": wheel_evidence,
        "sdist_validation": sdist_evidence,
        "valid": True,
    }


def validate_release_directory(release_directory: Path, identity: ReleaseIdentity) -> dict[str, object]:
    """Verify the published wheel and sdist pair."""

    directory = release_directory.resolve()
    expected_names = {identity.wheel_name, identity.sdist_name}
    observed_names = {path.name for path in directory.iterdir() if path.is_file()}
    if observed_names != expected_names:
        raise ValueError(
            f"published release membership differs: expected={sorted(expected_names)}, "
            f"observed={sorted(observed_names)}"
        )
    artifacts = validate_release_artifacts(
        directory / identity.wheel_name,
        directory / identity.sdist_name,
        identity,
    )
    return {
        "schema_name": "isanlp_rst.release_evidence.published_release_validation",
        "schema_version": "1.0.0",
        "artifacts": artifacts,
        "valid": True,
    }


def _rst_console_surface() -> frozenset[str]:
    """The installed command and its local HTTP projections, named after the console command."""

    return frozenset(
        {
            TOOL_NAME,
            f"{TOOL_NAME}.local-http./analyse",
            f"{TOOL_NAME}.local-http./capabilities",
            f"{TOOL_NAME}.local-http./health",
        }
    )


def _validate_wheel(path: Path, expected_source_commit: str | None, identity: ReleaseIdentity) -> dict[str, object]:
    package = identity.import_package
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        metadata_name = _one_name(names, ".dist-info/METADATA")
        record_name = _one_name(names, ".dist-info/RECORD")
        entry_points_name = _one_name(names, ".dist-info/entry_points.txt")
        metadata = BytesParser().parsebytes(archive.read(metadata_name))
        _validate_metadata(metadata, identity)
        _verify_record(archive, record_name)
        entry_points = archive.read(entry_points_name).decode("utf-8", errors="strict")
        if f"{TOOL_NAME} = {package}.rst.cli:main" not in entry_points:
            raise ValueError(f"wheel does not install the canonical {TOOL_NAME} command")
        required = {
            f"{package}/py.typed",
            f"{package}/build-provenance.json",
            f"{package}/rst/ingest/public-surface.json",
        }
        missing = required - names
        if missing or not any(name.startswith(f"{package}/rst/ingest/schemas/") for name in names):
            raise ValueError(f"wheel lacks required production contract resources: {sorted(missing)}")
        provenance = _validate_provenance(
            archive.read(f"{package}/build-provenance.json"),
            expected_source_commit,
            identity,
        )
        surface = json.loads(
            archive.read(f"{package}/rst/ingest/public-surface.json").decode("utf-8", errors="strict")
        )
        qualified = {entry["qualified_name"] for entry in surface["entries"]}
        if not _rst_console_surface() <= qualified:
            raise ValueError("wheel public surface omits installed command or local HTTP projections")
    return {
        "metadata_name": metadata.get("Name"),
        "metadata_version": metadata.get("Version"),
        "requires_python": metadata.get("Requires-Python"),
        "record_verified": True,
        "provenance": provenance,
    }


def _validate_sdist(path: Path, expected_source_commit: str | None, identity: ReleaseIdentity) -> dict[str, object]:
    package = identity.import_package
    with tarfile.open(path, mode="r:gz") as archive:
        members = {member.name: member for member in archive.getmembers() if member.isfile()}
        pkg_info_name = _one_name(set(members), "/PKG-INFO")
        pkg_stream = archive.extractfile(members[pkg_info_name])
        if pkg_stream is None:
            raise ValueError("sdist PKG-INFO cannot be read")
        metadata = BytesParser().parsebytes(pkg_stream.read())
        _validate_metadata(metadata, identity)
        provenance_name = _one_name(set(members), f"/{package}/build-provenance.json")
        provenance_stream = archive.extractfile(members[provenance_name])
        if provenance_stream is None:
            raise ValueError("sdist build provenance cannot be read")
        provenance = _validate_provenance(provenance_stream.read(), expected_source_commit, identity)
        required_suffixes = {
            f"/{package}/py.typed",
            f"/{package}/rst/ingest/public-surface.json",
        }
        missing = {
            suffix
            for suffix in required_suffixes
            if not any(name.endswith(suffix) for name in members)
        }
        if missing or not any(f"/{package}/rst/ingest/schemas/" in name for name in members):
            raise ValueError(f"sdist lacks required production contract resources: {sorted(missing)}")
    return {
        "metadata_name": metadata.get("Name"),
        "metadata_version": metadata.get("Version"),
        "requires_python": metadata.get("Requires-Python"),
        "provenance": provenance,
    }


def _validate_metadata(metadata: object, identity: ReleaseIdentity) -> None:
    getter = getattr(metadata, "get", None)
    if not callable(getter):
        raise TypeError("artifact metadata is not message-like")
    if getter("Name") != identity.distribution or getter("Version") != identity.version:
        raise ValueError(f"artifact metadata does not identify {identity.distribution} {identity.version}")
    if getter("Requires-Python") != ">=3.14":
        raise ValueError("artifact metadata does not require Python 3.14")


def _verify_record(archive: zipfile.ZipFile, record_name: str) -> None:
    rows = csv.reader(io.StringIO(archive.read(record_name).decode("utf-8", errors="strict")))
    seen: set[str] = set()
    for name, encoded_hash, size in rows:
        if name in seen:
            raise ValueError(f"wheel RECORD contains duplicate path: {name}")
        seen.add(name)
        if name == record_name:
            if encoded_hash or size:
                raise ValueError("wheel RECORD self-entry must omit hash and size")
            continue
        algorithm, separator, encoded = encoded_hash.partition("=")
        if separator != "=" or algorithm != "sha256":
            raise ValueError(f"wheel RECORD entry lacks SHA-256: {name}")
        payload = archive.read(name)
        observed = base64.urlsafe_b64encode(hashlib.sha256(payload).digest()).rstrip(b"=").decode("ascii")
        if observed != encoded or int(size) != len(payload):
            raise ValueError(f"wheel RECORD entry does not verify: {name}")
    if seen != set(archive.namelist()):
        raise ValueError("wheel RECORD membership differs from archive membership")


def _validate_provenance(payload: bytes, expected_source_commit: str | None, identity: ReleaseIdentity) -> dict[str, object]:
    parsed = json.loads(payload.decode("utf-8", errors="strict"))
    # The build writes the resource as ``rfc8785.dumps(...) + b"\n"`` (Verified 2026-09-02 at
    # tools/production_boundary/build.py:_provenance_bytes), so any other byte form is a
    # rewritten resource, not the one the build produced.
    if payload != rfc8785.dumps(parsed) + b"\n":
        raise ValueError("build provenance is not the RFC 8785 byte form the build writes")
    if not isinstance(parsed, dict) or set(parsed) != PROVENANCE_FIELDS:
        # Exactly what the installed runtime reader (rdam.rst._provenance) enforces, so
        # a schema drift fails this cheap gate rather than the clean install.
        raise ValueError("artifact build provenance does not carry the exact runtime field set")
    if parsed.get("schema_name") != "isanlp_rst.build_provenance":
        raise ValueError("artifact build provenance names the wrong contract")
    if parsed.get("package_name") != identity.distribution:
        raise ValueError("artifact provenance names a different distribution")
    if parsed.get("package_version") != identity.version:
        raise ValueError("artifact provenance version contradicts package version")
    if expected_source_commit is not None and parsed.get("source_commit") != expected_source_commit:
        raise ValueError("artifact provenance contradicts the expected source commit")
    return parsed


def _one_name(names: set[str], suffix: str) -> str:
    matches = tuple(name for name in names if name.endswith(suffix))
    if len(matches) != 1:
        raise ValueError(f"expected one artifact member ending {suffix!r}, found {matches}")
    return matches[0]


__all__ = [
    "inspect_artifact",
    "validate_release_artifacts",
    "validate_release_directory",
]
