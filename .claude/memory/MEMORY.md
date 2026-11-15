# MEMORY.md — RDAM project notes

Index of project-local notes. The format-design and upstream investigations are
historical snapshots, not current API instructions. See [current documentation](../../docs/README.md)
and [production ingest](../../docs/production-source-ingest.md). The package is
`rdam`, the command is `rdam`, and eRST work is suspended as of 2026-09-06.

## Project framing

- [Licensing constraints](licensing.md) — MIT source / CC BY-NC 4.0 weights; commercial use requires weight replacement.

## Dated observations (historical Docling work — retired from `rdam.ingest` in `6.1.0`)

- [Docling-core API contract](verified_docling_core_api.md) — historical `iterate_items`, `load_from_json`, default content-layer filter (`_inventory_docling` retired in `6.1.0` in favour of unified `dclq` + DocLang ingestion).
- [Docling JSON schema uniformity](verified_docling_schema.md) — historical `DoclingDocument` v1.10.0 sample notes across pptx / pdf / vtt / markdown.

## Dated observations (`dclq` and DocLang work)

- [DocLang spec](verified_doclang_spec.md) — XML-based; as of 2026-11-15 `pyproject.toml:44-45` ships `dclq>=2.107.0,<3` and `doclang[schematron-saxon]` at upstream `main` commit `ae8ad5490b9b03b344e3e49dcb0f6f2209795de6` (`v0.9.0`, 62 valid and 78 invalid fixtures in `tests/fixtures/doclang/`) as core dependencies. Historical body notes below the status banner record the initial 2026-05-15 v0.5 investigation.
- [DocLang fixture verifications (Phase 1)](verified_doclang_fixtures.md) — historical Q1–Q6 verified against the initial 40 valid fixtures; current 62-valid / 78-invalid conformance corpus is tracked in [`tests/fixtures/doclang/README.md`](../../tests/fixtures/doclang/README.md).

## Resolved questions (kept as historical record)

- [Boundary preservation in harvested text](open_boundary_preservation.md) — RESOLVED: boundary metadata as annotation; not structural.
- [Parse-per-boundary alternative architecture](open_parse_per_boundary.md) — REJECTED: one-tree-per-document wins.
- [`Parser` facade output shape](open_parser_facade_unverified.md) — RESOLVED: returns `{'rst': [tree]}`; tree has character-level absolute offsets; strictly binary; leaves are EDUs.
- [Device API public surface](open_device_api.md) — RESOLVED 2026-06-30: `device=` ("auto" default) is canonical on `Parser` + predictors; `cuda_device:int` is a deprecated warned shim.

## Historical open design questions

- [RST real-world quality](open_rst_real_world_quality.md) — biggest blind spot: RST was developed for prose; quality on slides / transcripts / long mixed docs is unverified. Also: which relation inventory to default to.
- [Schema-detail verifications](open_schema_detail_verifications.md) — slide-notes content_layer (RESOLVED: `"notes"`, not `"furniture"`), level distribution, OCR-PDF shape, VTT voice reliability, table cell structure, TextItem.orig vs .text, non-body content layers (FURNITURE / NOTES / BACKGROUND / INVISIBLE).
- [Boundary design decisions](open_boundary_design_decisions.md) — boundary_memberships semantics, section nesting, pages, picture-caption vs OCR-text, degenerate cases (empty boundaries, single-EDU, table-only documents).
- [Output schema specifics](open_output_schema_specifics.md) — relation / EDU / boundary ordering, id space, tool_version format, source field format, JSON serialisation specifics.
- [Long-input parser fallback](open_long_input_fallback.md) — what `parse_docling()` does if the existing `Parser` fails or degrades on 50K+-char harvests. Verified empirically in Phase 0 step 6.
