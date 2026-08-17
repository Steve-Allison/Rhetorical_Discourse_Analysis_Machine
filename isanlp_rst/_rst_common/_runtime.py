"""Shared runtime helpers for the format-native entry points.

One home for the device translation, tool-version resolution, and
inventory selection that the ``docling`` / ``doclang`` / ``markdown``
``_entry`` modules previously each carried a copy of.
"""

import subprocess
from functools import cache
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path


@cache
def resolve_tool_version() -> str:
    """Resolve a stable tool-version string.

    Tries, in order: ``git describe --always --dirty`` (when run inside a
    git checkout); ``importlib.metadata.version("isanlp_rst")`` (when
    installed); ``"unknown"`` (fallback). Never raises.
    """
    package_dir = Path(__file__).resolve().parent.parent.parent
    try:
        result = subprocess.run(
            ["git", "describe", "--always", "--dirty"],
            cwd=package_dir,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except OSError, subprocess.SubprocessError:
        pass

    try:
        return version("isanlp_rst")
    except PackageNotFoundError:
        pass

    return "unknown"


def resolve_inventory(hf_model_version: str, relinventory: str | None) -> str:
    """Pick the inventory string for result metadata.

    Explicit ``relinventory`` wins; otherwise fall back to
    ``hf_model_version`` as a coarse identifier.
    """
    return relinventory or hf_model_version


__all__ = ["resolve_inventory", "resolve_tool_version"]
