---
name: open-parse-per-boundary
description: Alternative architecture — parse RST once per slide / page / speaker turn, aggregate. Never properly compared against concat-and-parse. May be both simpler and higher quality.
metadata:
  type: project
---

The current build plan assumes one giant RST tree over a concatenated text. An alternative: produce one RST tree per slide / page / speaker turn / section, then aggregate.

**Pros:**

- No cross-boundary RST relations possible by construction. Resolves [[open-boundary-preservation]] entirely.
- Mapper simplifies: each tree's offsets index into its own boundary's text. No global-offset arithmetic; the overlap rule is per-boundary.
- Smaller inputs per parse → faster, less memory pressure, no risk of multi-MB inputs hitting model limits.
- Per-boundary parses are independently parallelisable.

**Cons:**

- N model passes instead of 1. For a 50-slide deck, that's 50 forward passes. Some setup amortises (model loaded once), but inference time scales with N.
- Some discourse relations *do* cross boundaries (a section header introducing a list; a cross-slide narrative arc). We'd never detect these. Open question: how often does this matter in practice?
- Aggregation logic: do we keep separate per-boundary RST trees in the output, or flatten into one self-ref-indexed list? Probably the latter (matches the proposal's output shape), but with a `boundary_id` field per relation so consumers can re-group.

**Open empirical questions:**

- For pptx: is cross-slide RST ever meaningful? My current intuition: rarely.
- For pdf: is cross-page RST ever meaningful? My intuition: sometimes, at section boundaries that happen to coincide with page breaks.
- For vtt: is cross-speaker-turn RST ever meaningful? My intuition: sometimes (one speaker's turn elaborates the prior speaker's claim), but the model isn't trained on conversational discourse.

**How to apply:**

- This is a real alternative architecture, not just a "v2 improvement". If it wins, it changes Phase 1 of the build plan from harvest+mapper to per-boundary-orchestrator+aggregator.
- Worth a focused session: pick one fixture per source flavour, hand-author "ideal" RST output, compare what each architecture would produce.

Related: [[open-boundary-preservation]].
