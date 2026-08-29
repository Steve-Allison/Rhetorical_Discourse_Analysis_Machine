"""Wheel and source-distribution boundary inspection."""

import hashlib
from email.parser import BytesParser
from pathlib import Path, PurePosixPath
import re
import tarfile
import zipfile

from tools.production_boundary.contracts import ArtifactReceipt


_FORBIDDEN_PARTS = frozenset({"workbench", "workbench.research", "tests", "scripts", "specs", "corpora", "experiments", "__pycache__", ".pytest_cache", ".ruff_cache", ".pixi", "graphify-out"})
_FORBIDDEN_SUFFIXES = frozenset({".pem", ".key", ".p12", ".pfx", ".pickle", ".pkl", ".pyc"})
_METADATA_MARKERS = (".dist-info/", ".egg-info/")
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
        return not (lower.startswith("isanlp_rst/") or any(marker in lower for marker in _METADATA_MARKERS))
    allowed_root = {"pyproject.toml", "manifest.in", "readme.md", "license", "license_models", "license.txt", "license.md", "notice", "pkg-info", "setup.cfg"}
    return not (lower.startswith("isanlp_rst/") or lower in allowed_root or any(marker in lower for marker in _METADATA_MARKERS))


def inspect_artifact(path: Path, declared_dependencies: tuple[str, ...] = ()) -> ArtifactReceipt:
    artifact = path.resolve()
    kind, members = _archive_members(artifact)
    forbidden = tuple(member for member in members if _forbidden(kind, member))
    production = tuple(member for member in members if member not in forbidden)
    dependencies = declared_dependencies or _declared_dependencies(artifact, kind)
    return ArtifactReceipt(artifact_path=str(artifact), artifact_kind=kind, artifact_sha256=_sha256(artifact), member_count=len(members), production_members=production, forbidden_members=forbidden, declared_dependencies=dependencies)
