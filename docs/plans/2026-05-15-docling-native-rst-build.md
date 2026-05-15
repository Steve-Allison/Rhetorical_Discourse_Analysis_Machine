# Docling-native RST output — build plan

**Status:** Ready to start (Phase 0 mostly complete; see § Phase 0 verification log)
**Date:** 2026-05-15
**Driver:** Steve Allison
**Proposal:** [`./2026-05-15-docling-native-rst.md`](./2026-05-15-docling-native-rst.md)
**Estimated effort:** 3–5 days of focused work
**Target consumers:** consumer-agnostic; any tool wanting RST relations on `DoclingDocument`-shaped input.

---

## Goal

Ship `isanlp_rst.docling.parse_docling(path)` — a new entry point that accepts a Docling JSON file and emits one RST tree (relations + EDUs, in flat-with-`left_id`/`right_id` form) over the cue-aware harvest, with boundary metadata (slide / page / section / turn / table) layered on top as annotations on each relation. One `Parser` call per document.

## Verified facts (post-investigation)

Investigated 2026-05-15 against `docling-core` `main` and a real-world Docling JSON corpus across pptx / pdf / vtt / html-markdown source formats. Key facts the design relies on:

- **Loader:** `DoclingDocument.load_from_json(filename: Union[str, Path]) -> DoclingDocument` — `docling_core/types/doc/document.py:5778`.
- **Walker:** `DoclingDocument.iterate_items(root=None, with_groups=False, traverse_pictures=False, page_no=None, included_content_layers=None) -> Iterable[tuple[NodeItem, int]]` — `document.py:5535`. Pre-order DFS through `body.children`, resolves `$ref` via `child_ref.resolve(self)`, yields `(NodeItem, depth)` tuples.
- **Default filter:** `DEFAULT_CONTENT_LAYERS = {ContentLayer.BODY}` — `document.py:1291`. Page headers, footers, slide masters, and other furniture-layer content are excluded by default.
- **Schema:** all inspected sources emit `DoclingDocument` v1.10.0 with uniform top-level shape (`body`, `furniture`, `groups`, `texts`, `pictures`, `tables`, `pages`, `origin`, …). Source-format differences are which fields are *populated*, not which fields *exist*.
- **`.texts[]` order ≠ canonical reading order.** Must walk via `body.children`. `iterate_items()` does this.
- **`origin.binary_hash`** is already present in every Docling input — consumers wanting a source-cache key use it directly.

## Dependencies

This entry point adds **one** new runtime dependency:

- **`docling-core`** — pure Python + Pydantic. Used for `DoclingDocument` loading, validation, and canonical iteration. Added to `pyproject.toml` (runtime) and `pixi.toml` (locked env). Version pin: TBD during Phase 0 (use latest stable; record in verification log).

No other new dependencies.

## Architecture

```text
parse_docling(path, **knobs)
  │
  ├─→ doc = DoclingDocument.load_from_json(path)
  │
  ├─→ harvest = harvest_docling_text(doc, knobs)
  │     # walks iterate_items(traverse_pictures=True); concatenates text;
  │     # records (self_ref, start, end) per harvested span.
  │     # cue-aware: section headers, slide notes, picture captions per knobs.
  │     # tables NOT harvested into full_text (their self_refs still seen by boundary detector).
  │
  ├─→ boundaries = detect_boundaries(doc, knobs)
  │     # walks Docling structure; produces ordered list of Boundary entries with
  │     # id / kind / label / parent_self_ref / self_refs. Source-format-aware.
  │
  ├─→ rst_tree = Parser(...).parse(harvest.full_text)
  │     # ONE Parser call; one DiscourseUnit tree over the full harvested text.
  │
  └─→ result = map_tree_to_refs(rst_tree, harvest, boundaries)
        # for each tree node: map node.start/end → self_refs via overlap rule.
        # for each relation: compute boundary_memberships by intersecting refs with boundary.self_refs.
        # flatten tree to relations[] + edus[]; preserve hierarchy via left_id / right_id.

  return DoclingRstResult(metadata, boundaries, relations, edus)
```

Boundary detection is independent of RST parsing. Boundaries come from the Docling structure; the tree comes from the harvested text; they meet at the mapper.

