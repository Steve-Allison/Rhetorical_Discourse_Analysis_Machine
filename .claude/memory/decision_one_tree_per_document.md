---
name: decision-one-tree-per-document
description: parse_docling() emits one RST tree per Docling JSON — the natural Parser output — with boundary metadata layered on top as annotations. Not parse-per-boundary; not parse-and-synthesise.
metadata:
  type: feedback
---

The Docling-native RST entry point produces **one `DiscourseUnit` tree per input Docling JSON**, serialised as a flat `relations[]` + `edus[]` with `left_id` / `right_id` so consumers can reconstruct the hierarchy. Boundary metadata (slide / page / section / turn / table) is layered on top as `boundary_memberships` annotations on each relation; it doesn't affect which RST relations are emitted.

**Why:** the natural output of `isanlp_rst.Parser(...)` is one `DiscourseUnit` tree per input. Forcing the input into per-boundary chunks and emitting a flat relations list under per-boundary trees is non-standard, loses hierarchical structure, and discards cross-boundary relations that may be meaningful (deck narrative arc, cross-turn elaboration in a conversation, section-to-section discourse).

Two architectures considered and rejected:

- **Parse-per-boundary, flat relations** (drafted 2026-05-15 r4, rejected same day): N small RST trees, flattened to a relations list with `boundary_id`. Eliminates cross-boundary relations by construction but loses the hierarchical structure RST is for.
- **Parse-per-boundary, synthesised root**: per-boundary trees combined under a fake document-root. Synthetic root relation (`Joint`? `Sequence`?) is dishonest.

**How to apply:**

- Harvest the full Docling document into one text input (cue-aware: section headers, slide notes, picture captions, OCR-PDF wrapped text). Tables are excluded from RST input but their `self_ref`s appear as `boundaries[]` entries.
- Run `Parser(...)` once.
- Map each tree node's `start`/`end` to `self_refs` via the overlap rule.
- Compute `boundary_memberships` for each relation by intersecting its refs with each boundary's `self_refs`.
- Flatten the tree to `relations[]` (internal nodes) + `edus[]` (leaves), preserving hierarchy via `left_id` / `right_id`.

Empirical question to close in Phase 0: does the parser handle long, structurally-diverse single inputs gracefully? Sliding-window encoding (`tokenizer.model_max_length = 1e9`) is the upstream mitigation. If long-input quality degrades materially, revisit — but the answer is probably "the parser is fine on document-scale inputs; we just need to verify".

Related: [[decision-consumer-agnostic]], [[decision-use-docling-core]], [[decision-overlap-rule]], [[open-parser-facade-unverified]].
