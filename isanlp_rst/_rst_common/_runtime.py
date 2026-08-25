"""Shared runtime helpers for the format-native entry points.

One home for the device translation, tool-version resolution, and
inventory selection that the ``docling`` / ``doclang`` / ``markdown``
``_entry`` modules previously each carried a copy of.
"""

import subprocess
from functools import cache
from pathlib import Path

from isanlp_rst._version import resolve_installed_package_version


resolve_package_version = resolve_installed_package_version


def resolve_tool_version() -> str:
    """Backward-compatible name for installed semantic package version."""

    return resolve_package_version()


@cache
def resolve_source_revision() -> str:
    """Return the checkout commit, with dirty state, independently of SemVer."""

    repository_root = Path(__file__).resolve().parents[2]
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


def resolve_inventory(hf_model_version: str, relinventory: str | None) -> str:
    """Pick the inventory string for result metadata.

    Explicit ``relinventory`` wins; otherwise fall back to
    ``hf_model_version`` as a coarse identifier.
    """
    return relinventory or hf_model_version


__all__ = ["resolve_inventory", "resolve_package_version", "resolve_source_revision", "resolve_tool_version"]
