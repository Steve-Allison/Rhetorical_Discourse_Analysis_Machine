"""Runtime provenance for production analyses."""

from collections.abc import Mapping
from importlib import resources
import json
import subprocess
from functools import cache
from pathlib import Path

from rdam.rst._version import PACKAGE_NAME, resolve_installed_package_version


resolve_package_version = resolve_installed_package_version

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
def load_build_provenance() -> Mapping[str, str | int] | None:
    """Load and strictly validate packaged exact-source provenance when present."""

    resource = resources.files(PACKAGE_NAME).joinpath("build-provenance.json")
    if not resource.is_file():
        return None
    payload = json.loads(resource.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or set(payload) != PROVENANCE_FIELDS:
        raise ValueError("packaged build provenance has an unexpected schema")
    if payload.get("schema_name") != "isanlp_rst.build_provenance":
        raise ValueError("packaged build provenance has the wrong contract")
    if payload.get("schema_version") != "1.0.0":
        raise ValueError("packaged build provenance has an unsupported version")
    if payload.get("package_name") != PACKAGE_NAME:
        raise ValueError("packaged build provenance names the wrong package")
    if payload.get("package_version") != resolve_package_version():
        raise ValueError("packaged build provenance contradicts installed metadata")
    if not all(isinstance(value, str | int) for value in payload.values()):
        raise TypeError("packaged build provenance values must be strings or integers")
    return payload


@cache
def resolve_source_revision() -> str:
    """Return the checkout commit and dirty state, or ``unknown`` off-tree."""

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
            ["git", "status", "--porcelain", "--untracked-files=no"],
            cwd=repository_root,
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    return f"{revision}-dirty" if dirty else revision


__all__ = ["PROVENANCE_FIELDS", "load_build_provenance", "resolve_package_version", "resolve_source_revision"]
