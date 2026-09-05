# Docling JSON fixtures

Real-world Docling JSON files used to test the Docling JSON source form through
the shared public production ingest API, `rdam.ingest`. Docling deserialization
is a private implementation detail. The file-by-file observations below record
the fixture inspection performed on 2026-05-15; they are not universal Docling
schema guarantees. Source filenames are recorded under Provenance; public
availability and redistribution permission have not been independently verified
in the 2026-09-04 preflight.

## Current loading check — 2026-09-04

All four fixtures loaded with Docling Core 2.94.1 using
`DoclingDocument.load_from_json`. Each stores schema 1.10.0 and loaded as 1.10.0.
Traversal with `with_groups=True`, `traverse_pictures=True` and all `ContentLayer`
values yielded 63 items for Markdown, 767 for PDF, 43 for PPTX and 38 for VTT.
These are fixture-specific observations. Full preflight scope and test results
are recorded in [Feature 019 research](../../../specs/019-unified-machine-interfaces/research.md).

## Historical file-by-file observations — 2026-05-15

### `pptx.docling.json` — 333 KB

- `origin.mimetype`: `application/vnd.ms-powerpoint`
- `version`: `1.10.0`
- `pages` map keys: `["1", ..., "9"]` (9 slides)
- `texts`: 8 total, distributed `content_layer`: 3 body, 5 notes
- `pictures`: 5
- `tables`: 20
- `groups`: 9 (one per slide; sampled `groups[0].name == "slide-0"`, `groups[0].label == "chapter"` per earlier survey)
- **Sampled `content_layer: "notes"` item** (`#/texts/3`): `label: "text"`, `parent: #/groups/1`, `prov[0].page_no: 2`, text content reads as a speaker-notes block (multi-week project planning text with `@mentions`). Confirms these are slide notes.
- **All 5 `notes`-layer texts have identical 1378-char content.** Either a Docling artefact (notes duplicated across slides) or a real case where the same note block applies to multiple slides. Behaviour observed; explanation `ASSUMED — to verify` if it matters for testing.

### `pdf.docling.json` — 965 KB

- `origin.mimetype`: `application/pdf`
- `version`: `1.10.0`
- `pages` map: 19 pages
- `texts`: 684 total
  - `content_layer` distribution: 651 body, 33 furniture
  - `label` distribution: 556 `text`, 84 `list_item`, 33 `page_footer`, 11 `section_header`
- `pictures`: 48 total; **24 of them have non-empty `children` lists** (total 130 child-refs)
- `tables`: 1
- **Picture classification (top predicted class per `annotations[].predicted_classes[0]`):** 40× `screenshot_from_computer`, 3× `photograph`, 1× each of `bar_chart`, `full_page_image`, `icon`, `logo`, `table`. **One picture is classified `full_page_image`** (the docling-core term for an OCR-derived full-page rendering).
- **Sampled `pictures[42]` (top class `screenshot_from_computer`, confidence 0.99) `.children[0]` (`#/texts/613`):** `parent: #/pictures/42`, `content_layer: "body"`, `label: "text"`, `text: "1100"`, narrow `bbox`. The text is parented to the picture and reachable only with `traverse_pictures=True`. Whether it was extracted by OCR or by vector-text-overlay is not knowable from the schema alone — the classification of the parent picture is the only signal.

### `vtt.docling.json` — 26 KB

- `origin.mimetype`: `text/vtt`
- `version`: `1.10.0`
- `pages` map: empty (VTT has no native page concept)
- `texts`: 37 total, all `content_layer: "body"`, all `label: "text"`
- `pictures`: 0; `tables`: 0; `groups`: 0
- **All 37 texts have `source[0].voice == "SPEAKER_00"`** — verified by `jq '[.texts[] | .source[0].voice] | unique' → ["SPEAKER_00"]`. **Single-speaker transcript.**
- Each `TextItem` also carries `source[0].start_time` / `source[0].end_time` (sampled on `texts[0]`; **not** exhaustively verified across all 37 — `ASSUMED — to verify if this matters for testing`).

### `markdown.docling.json` — 24 KB

- `origin.mimetype`: `text/markdown`
- `version`: `1.10.0`
- `pages` map: empty `{}`
- `texts`: 51 total
  - `label` distribution: 4 `section_header`, 4 `list_item`, 43 `text`
- `pictures`: 3
- `tables`: 0

## Cross-fixture claims (sample-scoped, not universal)

- All four files emit `DoclingDocument` v1.10.0. Sample-scope: 4 files. NOT a claim about Docling JSONs in general.
- All four files have the same top-level keys: `body`, `form_items`, `furniture`, `groups`, `key_value_items`, `name`, `origin`, `pages`, `pictures`, `schema_name`, `tables`, `texts`, `version`. Sample-scope: 4 files.

## What's NOT covered

These cases are **not** present in the current fixture set; flagged for future addition:

- **A PDF dominated by `full_page_image`-classified pictures** (typical of scanned-PDF OCR output). The current PDF fixture has 1 such picture among 48; a "true OCR PDF" fixture would have most or all pictures so classified.
- **A document with no `section_header`.** The PDF fixture has 11; Markdown has 4. PPTX and VTT have zero — but they exercise different boundary detection (slide groups, speaker turns), so the "default `document` boundary fallback" for prose-formats remains uncovered.
- **A single-text-item document** (parser edge case).
- **A document with empty `body.children`** (parser edge case).
- **A multi-speaker VTT.** The current VTT fixture has one speaker (`SPEAKER_00`); speaker-coalescing logic has no fixture to exercise.
- **A PDF with multi-level section headers.** The current PDF has 11× `level: 1` only. Markdown fixture has `level: 2` and `level: 3` (no `level: 1`) — multi-level hierarchy in one document not yet fixtured.

## Provenance

- Copied verbatim 2026-05-15 from a working corpus. Source filenames:
  - `pptx.docling.json` ← `creation_mvp_requirements.docling.json`
  - `pdf.docling.json` ← `02_accelerate_workbook_usingacrobatstudioandexpress_v3.docling.json`
  - `vtt.docling.json` ← `acrobat_studio_sales_press_v1_2.docling.json`
  - `markdown.docling.json` ← `generate_presentations.docling.json`
- No transformation applied.

## How facts were verified

All numerical / structural claims above were verified with `jq` queries against the actual fixture files on 2026-05-15. Where a claim cannot be re-verified by inspection (e.g. "exhaustively true for all N items"), it is marked `ASSUMED — to verify`.
