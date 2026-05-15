---
name: open-boundary-preservation
description: Open design question — naïve text concatenation in the harvester produces cross-slide / cross-page / cross-speaker-turn RST relations. Likely makes v1 output unfit for purpose. Needs resolution before Phase 1 starts.
metadata:
  type: project
---

**The biggest gap in the current Docling-native RST plan.** The harvester walks `iterate_items()`, concatenates `TextItem.text` values with a separator, runs RST on the concatenation. But the source is never a flat stream:

- **PPTX:** slides are independent discourse units. RST relations *across* slides are noise.
- **PDF:** page breaks (and section breaks at `section_header` items with `level`) mark major discourse shifts.
- **VTT:** each `source.start_time` boundary is a speaker turn. Speaker changes (`voice` field) are even more significant.
- **Markdown / HTML:** `section_header` with `level` is explicit hierarchy.

Without inserting boundary markers or running RST per-boundary, v1 will emit cross-slide / cross-speaker / cross-page relations that any downstream consumer will have to filter out. **This may make v1 unusable for the consumers we're designing for.**

**The boundary information is free** — `iterate_items()` gives us `depth`, items carry `prov.page_no`, group labels (`name: "slide-0"`), content-layer changes, `source.start_time`. The plan currently discards all of it.

**Options not yet compared:**

1. **Naïve concat (current v1 plan).** Ship it, document the limitation, leave boundary-handling to downstream consumers.
2. **Concat with boundary tokens.** Insert sentinel strings (`<page-break>`, `<slide-break>`, `<speaker-change>`) into the harvested text. The RST parser sees them and is more likely to break discourse there. Cost: trains-and-eval-time mismatch — the model wasn't trained on these tokens.
3. **Parse-per-boundary.** Run RST once per slide / page / speaker turn, aggregate into one `DoclingRstResult` with relations cleanly scoped to within boundaries. Cost: more model passes; simpler mapper. See [[open-parse-per-boundary]].

**How to apply:**

- Resolve this before Phase 1. The harvester architecture depends on which option wins.
- If we go with (1) for v1, the proposal should explicitly acknowledge the limitation; otherwise downstream consumers will discover it the hard way.
- If we go with (3), the build plan's architecture sketch is wrong and needs rewriting.

Related: [[open-parse-per-boundary]], [[verified-docling-schema]], [[decision-consumer-agnostic]].
