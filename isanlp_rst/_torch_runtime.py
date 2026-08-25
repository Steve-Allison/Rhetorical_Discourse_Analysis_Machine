"""Import PyTorch after configuring the Apple-Silicon fallback boundary."""

import os
from importlib import import_module
from typing import TYPE_CHECKING

os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")

if TYPE_CHECKING:
    import torch
else:
    torch = import_module("torch")

__all__ = ["torch"]
