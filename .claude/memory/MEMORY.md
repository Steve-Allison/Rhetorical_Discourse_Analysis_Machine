# MEMORY.md — isanlp_rst

Index of project-local memories. One line per entry.

## Project framing

- [Project status & ownership](project_status.md) — Steve's evolution of Elena's RST parser; not a tracking fork.
- [Licensing constraints](licensing.md) — MIT source / CC BY-NC 4.0 weights; commercial use requires weight replacement.

## Verified facts (Docling work)

- [Docling-core API contract](verified_docling_core_api.md) — `iterate_items`, `load_from_json`, default content-layer filter; with file:line citations.
- [Docling JSON schema uniformity](verified_docling_schema.md) — `DoclingDocument` v1.10.0 uniform across pptx / pdf / vtt / markdown; populated-vs-empty field differences only.

## Design decisions (Docling work)

- [One tree per Docling JSON](decision_one_tree_per_document.md) — one Parser call, one DiscourseUnit tree, boundary metadata as annotation.
- [Consumer-agnostic framing](decision_consumer_agnostic.md) — work is "Docling JSON in → RST relations indexed by self_ref → out"; no single-consumer coupling.
- [Overlap rule](decision_overlap_rule.md) — any non-empty intersection → include; `note` field for ≥ 90% lopsided overlaps.
- [Anchor on docling-core, not hand-rolled walker](decision_use_docling_core.md) — `docling-core` is a hard runtime dependency.

## Resolved questions (kept as historical record)

- [Boundary preservation in harvested text](open_boundary_preservation.md) — RESOLVED: boundary metadata as annotation; not structural.
- [Parse-per-boundary alternative architecture](open_parse_per_boundary.md) — REJECTED: one-tree-per-document wins.
- [v1 policy knobs](open_v1_policy_knobs.md) — RESOLVED: every policy is a parameter on `parse_docling()` with a default.
- [`Parser` facade output shape](open_parser_facade_unverified.md) — RESOLVED: returns `{'rst': [tree]}`; tree has character-level absolute offsets; strictly binary; leaves are EDUs.

## Open design questions

- [Device API public surface](open_device_api.md) — `cuda_device=int` is the CUDA-era API; new `device="auto"` proposed for `parse_docling()` but the underlying `Parser` still uses the legacy shape.
