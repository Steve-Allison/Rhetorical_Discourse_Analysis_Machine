"""Distribution and source-revision provenance owned by the machine runtime."""

from collections.abc import Mapping
from functools import cache
from importlib import resources
from importlib.metadata import PackageNotFoundError, version
import json
from pathlib import Path
import subprocess
from typing import Any, cast

PACKAGE_NAME = "rdam"
INSTRUCTIONS_REVISION_SEPARATOR = ":instructions:"
PROVENANCE_FIELDS = frozenset(
    {
        "schema_name",
        "schema_version",
        "package_name",
        "package_version",
        "production_contract",
        "production_contract_version",
        "source_commit",
        "source_tree",
        "source_archive_sha256",
        "source_date_epoch",
        "build_input_sha256",
        "build_tool",
    }
)


@cache
def installed_package_version() -> str:
    """Return installed distribution metadata, or ``unknown`` outside an install."""

    try:
        return version(PACKAGE_NAME)
    except PackageNotFoundError:
        return "unknown"


@cache
def load_build_provenance() -> Mapping[str, str | int] | None:
    """Load and strictly validate packaged exact-source provenance when present."""

    resource = resources.files(PACKAGE_NAME).joinpath("build-provenance.json")
    if not resource.is_file():
        return None
    raw: Any = json.loads(resource.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("packaged build provenance has an unexpected schema")
    payload = cast(dict[str, object], raw)
    if set(payload).symmetric_difference(PROVENANCE_FIELDS):
        raise ValueError("packaged build provenance has an unexpected schema")
    if payload.get("schema_name") != "isanlp_rst.build_provenance":
        raise ValueError("packaged build provenance has the wrong contract")
    if payload.get("schema_version") != "1.0.0":
        raise ValueError("packaged build provenance has an unsupported version")
    if payload.get("package_name") != PACKAGE_NAME:
        raise ValueError("packaged build provenance names the wrong package")
    if payload.get("package_version") != installed_package_version():
        raise ValueError("packaged build provenance contradicts installed metadata")
    if not all(isinstance(value, str | int) for value in payload.values()):
        raise TypeError("packaged build provenance values must be strings or integers")
    return cast(Mapping[str, str | int], payload)


@cache
def resolve_source_revision() -> str:
    """Return the packaged commit or checkout commit plus dirty-state evidence."""

    packaged = load_build_provenance()
    if packaged is not None:
        source_commit = packaged["source_commit"]
        if not isinstance(source_commit, str):
            raise TypeError("packaged source commit must be a string")
        return source_commit
    repository_root = Path(__file__).resolve().parents[1]
    try:
        revision = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repository_root,
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        ).stdout.strip()
        dirty = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repository_root,
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        ).stdout.strip()
    except OSError, subprocess.SubprocessError:
        return "unknown"
    return f"{revision}-dirty" if dirty else revision


__all__ = [
    "PROVENANCE_FIELDS",
    "installed_package_version",
    "load_build_provenance",
    "resolve_source_revision",
]
