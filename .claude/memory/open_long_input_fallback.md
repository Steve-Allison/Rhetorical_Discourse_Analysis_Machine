---
name: open-long-input-fallback
description: What `parse_docling()` does if the existing `Parser` fails or degrades on a long harvested input (50K+ chars). No fallback designed; verified empirically in Phase 0 step 6.
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

The one-tree-per-document architecture feeds the entire cue-aware harvest into a single `Parser` call. Realistic Docling-document harvests can be large:

- Multi-page PDFs: ~50–500 KB of harvested text.
- Long PowerPoint decks (50+ slides with notes): ~100 KB.
- Long VTT transcripts (60+ minutes): ~50–200 KB.

The CLAUDE.md notes `tokenizer.model_max_length = 1e9` (sliding-window encoding intentional) but the underlying XLM-RoBERTa-large model has an effective context window (~512 subword tokens per window).

**Unverified failure modes:**

- **OOM** on the GPU / CPU during forward pass for very long inputs.
- **Tree-quality degradation** as sliding windows lose long-range context.
- **Razdel tokenisation slowdown** on huge inputs (linear, but might dominate).
- **Memory pressure** as `DiscourseUnit.text` carries the full substring per node.

**Phase 0 step 6 long-input smoke test:** load the largest fixture, harvest it, run the existing `Parser`. Outcomes:

| Outcome | Response |
|---|---|
| Parser succeeds, tree looks coherent | Architecture validated. Document the largest tested input size as the practical limit. |
| Parser succeeds but tree quality is visibly bad on long inputs | Document the limit; consumers warned in API docs. Don't change architecture for this. |
| Parser raises OOM / context-overflow | Need a fallback strategy. See options below. |
| Parser hangs / runs absurdly slowly | Need a fallback strategy. |

**Fallback options if the parser fails at scale:**

1. **Refuse long inputs.** Raise `InputTooLargeError` when harvest exceeds a documented threshold (e.g. 200K chars). Forces consumers to chunk before calling. Cheap. Visible. Honest.
2. **Per-section parse + merge.** For documents with section_header structure, run the parser per section, stitch results under synthetic relations. Compromises the one-tree-per-document principle but only for inputs where the parser would otherwise fail.
3. **Sliding-window parse with overlap aggregation.** Run the parser on overlapping windows, vote on relation membership in overlap zones. Complex; non-standard; probably not worth it.

**Recommend option 1** as the explicit failure mode. Option 2 reintroduces the parse-per-boundary we rejected; only revisit if option 1 is unacceptable for major use cases.

**How to apply:**

- Phase 0 step 6 settles which of these applies.
- If options 2 or 3 are needed, the build plan and proposal need amending — bring back to user for redesign approval.
- Until empirically verified, the plan assumes option 0: parser works fine on all realistic Docling-document inputs.

Related: [decision-one-tree-per-document](decision_one_tree_per_document.md), [open-rst-real-world-quality](open_rst_real_world_quality.md).
