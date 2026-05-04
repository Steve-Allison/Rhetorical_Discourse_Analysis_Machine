"""Tests for the device-resolution helper.

All tests run on CPU only and never load a model. They cover the
DeviceSpec contract: legacy int handling, modern string handling,
auto-selection priority, and informative errors for unavailable
accelerators.
"""

from __future__ import annotations

import pytest
import torch

from isanlp_rst.utils.device import resolve_device


class TestLegacyIntegerSpec:
    """Backward compatibility: -1 → CPU, N → cuda:N."""

    def test_minus_one_resolves_to_cpu(self) -> None:
        assert resolve_device(-1) == torch.device("cpu")

    def test_zero_resolves_to_cuda_zero(self) -> None:
        assert resolve_device(0) == torch.device("cuda:0")

    def test_positive_integer_resolves_to_named_cuda(self) -> None:
        assert resolve_device(3) == torch.device("cuda:3")

    def test_below_minus_one_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid cuda_device integer"):
            resolve_device(-2)


class TestStringSpec:
    """Modern string-based device selection."""

    def test_cpu_string_resolves(self) -> None:
        assert resolve_device("cpu") == torch.device("cpu")

    def test_cpu_string_case_insensitive(self) -> None:
        assert resolve_device("CPU") == torch.device("cpu")

    def test_unknown_string_raises_with_helpful_message(self) -> None:
        with pytest.raises(ValueError, match="Unrecognised device string"):
            resolve_device("tpu")

    @pytest.mark.skipif(torch.cuda.is_available(), reason="CUDA is available")
    def test_cuda_request_without_cuda_raises(self) -> None:
        with pytest.raises(RuntimeError, match="CUDA is not available"):
            resolve_device("cuda")

    def test_mps_request_without_mps_raises(self) -> None:
        backend = getattr(torch.backends, "mps", None)
        if backend is not None and backend.is_available():
            pytest.skip("MPS is available; skip the negative test")
        with pytest.raises(RuntimeError, match="MPS is not available"):
            resolve_device("mps")


class TestAutoSelection:
    """`auto` and `None` pick the best available device."""

    def test_auto_returns_a_torch_device(self) -> None:
        assert isinstance(resolve_device("auto"), torch.device)

    def test_none_returns_a_torch_device(self) -> None:
        assert isinstance(resolve_device(None), torch.device)

    def test_auto_priority_is_cuda_then_mps_then_cpu(self) -> None:
        device = resolve_device("auto")
        if torch.cuda.is_available():
            assert device.type == "cuda"
        elif (
            getattr(torch.backends, "mps", None) is not None
            and torch.backends.mps.is_available()
        ):
            assert device.type == "mps"
        else:
            assert device.type == "cpu"


class TestPassThroughOfTorchDevice:
    """`torch.device` instances are returned unchanged."""

    def test_torch_device_pass_through(self) -> None:
        d = torch.device("cpu")
        assert resolve_device(d) is d


class TestInvalidTypes:
    def test_float_raises_typeerror(self) -> None:
        with pytest.raises(TypeError, match="Unsupported device spec"):
            resolve_device(1.0)  # type: ignore[arg-type]

    def test_list_raises_typeerror(self) -> None:
        with pytest.raises(TypeError, match="Unsupported device spec"):
            resolve_device(["cpu"])  # type: ignore[arg-type]
