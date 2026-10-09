---
name: open-device-api
description: RESOLVED 2026-06-30 — `device=` is now the canonical Parser knob ("auto" default); `cuda_device:int` kept as a deprecated warned shim. The misleading-name problem is fixed.
metadata:
  type: project
---

> **Historical note — current status reconciled 2026-09-06.** The observations,
> proposed APIs and open questions below describe the dated work recorded here.
> They are not current installation or implementation instructions. The current
> source boundary is `rdam.ingest`; format-specific `parse_docling`/`parse_doclang`
> APIs and envelopes have been removed. See the [current ingest guide](../../docs/production-source-ingest.md)
> and [documentation guide](../../docs/README.md). Original decisions and measurements
> remain below for traceability; eRST work is suspended.

**RESOLVED 2026-06-30.** Implemented option 1 below: `device=` is the canonical
knob on `Parser` and both predictors, accepting `"auto"` (default) / `"cpu"` /
`"mps"` / `"cuda"` / `"cuda:N"` / a `torch.device`, resolved by `resolve_device`
in [`isanlp_rst/base_predictor.py`](../../rdam/rst/base_predictor.py). The
resolved value is stored as `self._device` (a `torch.device`, replacing the
misnamed `self._cuda_device`). The legacy `cuda_device:int` is a deprecated shim
that emits a `DeprecationWarning` (`-1` → CPU, `>= 0` → best accelerator);
passing both `device=` and `cuda_device=` raises. The format-native entry points
pass `device=` straight to `Parser` — the old string→int
`_rst_common.resolve_device` bridge was removed (one resolver now, not two). The
inherited `ParsingNet` keeps its original `cuda_device=` kwarg name (Mode-B
research network, not renamed).

Default behaviour changed: from CPU (`cuda_device=-1`) to `device="auto"` —
fixes the foot-gun where Apple Silicon silently ran on CPU.

Verified end-to-end this session: gumrrg + unirst parse on both `device="cpu"`
and `device="mps"` (Apple Silicon); 440 fast tests + ruff + pyright green.

---

Original problem (kept for record): `Parser(..., cuda_device=N)` was named for
CUDA but on Apple Silicon selected MPS — the name was a lie and the integer was
meaningless on MPS, so the docstring gave users a confusing picture.