## Module structure

```text
isanlp_rst/docling/
  __init__.py          # exports: parse_docling, DoclingRstResult
  harvester.py         # harvest_docling_text(), HarvestSpan, HarvestResult
  boundaries.py        # detect_boundaries(), Boundary; per-format detection rules
  mapper.py            # map_tree_to_refs(), compute_overlap_refs(), tree-flattening
  schema.py            # DoclingRstResult, Boundary, RstRelation, RstEdu (typed dataclasses)
  _entry.py            # parse_docling() orchestrator
```

The existing `Parser` facade is reused unchanged.

## Public API

```python
from pathlib import Path
from isanlp_rst.docling import parse_docling, DoclingRstResult

result: DoclingRstResult = parse_docling(
    Path("source.docling.json"),
    # Model selection
    hf_model_name="tchewik/isanlp_rst_v3",
    hf_model_version="gumrrg",
    relinventory=None,                       # required for unirst
    # Device
    device="auto",                           # "auto" | "cpu" | "cuda:N" | "mps"
    # Harvest policy (what enters the RST input)
    include_picture_captions=True,
    include_furniture=False,
    harvest_separator="\n\n",
    # Boundary policy (annotation only)
    coalesce_speaker_turns=True,
    # Overlap rule
    note_threshold=0.90,
)
```

## Internal types (modern Python 3.13+ idioms)

```python
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class HarvestSpan:
    self_ref: str        # e.g. "#/texts/47"
    text: str
    start: int           # offset in the concatenated harvest
    end: int             # exclusive

@dataclass(frozen=True, slots=True)
class HarvestResult:
    full_text: str
    spans: tuple[HarvestSpan, ...]

@dataclass(frozen=True, slots=True)
class Boundary:
    id: str                                  # e.g. "slide-0", "section-3", "turn-7", "table-0"
    kind: str                                # "slide" | "slide-notes" | "section" | "turn" | "table" | "document"
    label: str | None                        # human-readable (slide title, speaker voice, section heading)
    parent_self_ref: str | None              # e.g. "#/groups/0" for slide groups; None for document boundary
    self_refs: tuple[str, ...]               # self_refs this boundary contains (or covers)

@dataclass(frozen=True, slots=True)
class RstRelation:
    id: int                                  # unique within this DoclingRstResult
    relation: str                            # e.g. "Elaboration"
    nuclearity: str                          # "NS" / "NN" / ""
    nucleus_refs: tuple[str, ...]
    satellite_refs: tuple[str, ...]
    depth: int
    left_id: int                             # child node id (relation or edu)
    right_id: int                            # child node id (relation or edu)
    boundary_memberships: tuple[str, ...]    # ids of boundaries this relation overlaps
    note: str | None = None                  # populated for lopsided overlaps or table refs

@dataclass(frozen=True, slots=True)
class RstEdu:
    id: int                                  # unique within this DoclingRstResult; referenced by RstRelation.left_id/right_id
    self_refs: tuple[str, ...]               # which self_refs this leaf's text spans
    depth: int

@dataclass(frozen=True, slots=True)
class DoclingRstResult:
    schema_name: str                         # "isanlp_rst_docling"
    schema_version: str                      # "1.0"
    tool: str                                # "isanlp_rst"
    tool_version: str                        # fork commit hash
    model_version: str                       # e.g. "gumrrg"
    inventory: str                           # e.g. "eng.rst.rstdt"
    source: str                              # input path
    source_origin: dict[str, object]         # mirror of doc.origin (mimetype, binary_hash, filename)
    boundaries: tuple[Boundary, ...]
    relations: tuple[RstRelation, ...]
    edus: tuple[RstEdu, ...]
```

Frozen dataclasses with `slots=True` for value semantics and lower memory. Native exception propagation; no `Result[T, E]`, no defensive returns. Serialise via stdlib `json` after converting to dicts.

## Output schema (canonical form)

See proposal's "Output shape" section.

## Implementation phases

### Phase 0 — Empirical validation of the one-tree architecture

The walker API is verified. The schema's top-level shape is verified on five files. What remains is empirical: does RST output on real Docling content actually make sense, does the schema-detail match assumptions on real fixtures, and does the parser hold up at document scale.

