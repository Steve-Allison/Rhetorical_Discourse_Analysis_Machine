---
name: open-parse-per-boundary
description: RESOLVED 2026-05-15 (rejected). Parse-per-boundary architecture was drafted on the same day and replaced before any commit by one-tree-per-document. Kept as historical record.
metadata:
  type: project
---

**Status: RESOLVED — REJECTED 2026-05-15** (same day as proposed).

Parse-per-boundary was drafted as the answer to [[open-boundary-preservation]]: one RST tree per slide / page / section / speaker turn, aggregated to a flat relations list with `boundary_id` annotations.

**Why rejected:** the natural output of `isanlp_rst.Parser(...)` is one `DiscourseUnit` tree per input. Forcing N small parses and flattening loses the hierarchical structure RST is for. Cross-boundary relations (deck narrative, cross-turn elaboration, cross-section discourse) are real phenomena, not noise; the parser is honest about them, and consumers can filter via boundary metadata if they want to ignore them.

Pros that were claimed:

- No cross-boundary noise — but cross-boundary relations aren't necessarily noise.
- Smaller inputs — but the parser's sliding-window encoding handles document-scale inputs.
- Trivially parallelisable — true, but not a v1 requirement.

Cons that won:

- Non-standard RST output (flat list under per-boundary trees).
- Loses hierarchical structure.
- N parser calls vs 1.
- Discards potentially meaningful cross-boundary relations.

**Replacement:** [[decision-one-tree-per-document]] — one parser call, one tree, with boundary metadata as annotation.

**How to apply:** kept as historical record. If a future change re-proposes parse-per-boundary, re-read this and [[decision-one-tree-per-document]] before committing.

Related: [[decision-one-tree-per-document]], [[open-boundary-preservation]].
