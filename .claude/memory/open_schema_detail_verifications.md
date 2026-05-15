---
name: open-schema-detail-verifications
description: Specific assumptions about the Docling JSON schema that need empirical verification on real fixtures before Phase 1 code. Slide notes reachability, level distribution, OCR-PDF structure, VTT voice, table cell layout, TextItem.orig vs .text.
metadata:
  type: project
---

The Docling-native plan rests on schema assumptions verified on **five sample files**. Each assumption needs broader empirical confirmation against the five-fixture set being built in Phase 0.

## Slide notes reachability — PARTIALLY RESOLVED 2026-05-15

**Original assumption (WRONG):** slide notes are at `content_layer == "furniture"`.

**Verified 2026-05-15 on `tests/fixtures/docling/pptx.docling.json`:** slide notes are at `content_layer == "notes"` (NOT `"furniture"`). Sampled `#/texts/3`: `content_layer: "notes"`, `parent: {"$ref": "#/groups/1"}`, text is recognisably speaker-notes content. 5 such items in the fixture (all 5 happen to be the same 1378-char text — possibly a Docling quirk, possibly a real per-slide duplicate).

**Still to verify:** whether `iterate_items(included_content_layers={ContentLayer.BODY, ContentLayer.NOTES})` actually yields these items via the tree walk. Requires running `docling-core` in the pixi env.

**`ContentLayer` enum (verified 2026-05-15 at `docling_core/types/doc/document.py:1281-1289`):** five members — `BODY` (`"body"`), `FURNITURE` (`"furniture"`, page headers/footers), `BACKGROUND` (`"background"`, watermarks), `INVISIBLE` (`"invisible"`, hidden text), `NOTES` (`"notes"`, author/speaker notes). `DEFAULT_CONTENT_LAYERS = {ContentLayer.BODY}` (line 1291).

## section_header `level` distribution — PARTIALLY RESOLVED 2026-05-15

**Verified on the fixture set (`jq` on `tests/fixtures/docling/*.docling.json`):**

- `pdf.docling.json`: 11 `section_header` items, all `level: 1`. No multi-level hierarchy.
- `markdown.docling.json`: 4 `section_header` items, levels `[2, 3]`. Notable: **no `level: 1` heading** in this fixture. Markdown can apparently start the section hierarchy at any level.
- `pptx.docling.json`, `vtt.docling.json`: zero section_header items.

**Implication:** boundary detection cannot assume `level: 1` is the entry point. Multi-level nesting and starting-mid-hierarchy both occur in real fixtures.

**Still open:** behaviour on a single PDF with both `level: 1` and `level: 2` headings — not yet observed in the fixture set.

## OCR-PDF structure — verified facts (2026-05-15)

**Verified at `docling_core/types/doc/document.py:5982-5985`** (docstring on `export_to_markdown(traverse_pictures=...)`, repeated at `:6086` for `export_to_text`):

> "Must be set to True for scanned/image-based PDFs processed with full-page OCR, where the layout model places all OCR text as children of a top-level PictureItem."

**Verified at `document.py:6408`:** `PictureClassificationLabel.FULL_PAGE_IMAGE` is a defined classification label (alongside others like `PIE_CHART`, `BAR_CHART`, `GEOGRAPHICAL_MAP`).

**Verified by `jq` on `tests/fixtures/docling/pdf.docling.json`:** 24 of 48 `PictureItem`s have non-empty `children`; total of 130 child refs. Sampled `pictures[42].children[0] == #/texts/613` which has `parent: #/pictures/42`, `content_layer: "body"`, `label: "text"`, `text: "1100"`, narrow `bbox`.

**NOT verified in this session:**

- Whether `iterate_items(traverse_pictures=True)` yields TextItems parented to a `FULL_PAGE_IMAGE`-classified picture the same way it yields TextItems parented to a chart-classified picture. The schema represents both via `PictureItem.children`; the walker's behaviour on each was not directly tested.
- Whether Docling's OCR pipeline emits `section_header` labels on OCR-extracted text, or whether everything becomes `label: "text"`.
- Whether the existing PDF fixture's picture-children code path is equivalent for testing purposes to what a `FULL_PAGE_IMAGE` picture would produce.

