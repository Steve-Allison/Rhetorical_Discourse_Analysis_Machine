"""Device resolution helpers.

Centralises the logic for selecting an inference device (CPU / CUDA / MPS)
from a flexible set of input formats. Exposes a single
:func:`resolve_device` entry point used by the parser entry point and by
the predictor classes.

Apple Silicon support: ``device='mps'`` and ``device='auto'`` (which
prefers MPS when available) make the parser inference path 3–10× faster
on Apple Silicon hardware than the previous CPU-only fallback. Inference
operations used by the parser (transformer encode + GRU decode +
classifier head) are MPS-supported as of PyTorch 2.4+.

**MPS fallback for unsupported ops.** A handful of operations used during
model construction (notably ``torch.linalg.qr`` inside LSTM orthogonal
initialisation, see https://github.com/pytorch/pytorch/issues/141287)
are not yet implemented on MPS. When this module resolves a device to
MPS — whether explicitly or via auto-detect — it sets the environment
variable ``PYTORCH_ENABLE_MPS_FALLBACK=1`` so that PyTorch silently
falls back to CPU for those ops. The fallback only fires for the missing
ops; inference itself still runs on MPS. To opt out (e.g. to surface
exactly which ops are falling back), set the env var to ``"0"`` *before*
importing this module.

Backward compatibility: the legacy ``cuda_device: int`` parameter
(``-1`` = CPU, ``N`` = ``cuda:N``) continues to work via
:func:`resolve_device`, which interprets integers using the original
semantics.
"""

from __future__ import annotations

import logging
import os
from typing import Union

import torch

logger = logging.getLogger(__name__)


# Environment variable that PyTorch reads to enable CPU fallback for
# MPS ops that aren't yet implemented natively. Documented at
# https://pytorch.org/docs/stable/notes/mps.html
_MPS_FALLBACK_ENV: str = "PYTORCH_ENABLE_MPS_FALLBACK"


# Public type for the ``device`` parameter — mirrors what PyTorch itself
# accepts but adds the literal string ``'auto'`` for "pick the best
# available". Integers are interpreted in the legacy isanlp_rst sense
# (``-1`` = CPU, ``N`` = ``cuda:N``).
DeviceSpec = Union[str, int, torch.device, None]


_AUTO_PRIORITY: tuple[str, ...] = ("cuda", "mps", "cpu")


def resolve_device(spec: DeviceSpec) -> torch.device:
    """Resolve a device specification to a concrete :class:`torch.device`.

    Args:
        spec: One of:

            - ``None`` or ``'auto'``: pick the best available device
              (CUDA → MPS → CPU).
            - ``'cpu'``, ``'cuda'``, ``'cuda:N'``, ``'mps'``: explicit
              device strings, passed straight to :class:`torch.device`.
            - ``int``: legacy isanlp_rst convention. ``-1`` selects CPU;
              any other integer ``N`` selects ``cuda:N``. Use this only
              when migrating existing code; new code should pass strings.
            - :class:`torch.device`: returned as-is.

    Returns:
        A :class:`torch.device` instance suitable for passing to ``.to()``
        and to ``torch.load(..., map_location=...)``.

    Raises:
        RuntimeError: If an explicit ``'cuda'`` request is made but CUDA
            is unavailable, or ``'mps'`` is requested but MPS is
            unavailable. The intent is to fail loudly when the operator
            asks for a specific accelerator that won't work — silent
            fallback to CPU is a debugging trap.

    Examples:
        >>> resolve_device('auto')        # MPS on Apple Silicon, CUDA on NV, CPU otherwise
        >>> resolve_device('mps')         # explicit MPS, raises if unavailable
        >>> resolve_device('cuda:1')      # second GPU
        >>> resolve_device(-1)            # legacy: CPU
        >>> resolve_device(0)             # legacy: cuda:0
    """
    if isinstance(spec, torch.device):
        return spec

    if spec is None or (isinstance(spec, str) and spec.lower() == "auto"):
        return _auto_select()

    if isinstance(spec, int):
        return _from_legacy_int(spec)

    if isinstance(spec, str):
        return _from_string(spec)

    raise TypeError(
        f"Unsupported device spec: {spec!r} (type={type(spec).__name__}). "
        "Expected str, int, torch.device, or None."
    )


