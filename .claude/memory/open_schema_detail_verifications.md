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

## section_header `level` distribution

**Assumption:** PDF / Markdown / HTML use `section_header` with a `level` attribute for hierarchy.

**Unverified:** range and distribution of `level` values in real Docling output. Have I seen `level: 2` or deeper? PDFs where every heading is `level: 1`?

**Verification:** in the PDF fixture (after building it), enumerate `level` values across all section_header items. Confirm range.

## OCR-PDF structure

**Assumption:** OCR PDFs wrap all text in top-level `PictureItem`s; `traverse_pictures=True` exposes that wrapped text; section detection works the same way.

**Why it's suspect:** I haven't actually inspected an OCR-PDF Docling JSON. The wrapped text may not carry `section_header` labels at all — Docling's OCR layer may emit everything as `label: "text"`. If section_header labelling doesn't survive OCR, boundary detection falls back to single `document` boundary for OCR PDFs.

**Verification:** find an OCR-PDF in the CSM corpus (or run Docling on one); inspect the structure. Does it have `section_header` items, or is everything `label: "text"`?

## VTT `source[*].voice` reliability

**Assumption:** every VTT `TextItem` has `source[*].voice` identifying the speaker.

**Unverified:** does every VTT TextItem actually have a `voice`? Can it be empty, `null`, or `"SPEAKER_UNKNOWN"`? What about anonymous transcripts?

**Verification:** in the VTT fixture, enumerate `voice` values across all items. Check for empty / null / missing.

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

## `furniture` sub-types

**Assumption:** `include_furniture=True` is a single binary knob that turns on slide notes (PPTX) and page footers/headers (PDF) simultaneously.

**Why it's suspect:** consumers may want slide notes (rhetorically meaningful) without page footers (typically boilerplate). A single binary knob conflates them.

**Verification + decision:** check what content lives at `content_layer == "furniture"` for each source format. If slide-notes vs page-furniture are distinguishable by `parent` type or by content patterns, consider exposing as two knobs (`include_slide_notes`, `include_page_furniture`).

## `prov.page_no` reliability

**Assumption:** PDF text items carry `prov[].page_no` reliably. PPTX text items carry `prov[].page_no` for slide number.

**Verification:** in PDF and PPTX fixtures, confirm `prov[].page_no` is populated for every relevant TextItem. Spot-check VTT items (which use `source` not `prov`).

## How to apply

Phase 0 step 3 (schema-detail verification) walks each of these against the fixture set. Each gets a yes/no answer and updates the plan if a "no" is found.

Related: [[verified-docling-core-api]], [[verified-docling-schema]], [[open-rst-real-world-quality]].
