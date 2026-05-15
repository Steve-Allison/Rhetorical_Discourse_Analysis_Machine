---
name: decision-overlap-rule
description: For self_ref overlap: any non-empty intersection → include in nucleus_refs / satellite_refs. When one self_ref dominates ≥ 90%, attach a free-form `note` field describing the imbalance.
metadata:
  type: feedback
---

When mapping RST relation character offsets back to Docling `self_ref`s, the rule is:

- **Inclusion:** a relation's `nucleus_refs` (resp. `satellite_refs`) contains every `self_ref` whose harvest character range has *any* non-empty intersection with the relation's nucleus (resp. satellite) span. No minimum threshold for inclusion.
- **`note` field:** when a relation's span overlaps ≥ 90% with one `self_ref` but marginally touches an adjacent one, attach a `note` field describing the imbalance, e.g.: `"nucleus dominantly in #/texts/47; spills into #/texts/48 (8% overlap)"`.
- **90% is the only knob.** Other `note` shapes are reserved for future use.

**Why:** EDU (elementary discourse unit) boundaries don't always align with Docling text-item boundaries. An EDU might straddle two or three Docling spans, and a relation might cover several EDUs. Modelling as list-of-refs is honest; a single-ref shortcut would lose information. The 90% threshold provides a downstream signal for "this relation is essentially in one ref, with a minor spill" without forcing the caller to compute it themselves.

**How to apply:**

- `compute_overlap_refs(start, end, spans) -> (refs, note)` is a pure function: no I/O, no model dependency, no defaults to inject. The 90% threshold is a named module-level constant; if it ever changes, change it in one place.
- Tests must cover: exact match, 50/50 even split, 92/8 lopsided, three-span coverage, threshold edges (89% / 90% / 91%), document-edge offsets.
- If `note` rates exceed ~30% on a representative corpus in practice, revisit the threshold (or the harvest separator, which affects how often EDUs straddle).

Related: [[decision-consumer-agnostic]].
