# Docling JSON fixtures

Real-world Docling JSON files used for testing `isanlp_rst.docling.parse_docling()` (when that entry point exists). All four files are publicly-available content. All claims below verified via `jq` on the actual fixtures on 2026-05-15.

## File-by-file verified facts

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
- `pictures`: 48 total; **24 of them have non-empty `children` lists** (total 130 child-refs across the 48 pictures)
- `tables`: 1
- **Sampled `pictures[42].children[0]` (`#/texts/613`)**: `parent: #/pictures/42`, `content_layer: "body"`, `label: "text"`, `text: "1100"`, very thin `bbox`. This is **figure-internal text** (e.g. a chart label or data value), **NOT OCR-extracted scanned-page text.** The PDF is a regular text-PDF with figure embeds, not an OCR PDF.

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

- **A true OCR-PDF.** None of the four fixtures is OCR-derived. The PDF has figure-internal text labels reachable via `traverse_pictures=True`, but those are vector-rendered numbers in charts, not OCR of scanned pages. To exercise OCR-PDF code paths, a fresh fixture is needed (run Docling on a scanned-PDF input).
- **A document with no `section_header`.** All three relevant fixtures (PDF, Markdown, plus PPTX in a sense) have at least one. The "default `document` boundary fallback" code path has no fixture.
- **A single-text-item document** (parser edge case).
- **A document with empty `body.children`** (parser edge case).
- **A multi-speaker VTT.** The current VTT fixture has one speaker; speaker-coalescing logic has no fixture to exercise.
- **A document with `level: 2`+ section_headers.** Not verified whether the current PDF has multi-level section headers — flagged for Phase 0 schema-detail verification.

## Provenance

- Copied verbatim 2026-05-15 from a working corpus. Source filenames:
  - `pptx.docling.json` ← `creation_mvp_requirements.docling.json`
  - `pdf.docling.json` ← `02_accelerate_workbook_usingacrobatstudioandexpress_v3.docling.json`
  - `vtt.docling.json` ← `acrobat_studio_sales_press_v1_2.docling.json`
  - `markdown.docling.json` ← `generate_presentations.docling.json`
- No transformation applied.

## How facts were verified

All numerical / structural claims above were verified with `jq` queries against the actual fixture files on 2026-05-15. Where a claim cannot be re-verified by inspection (e.g. "exhaustively true for all N items"), it is marked `ASSUMED — to verify`.
