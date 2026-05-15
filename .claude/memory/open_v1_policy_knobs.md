---
name: open-v1-policy-knobs
description: RESOLVED 2026-05-15. The single-release scope decision means every policy is a parameter on parse_docling() with a default. No deferred-to-v2.
metadata:
  type: project
---

**Status: RESOLVED 2026-05-15** by the "do the full thing first time" directive and the architecture revision.

The proposal's `parse_docling()` signature now exposes:

- `include_picture_captions: bool = True` — non-OCR caption text harvested by default.
- `include_slide_notes: bool = True` — `ContentLayer.NOTES` items harvested by default (PPTX speaker notes — rhetorically meaningful).
- `include_furniture: bool = False` — `ContentLayer.FURNITURE` (page headers / footers, typically boilerplate) off by default.
- `harvest_separator: str = "\n\n"` — caller can override.
- `coalesce_speaker_turns: bool = True` — VTT same-voice runs coalesce into one boundary by default.
- `note_threshold: float = 0.90` — overlap-rule lopsided threshold.
- `device: str = "auto"` — replaces the legacy `cuda_device: int`.

Two policies are NOT parameters by design:

- **Table cell text is not in the RST harvest input.** RST over flattened table cells produces nonsense; the cost of making this a parameter is one more boolean that almost no one will flip and that produces bad output when they do. `TableItem` `self_refs` still appear as `boundaries[]` entries so consumers know they're there.
- **`traverse_pictures=True` is always passed to `iterate_items()`** because it's required for OCR-PDF support. The `include_picture_captions` knob does the actual filtering downstream of iteration.

**How to apply:** when adding new policy decisions for the entry point, default to "expose as parameter with safe default" unless there's a structural reason not to (e.g. tables-as-grids).

Related: [[decision-one-tree-per-document]], [[open-device-api]] (the `device` parameter shape).
