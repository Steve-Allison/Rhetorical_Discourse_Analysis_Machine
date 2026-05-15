---
name: open-device-api
description: The public Parser API takes `cuda_device: int` even though MPS is now first-class. The naming is misleading and the integer is unused on MPS. Worth a public-API revision before next minor release.
metadata:
  type: project
---

`Parser(..., cuda_device=N)` is the device knob. It now auto-selects:

- NVIDIA CUDA host → `cuda:N`
- Apple Silicon (no CUDA) → `mps` (the integer is ignored; MPS exposes a single device)
- No GPU available → `RuntimeError` (use `cuda_device=-1` for CPU)

**Problem:** the parameter is named `cuda_device` but on Apple Silicon it's actually selecting MPS — the name is a lie, and the integer is meaningless. Users reading the docstring get a confusing picture.

**Options:**

- **Add `device=` as the preferred name**, keep `cuda_device=` as a deprecated alias. `device="auto"` is the default; explicit `"cpu"` / `"cuda:0"` / `"mps"` strings are accepted.
- **Or:** introduce a richer `device` object that wraps backend + index, and have `cuda_device=` continue working for backwards compatibility.

**How to apply:**

- This is a public API change. Cluster it with other public-API revisions for the next minor release (3.3.0?), not as a one-off.
- The Docling-native `parse_docling()` entry point should accept the *new* device API from day one, not inherit the legacy `cuda_device=` from `Parser`.
- README has a sub-section explaining the auto-selection behaviour — it acknowledges the awkwardness ("the integer is ignored; MPS exposes a single device") but doesn't fix it.

Related: [[open-v1-policy-knobs]] (similar "expose proper knobs" theme).
