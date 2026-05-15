---
name: open-v1-policy-knobs
description: The Docling-native parse_docling() v1 policy decisions (skip table cells, skip picture captions, default separator) are baked into the harvester. They should be exposed as parameters with safe defaults — cheap to do, removes "wait for v2" friction.
metadata:
  type: project
---

The Docling-native build plan locks several v1 policy decisions into code rather than exposing them as parameters:

- **Skip `TableItem` cell text.** Tables yield only their `self_ref`; no cell-text harvesting.
- **Skip `PictureItem.captions`.** `traverse_pictures=False` (the `iterate_items` default).
- **Harvest separator** between concatenated spans (`\n\n` is the current lean).
- **Content-layer filter** = `{ContentLayer.BODY}` (excludes furniture).
- **Overlap rule** 90% threshold for the `note` field.

**Problem:** the first consumer who wants caption-aware RST, or wants to include furniture, or wants `<P>` separators between paragraphs, has to wait for v2. That's friction that costs us early adopters.

**Fix:** make `parse_docling()` accept these as parameters, with the current v1 defaults baked in. Costs ~5 lines of code; immediately enables more consumers.

```python
def parse_docling(
    path: Path,
    *,
    hf_model_name: str = "tchewik/isanlp_rst_v3",
    hf_model_version: str = "gumrrg",
    cuda_device: int = -1,
    include_table_cells: bool = False,
    include_picture_captions: bool = False,
    include_furniture: bool = False,
    harvest_separator: str = "\n\n",
    note_threshold: float = 0.90,
) -> DoclingRstResult:
    ...
```

**How to apply:**

- Bake this into the Phase 3 orchestrator design. Don't ship a no-knobs API.
- Defaults match v1 policy; non-default values opt the caller into more inclusive harvests at the cost of larger inputs and possibly worse RST quality (well-known limit on noise tolerance).
- Document each knob's trade-off in the docstring.

Related: [[open-device-api]] (similar "expose proper knobs" theme).
