"""Shared runtime helpers for the format-native entry points.

One home for the device translation, tool-version resolution, and
inventory selection that the ``docling`` / ``doclang`` / ``markdown``
``_entry`` modules previously each carried a copy of.
"""

from __future__ import annotations

import subprocess
from functools import cache
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path


def _gpu_available() -> bool:
    """True when torch reports a usable CUDA or MPS backend.

    torch is imported lazily — the entry points only need it when a
    ``Parser`` is actually constructed, and unit tests of the pure
    helpers should not pay the torch import.
    """
    import torch

    return torch.cuda.is_available() or torch.backends.mps.is_available()


def resolve_device(device: str) -> int:
    """Translate the string device API to ``cuda_device: int`` on ``Parser``.

    ``"auto"`` → 0 when torch reports a CUDA or MPS backend, else -1
    (CPU). ``"cpu"`` → -1; ``"mps"`` → 0 (the integer is ignored on
    Apple Silicon); ``"cuda"`` / ``"cuda:0"`` → 0; ``"cuda:N"`` → N.
    """
    match device:
        case "auto":
            return 0 if _gpu_available() else -1
        case "cpu":
            return -1
        case "mps" | "cuda" | "cuda:0":
            return 0
        case _ if device.startswith("cuda:"):
            try:
                n = int(device.split(":", 1)[1])
            except ValueError as exc:
                raise ValueError(f"Invalid CUDA device specifier: {device!r}") from exc
            if n < 0:
                raise ValueError(f"CUDA device index must be non-negative: {device!r}")
            return n
        case _:
            raise ValueError(
                f"Unrecognised device {device!r}. Expected one of "
                f"'auto', 'cpu', 'mps', 'cuda', 'cuda:N'."
            )


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
    except (OSError, subprocess.SubprocessError):
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


__all__ = ["resolve_device", "resolve_inventory", "resolve_tool_version"]
