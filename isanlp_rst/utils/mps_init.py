"""Device-aware orthogonal weight initialisation for Apple Silicon MPS.

PyTorch's MPS backend does not implement ``aten::linalg_qr.out`` (verified up
to 2.11), which ``torch.nn.init.orthogonal_`` calls under the hood. Setting
``PYTORCH_ENABLE_MPS_FALLBACK=1`` does not always cover the ``.out`` overload,
so this helper does the orthogonal computation on CPU and copies the result
back to the parameter's original device.

For CPU and CUDA tensors the helper is a thin pass-through.
"""

from __future__ import annotations

import torch


def orthogonal_(tensor: torch.Tensor, gain: float = 1.0) -> torch.Tensor:
    """Drop-in replacement for ``torch.nn.init.orthogonal_`` that is safe on
    Apple Silicon's MPS backend.

    Args:
        tensor: parameter tensor (data) to initialise in-place.
        gain: optional gain factor, forwarded to PyTorch.

    Returns:
        The initialised tensor (same object as ``tensor``).
    """
    if tensor.device.type == 'mps':
        cpu_view = tensor.detach().cpu().clone()
        torch.nn.init.orthogonal_(cpu_view, gain=gain)
        tensor.data.copy_(cpu_view.to(tensor.device))
        return tensor
    return torch.nn.init.orthogonal_(tensor, gain=gain)
