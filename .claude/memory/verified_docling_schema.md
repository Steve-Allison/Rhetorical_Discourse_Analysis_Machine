---
name: verified-docling-schema
description: Sample-scoped findings (4 files in tests/fixtures/docling/ + 1 additional sample) about DoclingDocument v1.10.0 shape. Inferences beyond the sample are NOT claimed.
metadata:
  type: reference
---

Findings from inspecting 5 Docling JSON files on 2026-05-15: the four files in [`tests/fixtures/docling/`](../../tests/fixtures/docling/) plus one additional sample from the same corpus. **Sample size: 5. Scope of any claim below is the sample, unless explicitly noted otherwise.**

## Per-fixture observations

See [`tests/fixtures/docling/README.md`](../../tests/fixtures/docling/README.md) for the verified file-by-file facts. That README is the source of truth for what each fixture contains; this memory captures cross-fixture observations.

## Cross-fixture observations (sample-scope: 5 files)

- All 5 files emit `schema_name: "DoclingDocument"`, `version: "1.10.0"`.
- All 5 files share the same top-level keys: `body`, `form_items`, `furniture`, `groups`, `key_value_items`, `name`, `origin`, `pages`, `pictures`, `schema_name`, `tables`, `texts`, `version`.
- `body.children` is a list of `$ref` references, not inline objects. Resolving these `$ref`s is required to walk the document in canonical reading order.
- `origin.binary_hash` is present as an integer on every file in the sample.

## Per-source-format observations (each from N=1 file in the sample)

These are observations from **single fixtures**, not validated across multiple files per format. Treat as preliminary, not as schema-wide guarantees:

| Source format | What this single fixture shows |
|---|---|
| PPTX (`pptx.docling.json`) | `body.children` contains `groups[i]` refs (one per slide); group `name` matches `^slide-N$`, `label` is `"chapter"`. Slide notes live at `content_layer: "notes"` parented to the slide group (i.e. **reachable via tree walk** from `body.children` if `included_content_layers` includes `notes` — not just orphans in `.texts[]`). Page footers / masters not observed because slide content_layer is `body`/`notes` only here. |
| PDF (`pdf.docling.json`) | `body.children` contains direct text/picture/group refs. Some pictures have `children` lists of text refs — verified the children are figure-internal text labels (e.g. chart axis values), NOT OCR-extracted scanned-page text. PDFs of OCR origin would presumably differ; not yet inspected. |
| VTT (`vtt.docling.json`) | Flat: `body.children` is all direct text refs. Each text in this single fixture has `source[0].voice == "SPEAKER_00"` — single-speaker. Multi-speaker VTT shape not yet inspected. |
| Markdown (`markdown.docling.json`) | `pages` map is empty `{}` (no native page concept). `body.children` shape and section_header behaviour for markdown not yet fully traced. |

## What this memory does NOT claim

- Schema uniformity across ALL Docling JSONs in the wild. The sample is 5 files, all from one working corpus.
- That OCR-PDF processing produces a particular shape. No OCR-PDF fixture exists.
- That `.furniture.children` is empty across all Docling outputs. ASSUMED for PDF and PPTX based on the unique-value check; not directly opened for verification across all 5.
- That every VTT TextItem in every transcript carries `source[0].voice`. ASSUMED universally; verified for 37/37 in the one VTT fixture.
- That every PPTX file uses `groups[name=slide-N, label=chapter]`. ASSUMED from one PPTX sample.

## How to apply

- Phase 0 step 3 (schema-detail verification) closes the gaps named above and in [[open-schema-detail-verifications]].
- Use the per-fixture README (`tests/fixtures/docling/README.md`) as the citable evidence base — don't restate from this memory; cite the README instead.
- New Docling files added to the fixture set must have their facts verified and committed to the README, not just inferred from this memory.

Related: [[verified-docling-core-api]], [[open-schema-detail-verifications]], [[open-rst-real-world-quality]].
