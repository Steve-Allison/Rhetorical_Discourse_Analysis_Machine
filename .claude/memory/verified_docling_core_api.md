---
name: verified-docling-core-api
description: docling-core's DoclingDocument provides load_from_json and iterate_items (canonical pre-order DFS walker). Default content-layer filter is BODY. Verified against main branch on 2026-05-15.
metadata:
  type: reference
---

Investigated 2026-05-15 against `docling-project/docling-core` `main`. Findings used by the Docling-native RST plan.

**Loader:** `DoclingDocument.load_from_json(filename: str | Path) -> DoclingDocument` at `docling_core/types/doc/document.py:5778`. Pydantic-validated.

**Walker:** `DoclingDocument.iterate_items(root=None, with_groups=False, traverse_pictures=False, page_no=None, included_content_layers=None) -> Iterable[tuple[NodeItem, int]]` at `document.py:5535`. Pre-order DFS through `body.children`; resolves `$ref` via `child_ref.resolve(self)`. Yields `(NodeItem, depth)` tuples.

**Default content-layer filter:** `DEFAULT_CONTENT_LAYERS = {ContentLayer.BODY}` at `document.py:1291`. To include other layers, pass `included_content_layers={...}` explicitly.

**`ContentLayer` enum (verified at `document.py:1281-1289`):**

- `BODY = "body"` — main content
- `FURNITURE = "furniture"` — page headers / footers
- `BACKGROUND = "background"` — watermarks
- `INVISIBLE = "invisible"` — hidden / invisible text
- `NOTES = "notes"` — author / speaker notes, corrections

Slide notes in real PPTX output are in the `NOTES` layer (verified on `tests/fixtures/docling/pptx.docling.json`), **not** `FURNITURE` as an earlier draft assumed.

**`export_to_text(...)` exists** at `document.py:6049` but does NOT track per-item character positions — only emits the concatenated string. So we still need our own iteration + position tracking for the harvester.

**`.texts[]` is the storage, NOT the canonical reading order.** The array order in `.texts[]` does not correspond to document reading order. The body-rooted tree walk via `body.children` is canonical.

**$ref resolution:** every `$ref`-shaped child has a`.resolve(doc)` method that returns the actual `NodeItem`. The walker uses this internally; consumers shouldn't need to call it.

**How to apply:**

- Verify before relying on this in code: the API may have changed since 2026-05-15. Re-check `iterate_items` on the currently-locked `docling-core` version. If they refactor, this memory needs updating. *(2026-06-27: docling-core is now 2.85.0 — unpinned, tracking latest — and the 113 docling tests pass, so `iterate_items` remains compatible with our usage; full signature not re-diffed.)*
- Don't roll our own walker. Anchor on `iterate_items()`.
- The default `with_groups=False` + `traverse_pictures=False` is correct for v1 of the Docling-native entry point — we want leaf-ish text-carrying items, not group markers, and we explicitly skip picture-caption recursion in v1.

Related: [[verified-docling-schema]], [[decision-use-docling-core]].
