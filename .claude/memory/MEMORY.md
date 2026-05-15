# MEMORY.md — isanlp_rst

Index of project-local memories. One line per entry.

## Project framing

- [Project status & ownership](project_status.md) — Steve's evolution of Elena's RST parser; not a tracking fork.
- [Licensing constraints](licensing.md) — MIT source / CC BY-NC 4.0 weights; commercial use requires weight replacement.

## Verified facts (Docling work)

- [Docling-core API contract](verified_docling_core_api.md) — `iterate_items`, `load_from_json`, default content-layer filter; with file:line citations.
- [Docling JSON schema uniformity](verified_docling_schema.md) — `DoclingDocument` v1.10.0 uniform across pptx / pdf / vtt / markdown; populated-vs-empty field differences only.

## Design decisions (Docling work)

- [Consumer-agnostic framing](decision_consumer_agnostic.md) — work is "Docling JSON in → RST relations indexed by self_ref → out"; no CSM or any single-consumer coupling.
- [Overlap rule](decision_overlap_rule.md) — any non-empty intersection → include; `note` field for ≥ 90% lopsided overlaps.
- [Anchor on docling-core, not hand-rolled walker](decision_use_docling_core.md) — add `docling-core` as a hard dependency.

## Open design questions

- [Boundary preservation in harvested text](open_boundary_preservation.md) — page / slide / speaker-turn boundaries; biggest gap in current v1 plan.
- [Parse-per-boundary alternative architecture](open_parse_per_boundary.md) — never properly compared against concat-and-parse; worth a session.
- [`Parser` facade output shape](open_parser_facade_unverified.md) — assumed character-level offsets per CLAUDE.md; never read `parser.py` to confirm.
- [Device API public surface](open_device_api.md) — `cuda_device=int` is the CUDA-era API; MPS support is in but the public surface is misleading.
- [v1 policy knobs](open_v1_policy_knobs.md) — table cells, picture captions, harvest separator all hard-coded; should be parameters with defaults.
