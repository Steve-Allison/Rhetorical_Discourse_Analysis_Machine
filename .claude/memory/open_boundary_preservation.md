---
name: open-boundary-preservation
description: RESOLVED 2026-05-15. Boundaries are now annotation, not structural. The parser sees one big input; each relation gets boundary_memberships metadata so consumers can filter cross-boundary relations if they want.
metadata:
  type: project
---

> **Historical note — current status reconciled 2026-09-06.** The observations,
> proposed APIs and open questions below describe the dated work recorded here.
> They are not current installation or implementation instructions. The current
> source boundary is `rdam.ingest`; format-specific `parse_docling`/`parse_doclang`
> APIs and envelopes have been removed. See the [current ingest guide](../../docs/production-source-ingest.md)
> and [documentation guide](../../docs/README.md). Original decisions and measurements
> remain below for traceability; eRST work is suspended.

**Status: RESOLVED 2026-05-15** (same day as the question was raised).

The earlier framing held that boundary-handling was a structural problem: either insert boundary markers into harvested text, or parse-per-boundary, or accept cross-boundary noise. The resolution is none of these — see [decision-one-tree-per-document](decision_one_tree_per_document.md):

- The Docling document is harvested into one cue-aware text input.
- The RST parser sees the whole document and produces one tree.
- Boundary metadata (slide / page / section / turn / table) is detected separately from the Docling structure.
- Each relation gets a `boundary_memberships` annotation listing which boundaries its `self_refs` touch.
- Consumers can group / filter by `boundary_memberships` if they want; default output preserves everything.

**Why the original framing was wrong:** "cross-boundary RST relations are noise" was an assumption I had not verified. Cross-slide narrative arcs, cross-turn elaboration in conversations, section-to-section discourse — these are real RST phenomena. The parser was trained on document-scale prose; the output is honest, and consumers should be the ones to decide what counts as noise for their use case.

**How to apply:** if a future change tempts you back toward parse-per-boundary, re-read [decision-one-tree-per-document](decision_one_tree_per_document.md) before committing.

Related: [decision-one-tree-per-document](decision_one_tree_per_document.md), [open-parse-per-boundary](open_parse_per_boundary.md) (also resolved).