Decision on whether a separate OCR-PDF fixture is needed: not yet made; depends on the NOT-verified items above.

## VTT `source[*].voice` reliability — PARTIALLY RESOLVED 2026-05-15

**Verified on `tests/fixtures/docling/vtt.docling.json`:** 37/37 texts have `source[0].voice`; single distinct value (`"SPEAKER_00"`) — single-speaker fixture.

**Still open:** multi-speaker behaviour. Anonymous / unnamed turns. Whether `voice` can be empty / null. Need another VTT fixture with multiple distinct speakers, ideally one with at least one anonymous turn, to close fully.

## Table cell structure

**Assumption:** `TableItem.data.grid` is a 2D array of cells; cells have row/col indices accessible as `rXcY`. Synthetic self_refs `#/tables/N/grid/rXcY` are a reasonable extension.

**Why it's suspect:** I have not looked at a populated table's `data.grid`. Don't know:

- Whether cells have row/col indices in the schema or are positional in the array.
- Whether merged cells are represented (span attributes? duplicated cell refs?).
- Whether table headers vs body cells are distinguished.
- Whether captions attach to tables in a structured way (`captions: [$ref]` list).

**Verification:** in the PPTX fixture (which has 20 tables) or PDF fixture, inspect `data.grid` for at least one populated table. Document the actual schema.

## `TextItem.text` vs `TextItem.orig`

**Assumption:** the plan harvests `TextItem.text`. Verified both `.text` and `.orig` exist; not verified which is correct.

**Why it matters:** if `.orig` is the verbatim source string and `.text` is normalised (whitespace collapsed, tags stripped, etc.), the harvest mismatches the source file's byte-for-byte content. `self_ref` mappings stay correct (they're identifier-based), but consumers comparing against source bytes via `origin.binary_hash` will see drift.

**Verification:** in any fixture, pick a TextItem and compare `.orig` and `.text`. Document the difference. Decide which to harvest.

## Non-body content layers — separate knobs needed

`ContentLayer` has five members (verified in `docling_core/types/doc/document.py:1281-1289`): `BODY`, `FURNITURE`, `BACKGROUND`, `INVISIBLE`, `NOTES`. Default filter is `{BODY}`.

The four non-default layers serve different rhetorical purposes:

- `NOTES` — speaker notes, author corrections. PPTX slide notes live here (verified on `pptx.docling.json`). Often rhetorically meaningful.
- `FURNITURE` — page headers/footers. PDF page footers live here (verified on `pdf.docling.json`: 33 furniture-layer texts, predominantly footer-style content per the `page_footer` label distribution). Typically boilerplate.
- `BACKGROUND` — watermarks. Not yet observed in fixtures.
- `INVISIBLE` — hidden text. Not yet observed in fixtures.

**Design implication:** the original `include_furniture=True` single-knob proposal conflates `NOTES` (rhetorically valuable) with `FURNITURE` (boilerplate). Likely need separate knobs:

- `include_slide_notes: bool = True` → adds `ContentLayer.NOTES` to the filter
- `include_furniture: bool = False` → adds `ContentLayer.FURNITURE` to the filter
- `include_background: bool = False`, `include_invisible: bool = False` — likely never needed, but trivial to expose if asked

**Verification + decision:** to confirm before Phase 1, run `iterate_items(included_content_layers={BODY, NOTES})` on the pptx fixture and check that slide notes appear in the yielded items.

## `prov.page_no` reliability — PARTIALLY RESOLVED 2026-05-15

**Verified on the fixture set:**

- `pdf.docling.json`: 684/684 texts have `prov[0].page_no` populated.
- `pptx.docling.json`: 8/8 texts have `prov[0].page_no` populated (matches slide number).

**Not applicable:**

- `vtt.docling.json`: uses `source[0].start_time` / `end_time` instead of `prov`.
- `markdown.docling.json`: not yet inspected for `prov` coverage. Markdown has no native paging (`pages` map is empty), so `page_no` likely null or absent. To verify.

## How to apply

Phase 0 step 3 (schema-detail verification) walks each of these against the fixture set. Each gets a yes/no answer and updates the plan if a "no" is found.

Related: [[verified-docling-core-api]], [[verified-docling-schema]], [[open-rst-real-world-quality]].
