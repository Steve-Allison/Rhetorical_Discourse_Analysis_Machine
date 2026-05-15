---
name: open-boundary-design-decisions
description: Specific design calls still needed for the boundary system. Boundary membership semantics, section nesting, pages as boundaries, picture-caption / OCR-text disambiguation, degenerate cases (empty boundaries, single-turn VTT, table-only documents).
metadata:
  type: project
---

The Docling-native plan introduces a `boundaries[]` list and `boundary_memberships` annotation on each relation. Several specifics need design decisions before Phase 1.

## `boundary_memberships` semantics

**Open:** a relation has `nucleus_refs: ["#/texts/47"]` (in `slide-0`) and `satellite_refs: ["#/texts/120"]` (in `slide-3`). What is `boundary_memberships`?

Two readings:

1. **"This relation touches these boundaries"** → `["slide-0", "slide-3"]`. A relation spanning two boundaries lists both. Consumers filtering by `boundary_memberships == ["slide-0"]` miss this relation. Current spec.
2. **"This relation is bounded within these boundaries"** → only listed when fully contained. Cross-boundary relations have `boundary_memberships: []` or a sentinel. Consumers can filter for "within-X-only" cleanly.

Reading (1) is more permissive; reading (2) is more useful for "within-this-slide" queries. Could expose both via richer schema.

**Decision needed:** pick a reading. Recommend (1) + add a separate `is_cross_boundary: bool` field for fast filtering. Decide before Phase 1.

## Section nesting (parent_boundary_id)

**Open:** PDF with `level: 1` section "Introduction" containing `level: 2` sub-section "Background". Per current rule (open new boundary at every section_header, regardless of level), these are sibling boundaries — but in the source they're nested.

**Options:**

- Keep sibling-flat structure. Consumers reconstruct nesting from `level` field on the opening section_header.
- Add `Boundary.parent_boundary_id: str | None`. When a `level: 2` header opens within an active `level: 1` boundary, the new boundary's parent is the active one.
- Add `Boundary.level: int | None` (mirrors source). Optional.

Recommend: add `level: int | None` (passes through Docling's hint cheaply); skip `parent_boundary_id` until a consumer asks for it.

## Page boundaries

**Open:** the plan dropped page boundaries entirely in favour of section boundaries. But:

- PDFs without section headers have no boundaries other than the default `document`. Loses page-level groupability.
- Consumers may legitimately want "all relations on page 5" — currently no way to express this.
- PPTX slides are page-like; we have them as `slide-N` boundaries.

**Options:**

- Add `Boundary.kind: "page"` for PDFs, alongside `section`. Every PDF would have N page boundaries + M section boundaries (potentially overlapping).
- Don't emit page boundaries; expose `prov.page_no` per harvested span on `HarvestSpan` (already there), let consumers compute.
- Emit page boundaries only when no section_headers exist (fallback).

Recommend: do not emit page boundaries by default. Expose `page_no` on each `Boundary` (when applicable) as metadata. Consumers wanting page-level grouping use the metadata.

## Picture-caption vs OCR-text disambiguation

**Open:** with `traverse_pictures=True`, `iterate_items` yields texts inside pictures. These texts could be:

- **OCR-extracted text** in a scanned-PDF page-image picture: real content, should always be harvested.
- **Picture captions** (alt-text-like) for an embedded figure: meta-content, may or may not be wanted (the `include_picture_captions` knob).

A single boolean knob can't cleanly distinguish them. Distinction requires inspecting the parent `PictureItem`'s `label` or properties.

**Verification needed:** what does an OCR-PDF look like? Is the parent picture distinguishable from a "caption-bearing figure" picture? Probably via the picture's label or annotation set — needs Phase 0 step 3 inspection.

**Once verified:** the `include_picture_captions` knob filters only "caption-bearing figure" picture-children, not OCR-PDF wrapped text.

## Degenerate cases

### Empty boundary

A section_header followed immediately by another section_header → boundary with zero `self_refs`. Current spec silent.

**Decision:** filter out empty boundaries before emitting. They add noise without value. Document this.

### Single-EDU boundary

A turn-N boundary with one short utterance → RST input is one EDU, parser produces a trivial tree (one EDU, zero relations). Current spec silent.

**Decision:** still emit the boundary in `boundaries[]` (consumers know it exists); produce zero relations for it. Document.

### Table-only document

A Docling JSON with only `TableItem`s and no other body text. Harvest is empty; parser receives empty string. Current spec silent.

**Decision:** raise `EmptyHarvestError`. Tables alone don't enter the RST input by design (see [[decision-one-tree-per-document]] and the tables-as-grids exclusion). A document with nothing but tables has no RST output by definition.

### `coalesce_speaker_turns=False`

Every VTT turn becomes its own boundary. With short turns, each boundary has one EDU, zero relations. Output is mostly empty.

**Decision:** keep the knob but document the degeneracy in the docstring. Default `True` (sensible behaviour); `False` is for consumers who know what they're doing.

## How to apply

Resolve each of these design questions before Phase 1 starts. Update the proposal and build plan accordingly. Each decision lands as a clarification in the output-schema spec or the harvester docstring.

Related: [[decision-one-tree-per-document]], [[open-rst-real-world-quality]], [[open-output-schema-specifics]].
