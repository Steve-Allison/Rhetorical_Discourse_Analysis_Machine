---
name: verified-docling-schema
description: DoclingDocument v1.10.0 shape is uniform across pptx, pdf, vtt, html-markdown source formats. Differences are which fields are populated, not which fields exist. Verified 2026-05-15.
metadata:
  type: reference
---

Investigated 2026-05-15 against a real-world Docling JSON corpus (five files across four source formats).

**All five files emit `DoclingDocument` v1.10.0** with identical top-level shape: `body`, `furniture`, `groups`, `texts`, `pictures`, `tables`, `pages`, `origin`, `form_items`, `key_value_items`, `name`, `schema_name`, `version`.

**Source-format-specific differences are populated-vs-empty, not structural:**

| Aspect | PPTX | PDF | VTT | HTML / Markdown |
|---|---|---|---|---|
| `body.children` | → `groups` (one per slide), then texts/pictures/tables | mostly direct text / picture / group `$ref`s | flat list of text `$ref`s | similar to PDF, simpler |
| `groups` | slide containers (`name: "slide-N"`, `label: "chapter"`) | semantic groupers (`name: "list"`) | none | semantic groupers |
| Page info | `pages` map + `prov.page_no` on texts | `pages` map + `prov.page_no` on texts | none — text items have `source.start_time` / `source.end_time` instead | `pages` map empty if source has no native paging |
| Text labels | `title`, `text`, ... | `section_header`, `list_item`, `text`, `page_footer`; `level` on headers | only `text`; each carries `voice` (speaker) | similar to PDF |
| Provenance | `prov` with bbox | `prov` with bbox + `level` hierarchy | `source` with VTT timing, no `prov` | similar to PDF, `prov` may be sparse |

**Furniture handling:** `.furniture.children` is empty across all files, but text items can carry `content_layer: "furniture"`. They're only reachable via the flat `.texts[]` array, not via `body.children`. The default `iterate_items()` filter (`{ContentLayer.BODY}`) excludes them automatically.

**`origin.binary_hash`** is present in every file as an integer. Consumers needing a source-cache anchor read it from there; we don't compute it.

**How to apply:**

- One walker handles all source formats. No source-format special-casing in our harvester code.
- Phase 1 fixture set should include one example per source flavour (pptx / pdf / vtt / markdown) to catch any edge cases the five-file sample missed.
- Forms (`form_items`) and key-value pairs (`key_value_items`) appear as top-level fields but were not exercised in the sample — flag these if a future Docling source populates them.
- OCR'd PDFs (where all text is wrapped in pictures and needs `traverse_pictures=True`) are also untested; document this in the harvester as a known v1 gap.

Related: [[verified-docling-core-api]], [[open-boundary-preservation]].