**Reordered (the order matters — earlier steps gate later ones):**

1. **Build the fixture set first.** Commit one Docling JSON per source flavour under `tests/fixtures/docling/`. Source from the CSM corpus at `Content_Structuring_Machine/project/sources/` (Steve's working corpus), suitably trimmed:
   - pptx (multi-slide with notes, tables, pictures)
   - pdf (multi-section with `level: 1` and ideally `level: 2` headers)
   - vtt (multi-speaker, multi-turn)
   - markdown / html (section-headed)
   - **OCR-PDF** (text wrapped in top-level pictures requiring `traverse_pictures=True`)
   Each < 200 KB, free of sensitive content. Adobe-owned content is fine; trim any genuinely confidential material.
2. **Empirical RST quality check** (gating). For each fixture, harvest the body text (without any `parse_docling()` infrastructure — just `iterate_items` + concatenate) and feed it to the existing `Parser` with `gumrrg`. Eyeball the resulting `DiscourseUnit` tree. Questions:
   - Does the tree make any semantic sense on slide-deck content?
   - Does it produce useful relations on VTT transcripts?
   - Does it handle mixed prose + bullets + captions gracefully?
   - Are there obviously wrong relations (e.g. "Elaboration" between two unrelated slides)?
   If the answer on a major source format is "the parser produces a tree but it's noise", the whole architecture is suspect and we rethink before any code. See [[open-rst-real-world-quality]].
3. **Schema-detail verification.** Against each fixture, verify the assumptions catalogued in [[open-schema-detail-verifications]]: slide-notes reachability via `iterate_items(included_content_layers={BODY, FURNITURE})`; `level` distribution on section_headers; OCR-PDF text structure; VTT `voice` reliability; table-cell layout in `data.grid`; `TextItem.text` vs `.orig`; `prov.page_no` reliability. Each gets a documented yes/no answer; update the proposal / build plan if any answer changes the design.
4. **Pin `docling-core`.** Latest stable; record in the verification log. **Discipline:** when a new `docling-core` version ships, bump this pin (the Docling JSON files in the wild will reflect whatever version produced them).
5. **Smoke-iterate** per fixture. Short script: load each, print `(self_ref, text_preview, content_layer, label, depth)` for each item yielded by `iterate_items(traverse_pictures=True, included_content_layers={BODY, FURNITURE})`. Eyeball: canonical order, no surprises, expected items reachable.
6. **Long-input smoke** on the largest fixture. Run the existing `Parser` on its harvested text. Outcomes per [[open-long-input-fallback]]:
   - Succeeds with coherent tree → architecture validated.
   - Succeeds with degraded quality → document the limit.
   - Fails (OOM, hang, garbage) → design-level redesign required.

**Output:** populate § Phase 0 verification log with findings from each step.

**Success criterion:** every step has a documented outcome; no step has the answer "we don't know"; if any step exposes a failure mode, the proposal / build plan is updated before Phase 1 starts.

### Phase 1 — Harvester + schema + boundary detection

**Files:** `harvester.py`, `schema.py`, `boundaries.py`.

**Implementation:**

- `harvest_docling_text(doc, *, include_picture_captions, include_furniture, harvest_separator) -> HarvestResult` — walks `iterate_items(traverse_pictures=True)`, filters per policy, concatenates text, records `HarvestSpan`s with `(self_ref, start, end)`. Skips `TableItem`s (their cells are excluded from RST input).
- `detect_boundaries(doc, *, coalesce_speaker_turns) -> tuple[Boundary, ...]` — source-format-aware. Dispatch on `doc.origin.mimetype`:
  - `application/vnd.ms-powerpoint`, `application/vnd.openxmlformats-officedocument.presentationml.presentation` → slide detection (one `slide-N` + one `slide-N-notes` per slide group)
  - `text/vtt` → speaker-turn coalescing
  - `application/pdf` and `text/markdown`, `text/html` → section detection (open new boundary at each `section_header`)
  - default → single `document` boundary covering everything
- Every source format also emits one `table-N` boundary per `TableItem` regardless of mimetype.
- Typed dataclasses in `schema.py` per § Internal types.

**Tests:** `tests/test_docling_harvester.py`, `tests/test_docling_boundaries.py`

Harvester:

- **Round-trip:** for each fixture, concatenated harvest matches a recorded golden text.
- **Self-ref coverage:** every text-carrying `self_ref` reachable through the iteration appears in `HarvestResult.spans` exactly once (subject to filter policy).
- **Determinism:** same source twice → byte-identical `full_text`.
- **Offsets consistent:** `full_text[span.start:span.end] == span.text` for every span.
- **Table exclusion:** no `#/tables/N` or `#/tables/N/grid/...` self_refs appear in `HarvestResult.spans`.

Boundaries:

- **PPTX:** N slides → 2N + (table count) boundaries (`slide-N`, `slide-N-notes`, `table-K`).
- **PDF:** every `section_header` opens a new boundary; pre-header content lives in a `document` boundary.
- **VTT:** contiguous-same-voice runs coalesce; speaker change opens new boundary.
- **Tables:** each `TableItem` emits exactly one `table-N` boundary regardless of source format.
- **No source-format special-casing in client code:** `detect_boundaries(doc)` works on every fixture.

**Success criterion:** all harvester + boundary tests pass; harvester is < 60 lines of code.

### Phase 2 — Mapper

**Files:** `mapper.py`.

**Implementation:**

- `compute_overlap_refs(start: int, end: int, spans: tuple[HarvestSpan, ...]) -> tuple[tuple[str, ...], str | None]` — pure function: returns `self_ref`s with any non-empty overlap, plus optional note for ≥ 90% lopsided overlaps.
- `flatten_tree(rst_tree, harvest_spans, boundaries) -> tuple[tuple[RstRelation, ...], tuple[RstEdu, ...]]` — walks the `DiscourseUnit` tree, assigns sequential ids, computes refs via overlap rule, computes `boundary_memberships` by intersecting each relation's refs with each boundary's `self_refs`. Leaves become `RstEdu`s; internal nodes become `RstRelation`s with `left_id` / `right_id` set.

**Tests:** `tests/test_docling_mapper.py`

Overlap rule:

- **Exact match:** range coincides with one span → single ref, no note.
- **50/50 split:** range spans two spans evenly → both refs, no note.
- **92/8 lopsided:** → both refs + note describing 8% spill.
- **Three-span coverage:** 30/40/30 across three → all three refs, no note.
- **Threshold edges:** 89% / 90% / 91% → verify note fires only at ≥ 90%.
- **Edge of document:** range at offset 0 or `len(full_text)` → no off-by-one.

Tree flattening:

- **Leaf detection:** every `DiscourseUnit` with no children → `RstEdu`; otherwise `RstRelation` with `left_id` / `right_id`.
- **Id stability:** sequential, deterministic ids.
- **Boundary memberships:** for a synthetic relation spanning two known boundaries, `boundary_memberships` contains both ids.
- **Single-boundary relation:** `boundary_memberships` has exactly one id.

**Success criterion:** all tests pass; `compute_overlap_refs` is pure; the 90% threshold is a named module-level constant.

### Phase 3 — Orchestrator + entry

**Files:** `_entry.py`, `__init__.py`.

**Implementation:**

- `parse_docling(path, **knobs) -> DoclingRstResult` orchestrates `load → harvest → boundaries → parse → flatten`.
- `__init__.py` exports `parse_docling`, `DoclingRstResult`, and the type aliases consumers may need (`Boundary`, `RstRelation`, `RstEdu`).

**Tests:** `tests/test_docling_entry.py`

- **End-to-end smoke per fixture:** real Docling source → non-empty `DoclingRstResult` with `>= 1` relations; every `self_ref` in relations exists in the source's `self_ref` set or the boundaries-extension cell refs.
- **Schema name/version stamped:** result carries `schema_name="isanlp_rst_docling"`, `schema_version="1.0"`.
- **Tree reconstructibility:** for every relation with non-null `left_id` / `right_id`, the referenced id exists in `relations` or `edus`.
- **Boundary tagging:** every relation has non-empty `boundary_memberships`; every listed id exists in `boundaries`.
- **Path handling:** `Path` and `str` inputs both work.

**Success criterion:** all five fixture smoke tests pass; output passes a JSON schema validation pass if we add one.

### Phase 4 — Docs

**Files:** `README.md` (new section), `docs/examples/docling-native.md` (usage walkthrough).

**Implementation:**

- "Docling-native output" section in `README.md` with the public API and a short example showing tree reconstruction.
- Usage walkthrough showing: parse → group by boundary → filter cross-boundary relations → reconstruct tree.

**Success criterion:** README example runs verbatim against a real Docling source.

## Testing strategy

- **Unit:** harvester (Phase 1), boundaries (Phase 1), mapper (Phase 2) — pure-function tests, fast, no model load.
- **Integration:** end-to-end via `parse_docling` (Phase 3) — slower; tagged `@pytest.mark.slow` so the nightly CI workflow picks it up.
- **Fixtures:** five Docling JSONs under `tests/fixtures/docling/` (pptx, pdf, vtt, markdown, OCR-PDF). Each < 200 KB, free of sensitive content. Golden harvest text + golden boundary list recorded alongside each.

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| `docling-core` schema bumps to a breaking version mid-implementation | Hard-pin the dependency. Track changelog; reassess at each upstream release. |
| EDU boundaries chronically straddle Docling spans | Overlap rule + note field. If `note` rates exceed ~30% on real corpora, revisit the threshold or harvest separator. |
| Long inputs cause RST parser degradation | Verified in Phase 0 long-input smoke test. If problematic, document the practical input-size limit. Sliding-window encoding (`tokenizer.model_max_length = 1e9`) is the upstream mitigation. |
| Source-format edge cases (empty `pages` map, missing `prov`, table-only documents, multi-language single document) | Format-coverage fixtures in Phase 1 catch this; `iterate_items()` abstracts most variance. |
| Boundary detection on weird sources (PDF with no `section_header` at all, single-line VTT, etc.) | Default `document` boundary covers everything; tests include edge cases (single-section PDF, single-speaker VTT). |
| Cross-boundary RST relations confuse downstream consumers | Documented in the proposal as expected behaviour; `boundary_memberships` annotation lets consumers filter. |

## Out of scope

- **Table cell-level RST.** Tables are structurally grids; cells excluded from RST input.
- **Parse-per-boundary architecture.** Considered and rejected (see proposal Revisions).
- **Contributing back to `tchewik/isanlp_rst`** (Elena's original repo). Not the default workflow.
- **Pedagogic / domain judgement.** RST is descriptive linguistics.
- **Embedding outputs.** Separate scaffold layer.
- **Streaming / async API.** Synchronous only.
- **Custom relation taxonomies.** Whatever the RST model emits, we relay.
- **CLI entry point.** Python API only. Add later if needed.

## Open questions to close before Phase 1

The 2026-05-15 critical review surfaced a larger set than the original three. See the project memory:

- [[open-rst-real-world-quality]] — gating: empirical RST quality on real fixtures.
- [[open-schema-detail-verifications]] — slide notes, levels, OCR-PDF, VTT voice, tables, .orig/.text.
- [[open-boundary-design-decisions]] — `boundary_memberships` semantics, section nesting, pages, picture-caption / OCR-text disambiguation, degenerate cases.
- [[open-output-schema-specifics]] — relation / EDU / boundary ordering, id space, tool_version format, source field, JSON serialisation.
- [[open-long-input-fallback]] — what `parse_docling()` does if the parser fails at scale.

**Carried over from the previous open-questions list:**

1. **`harvest_separator` default:** `\n\n` is the lean (matches existing flat-text usage). If Phase 0 step 6 long-input smoke shows the parser handles ` ` separators just as well and avoids spurious paragraph-break inference, consider that instead. Resolution: measure.
2. **Malformed source policy:** when `docling-core` raises on load (Pydantic validation error), let it propagate — that's the contract. When `iterate_items` yields a node with empty `text` or unexpected shape, skip silently or raise? Default lean: skip with a one-time `logging.debug` for empty text; raise on unexpected shape (per no-defensive-coding rule).

Resolution sequence: Phase 0 closes the empirical questions in the memory files; Phase 1 starts only when each has a documented answer.

## Acceptance test for the whole feature

```python
from pathlib import Path
from isanlp_rst.docling import parse_docling

result = parse_docling(
    Path("tests/fixtures/docling/sample.pptx.docling.json"),
    device="cpu",
)

assert result.schema_name == "isanlp_rst_docling"
assert result.schema_version == "1.0"
assert len(result.relations) > 0
assert len(result.edus) > 0
assert len(result.boundaries) > 0

# every referenced self_ref exists in the input or is a known cell-ref extension
input_refs = load_self_refs_from_docling("tests/fixtures/docling/sample.pptx.docling.json")
known_refs = input_refs | {b.id for b in result.boundaries}
for relation in result.relations:
    for ref in (*relation.nucleus_refs, *relation.satellite_refs):
        assert ref in input_refs, f"unknown self_ref: {ref}"

# tree is reconstructible: every left_id/right_id resolves
all_ids = {r.id for r in result.relations} | {e.id for e in result.edus}
for relation in result.relations:
    assert relation.left_id in all_ids
    assert relation.right_id in all_ids

# every relation belongs to at least one boundary
boundary_ids = {b.id for b in result.boundaries}
for relation in result.relations:
    assert len(relation.boundary_memberships) > 0
    for bid in relation.boundary_memberships:
        assert bid in boundary_ids
```

## Phase sequencing

1. **Phase 0** (gated; each step gates the next):
   1. Build 5-fixture set under `tests/fixtures/docling/`.
   2. Empirical RST quality check per fixture — if quality on slides / transcripts is poor, rethink before any further code.
   3. Schema-detail verification per the [[open-schema-detail-verifications]] checklist.
   4. Pin `docling-core` in `pyproject.toml` + `pixi.toml` (latest stable; bump-discipline when new versions ship).
   5. Smoke-iterate per fixture.
   6. Long-input smoke against existing `Parser`.
2. Resolve the open design decisions in [[open-boundary-design-decisions]] and [[open-output-schema-specifics]].
3. **Phase 1:** harvester + schema + boundaries (parallel-developable, mostly independent).
4. **Phase 2:** mapper (tree flattening + boundary tagging).
5. **Phase 3:** orchestrator + entry + integration tests.
6. **Phase 4:** docs.
7. Cut a release tag.

Each phase has its own success criterion above. No phase counts as done until its tests pass.

## Phase 0 verification log

**Investigated 2026-05-15** against `docling-core` `main` and a real-world Docling JSON corpus (five files across four source formats — pptx, pdf, vtt, html/markdown — held in a local working corpus).

- **Canonical iteration API confirmed:** `DoclingDocument.iterate_items(...)` at `docling_core/types/doc/document.py:5535`. Pre-order DFS through `body.children`; resolves `$ref` via `child_ref.resolve(self)`. Yields `(NodeItem, depth)` tuples.
- **Loader confirmed:** `DoclingDocument.load_from_json(filename)` at `document.py:5778`.
- **Default filter confirmed:** `DEFAULT_CONTENT_LAYERS = {ContentLayer.BODY}` (document.py:1291).
- **Schema uniformity confirmed:** five Docling JSONs across four source formats (pptx / pdf / vtt / html-markdown) all emit `DoclingDocument` v1.10.0 with identical top-level shape.
- **Text-carrying node types observed:** `TextItem` (with subclass-level labels `text`, `section_header`, `list_item`, `title`, `page_footer`). `PictureItem.captions` carries `$ref`s to text items (skipped by default; we'll pass `traverse_pictures=True` for OCR-PDF support). `TableItem.data.grid[].text` is cell-level content (not yielded by `iterate_items`; intentionally excluded from harvest).
- **`origin.binary_hash`** is already a field in every Docling input JSON.

**Outstanding Phase 0 work:**

- Pin `docling-core` version (latest stable as of implementation start).
- Build and commit the five fixture files (pptx, pdf, vtt, markdown, OCR-PDF) under `tests/fixtures/docling/`.
- Run the smoke-iterate script on each fixture.
- Run the long-input smoke test on the largest fixture (or one ~50KB harvested text) to verify the one-tree architecture works at scale.

---

*Generated 2026-05-15. Companion to the proposal at [`./2026-05-15-docling-native-rst.md`](./2026-05-15-docling-native-rst.md).*
