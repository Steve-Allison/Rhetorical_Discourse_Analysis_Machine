"""Runtime provenance for production analyses."""

import subprocess
from functools import cache
from pathlib import Path

from isanlp_rst._version import resolve_installed_package_version


resolve_package_version = resolve_installed_package_version


@cache
def resolve_source_revision() -> str:
    """Return the checkout commit and dirty state, or ``unknown`` off-tree."""

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


__all__ = ["resolve_package_version", "resolve_source_revision"]
