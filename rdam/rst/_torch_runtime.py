"""One authority for PyTorch import ordering, devices, and inference dtypes."""

from dataclasses import dataclass
import os
from importlib import import_module
from typing import TYPE_CHECKING
import warnings

os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")

if TYPE_CHECKING:
    import torch
else:
    torch = import_module("torch")


@dataclass(frozen=True, slots=True)
class DeviceProbe:
    """Immutable accelerator-availability snapshot, injectable in tests."""

    cuda_available: bool = False
    cuda_device_count: int = 0
    mps_available: bool = False

    @classmethod
    def detect(cls) -> DeviceProbe:
        cuda_available = torch.cuda.is_available()
        return cls(
            cuda_available=cuda_available,
            cuda_device_count=torch.cuda.device_count() if cuda_available else 0,
            mps_available=torch.backends.mps.is_available() and torch.backends.mps.is_built(),
        )


def _device_from_spec(spec: str, probe: DeviceProbe) -> torch.device:
    key = spec.strip().casefold()
    if key == "cpu":
        return torch.device("cpu")
    if key == "auto":
        if probe.cuda_available:
            return torch.device("cuda:0")
        if probe.mps_available:
            return torch.device("mps")
        return torch.device("cpu")
    if key == "mps":
        if not probe.mps_available:
            raise RuntimeError("device='mps' requested but MPS is not available on this host.")
        return torch.device("mps")
    if key == "cuda" or key.startswith("cuda:"):
        if not probe.cuda_available:
            raise RuntimeError(f"device={spec!r} requested but CUDA is not available on this host.")
        if key == "cuda":
            return torch.device("cuda:0")
        try:
            index = int(key.partition(":")[2])
        except ValueError as exc:
            raise ValueError(f"Invalid CUDA device specifier: {spec!r}") from exc
        if index < 0:
            raise ValueError(f"CUDA device index must be non-negative: {spec!r}")
        if index >= probe.cuda_device_count:
            raise ValueError(f"CUDA device index {index} is out of range (device_count={probe.cuda_device_count}).")
        return torch.device(f"cuda:{index}")
    raise ValueError(f"Unrecognised device {spec!r}. Expected 'auto', 'cpu', 'mps', 'cuda', or 'cuda:N'.")


def resolve_device(
    device: str | torch.device | None = None,
    cuda_device: int | None = None,
    *,
    probe: DeviceProbe | None = None,
) -> torch.device:
    """Resolve the canonical device API and its deprecated integer shim."""

    resolved_probe = probe if probe is not None else DeviceProbe.detect()
    if cuda_device is not None:
        if device is not None:
            raise ValueError("Pass either `device` (preferred) or `cuda_device` (deprecated), not both.")
        if type(cuda_device) is not int:
            raise ValueError(f"cuda_device must be an int; got {type(cuda_device).__name__}.")
        if cuda_device < -1:
            raise ValueError(f"cuda_device must be -1 (CPU) or >= 0 (GPU); got {cuda_device!r}.")
        if cuda_device == -1:
            resolved = torch.device("cpu")
        elif resolved_probe.cuda_available:
            if cuda_device >= resolved_probe.cuda_device_count:
                raise ValueError(
                    f"CUDA device index {cuda_device} is out of range "
                    f"(device_count={resolved_probe.cuda_device_count})."
                )
            resolved = torch.device(f"cuda:{cuda_device}")
        elif resolved_probe.mps_available:
            resolved = torch.device("mps")
        else:
            raise RuntimeError(
                f"cuda_device={cuda_device} requested but no GPU backend is available; pass device='cpu'."
            )
        warnings.warn(
            "`cuda_device` is deprecated; use `device=` instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return resolved
    if device is None:
        return _device_from_spec("auto", resolved_probe)
    if isinstance(device, torch.device):
        return device if device.type == "cpu" else _device_from_spec(str(device), resolved_probe)
    return _device_from_spec(device, resolved_probe)


def resolve_dtype(device: torch.device, dtype: str | torch.dtype | None = "auto") -> torch.dtype:
    """Resolve an inference dtype supported by the selected accelerator."""

    if isinstance(dtype, torch.dtype):
        if dtype not in {torch.float16, torch.float32, torch.bfloat16}:
            raise ValueError(f"Unsupported dtype {dtype!r}. Use float32, float16, or bfloat16.")
        return dtype
    key = "auto" if dtype is None else dtype.strip().casefold()
    if key == "auto":
        if device.type == "cuda":
            return torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
        if device.type == "mps":
            return torch.float16
        return torch.float32
    aliases = {
        "float32": torch.float32,
        "fp32": torch.float32,
        "float16": torch.float16,
        "fp16": torch.float16,
        "half": torch.float16,
        "bfloat16": torch.bfloat16,
        "bf16": torch.bfloat16,
    }
    try:
        return aliases[key]
    except KeyError as exc:
        raise ValueError(
            f"Unknown dtype {dtype!r}. Supported: auto, float32/fp32, float16/fp16, bfloat16/bf16."
        ) from exc


__all__ = ["DeviceProbe", "resolve_device", "resolve_dtype", "torch"]