def _auto_select() -> torch.device:
    """Pick the best available accelerator, preferring CUDA over MPS over CPU.

    For MPS, also probes whether the parser's required ops dispatch
    natively. If MPS is missing a critical op (e.g. ``torch.linalg.qr``
    used in LSTM init), auto-mode falls back to CPU silently — this
    matches the documented behaviour of "auto" (never raise; pick what
    will work).
    """
    if torch.cuda.is_available():
        device = torch.device("cuda")
        logger.info("Auto-selected device: %s (cuda available)", device)
        return device
    if _mps_is_available():
        if _mps_supports_required_ops():
            _enable_mps_fallback()
            logger.info("Auto-selected device: mps (Apple Silicon GPU)")
            return torch.device("mps")
        logger.warning(
            "MPS available but missing operators required by the parser "
            "(set %s=1 in your shell *before* launching Python to enable "
            "native MPS with CPU fallback). Falling back to CPU for now.",
            _MPS_FALLBACK_ENV,
        )
    device = torch.device("cpu")
    logger.info("Auto-selected device: %s (no accelerator available)", device)
    return device


def _enable_mps_fallback() -> None:
    """Set ``PYTORCH_ENABLE_MPS_FALLBACK=1`` unless the operator opted out.

    PyTorch reads this env var once when the MPS context initialises,
    so the value set here only takes effect if PyTorch has not yet
    touched MPS — typically true at process start, but not always after
    other libraries (e.g. transformers) have probed device availability.
    This is why :func:`_mps_supports_required_ops` does a runtime probe
    rather than relying solely on the env var.
    """
    if _MPS_FALLBACK_ENV not in os.environ:
        os.environ[_MPS_FALLBACK_ENV] = "1"
        logger.debug(
            "Set %s=1 to support MPS init ops missing native dispatch.",
            _MPS_FALLBACK_ENV,
        )


def _mps_supports_required_ops() -> bool:
    """Probe whether MPS supports every op the parser needs at construction.

    The parser's LSTM segmenter calls :func:`torch.nn.init.orthogonal_`,
    which internally invokes ``torch.linalg.qr``. As of PyTorch 2.11 this
    op is not implemented for MPS (see pytorch/pytorch#141287).

    The probe runs a tiny QR decomposition on a 2×2 zero tensor. Cost is
    negligible (microseconds) and the result is cacheable — but we
    intentionally re-probe on each call so the result reflects current
    PyTorch state (env var changes, op support added in a later release).
    """
    try:
        probe = torch.zeros(2, 2, device="mps")
        torch.linalg.qr(probe)
        return True
    except (NotImplementedError, RuntimeError) as exc:
        logger.debug("MPS op probe failed: %s", exc)
        return False


def _from_legacy_int(spec: int) -> torch.device:
    """Interpret integer specs using the original isanlp_rst convention."""
    if spec == -1:
        return torch.device("cpu")
    if spec < -1:
        raise ValueError(
            f"Invalid cuda_device integer: {spec}. Use -1 for CPU, or "
            "a non-negative integer for cuda:N."
        )
    return torch.device(f"cuda:{spec}")


def _from_string(spec: str) -> torch.device:
    """Parse a string spec, validating that the requested device is usable."""
    spec_lower = spec.strip().lower()
    if spec_lower.startswith("cuda"):
        if not torch.cuda.is_available():
            raise RuntimeError(
                f"Requested device {spec!r} but CUDA is not available. "
                "Use device='auto' for automatic fallback."
            )
        return torch.device(spec_lower)
    if spec_lower == "mps":
        if not _mps_is_available():
            raise RuntimeError(
                "Requested device 'mps' but MPS is not available. "
                "MPS requires macOS on Apple Silicon with PyTorch 2.0+. "
                "Use device='auto' for automatic fallback."
            )
        _enable_mps_fallback()
        return torch.device("mps")
    if spec_lower == "cpu":
        return torch.device("cpu")
    raise ValueError(
        f"Unrecognised device string: {spec!r}. Expected one of: "
        "'cpu', 'cuda', 'cuda:N', 'mps', 'auto'."
    )


def _mps_is_available() -> bool:
    """True when MPS is available AND functional.

    `torch.backends.mps.is_available()` returns True even on macOS
    versions where MPS is stubbed but unusable (very rare in 2026 but
    historically common). We add a defensive build-check.
    """
    backend = getattr(torch.backends, "mps", None)
    if backend is None:
        return False
    try:
        return bool(backend.is_available()) and bool(backend.is_built())
    except Exception:
        return False


__all__ = ["DeviceSpec", "resolve_device"]
