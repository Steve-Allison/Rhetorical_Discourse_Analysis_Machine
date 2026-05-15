# Docling-native RST output — build plan

**Status:** Phase 0 partly verified (`docling-core` API + Docling JSON schema, both at sample scope). Gating empirical work outstanding: dependency not yet pinned, RST quality on real fixtures not eyeballed, long-input behaviour not measured, determinism not checked. Phase 1 not eligible until §Decisions below are closed and Phase 0 success criteria met.
**Date:** 2026-05-15 (revised 2026-05-15 after critical review)
**Driver:** Steve Allison
**Proposal:** [`./2026-05-15-docling-native-rst.md`](./2026-05-15-docling-native-rst.md) (one paragraph in proposal §Tables to be struck in a follow-up edit; flagged in §Decisions: Table references below)
**Estimated effort:** 3–5 days of focused work — assumes Phase 0 RST-quality check passes on most source formats. Add 2–4 days if redesign required (e.g. if slide RST is incoherent and we need a per-section / per-slide fallback).
**Target consumers:** consumer-agnostic; any tool wanting RST relations on `DoclingDocument`-shaped input.

---

## Goal

Ship `isanlp_rst.docling.parse_docling(path)` — a new entry point that accepts a Docling JSON file and emits one RST tree (relations + EDUs, in flat-with-`left_id`/`right_id` form) over the cue-aware harvest, with boundary metadata (slide / page / section / turn / table) layered as annotations on each relation. One `Parser` call per document; the underlying `Parser` instance is **injectable** so batch consumers reuse weights.

## Verified facts (with evidence)

Investigated 2026-05-15 against `docling-core` `main` (fetched via raw GitHub URL) and the four real-world Docling JSONs in `tests/fixtures/docling/` (pptx, pdf, vtt, markdown). The original plan's "five files" claim included a no-longer-present fixture; the present fixture set is four.

- **Loader:** `DoclingDocument.load_from_json(filename: Union[str, Path]) -> DoclingDocument` — `docling_core/types/doc/document.py:5778`.
- **Walker:** `DoclingDocument.iterate_items(root=None, with_groups=False, traverse_pictures=False, page_no=None, included_content_layers=None) -> Iterable[tuple[NodeItem, int]]` — `document.py:5535`. Pre-order DFS through `body.children`, resolves `$ref` via `child_ref.resolve(self)`, yields `(NodeItem, depth)` tuples.
- **Default filter:** `DEFAULT_CONTENT_LAYERS = {ContentLayer.BODY}` — `document.py:1291`. Non-body layers excluded unless explicitly included.
- **`ContentLayer` enum:** `BODY`, `FURNITURE`, `BACKGROUND`, `INVISIBLE`, `NOTES` — `document.py:1281-1289`. PPTX slide notes live in `NOTES`; PDF page footers live in `FURNITURE` (sample-scoped on `pptx.docling.json`, `pdf.docling.json`).
- **Schema (sample-scope: four fixtures):** all four emit `DoclingDocument` v1.10.0 with identical top-level keys (`body`, `furniture`, `groups`, `texts`, `pictures`, `tables`, `pages`, `origin`, `form_items`, `key_value_items`, `name`, `schema_name`, `version`). Source-format differences are which fields are *populated*, not which exist. ASSUMED to generalise within the v1.10.x major; re-verify on a Docling minor-version bump.
- **`origin.binary_hash`** is a Python integer on all four fixtures. ASSUMED universal.
- **Picture-children iteration (sample-scoped on `pdf.docling.json`):** 24 of 48 `PictureItem`s have non-empty `children`, 130 child refs in total. Classifications observed across the picture set: `bar_chart`, `icon`, `table`, `logo`, `photograph`, `screenshot_from_computer`, `full_page_image` (the last with zero children in this fixture). The OCR-PDF case (`full_page_image` with children) and the regular-figure case (e.g. `bar_chart` with label children) use the **same `iterate_items(traverse_pictures=True)` code path**. Functional equivalence on a populated `full_page_image`: ASSUMED — covered by a Phase 1 unit test on picture-children yield rather than a separate OCR-PDF fixture.
- **`Parser` facade call shape:** `parser(text)` (i.e. `Parser.__call__`, **not** `.parse`); returns `{'rst': [tree]}` — a single-element list with one strictly-binary `DiscourseUnit` tree. Verified `isanlp_rst/parser.py:148`, `isanlp_rst/dmrst_parser/predictor.py:248-316`. Leaves are EDUs (`left is None and right is None`); internal nodes are relations; `remap_tree_offsets` (`base_predictor.py:126-167`) ensures every node's `.start` / `.end` are character offsets into the input text. Short-input fallback (`< 3 razdel tokens`) emits a `DUConverter.dummy_tree` with the same shape.
- **`Parser.from_edus(edus)` exists** (`parser.py:151`) — pre-segmented EDU path, returns same `{'rst': [tree]}` shape. Considered as an alternative input route; rejected in §Decisions: Input path.

## Dependencies — current state and plan

**Not yet added.** Verified 2026-05-15: `grep -n docling pyproject.toml` returns nothing; no separate `pixi.toml` file exists. Pixi configuration lives in `[tool.pixi.*]` blocks inside `pyproject.toml`; the lock is `pixi.lock`.

To add (Phase 0 step 1):

```bash
pixi add --pypi docling-core
```

This writes `docling-core==X.Y.Z` to `[project.dependencies]` in `pyproject.toml` and resolves the version into `pixi.lock`. Record the pinned version in the §Phase 0 verification log.

Bump discipline: on a `docling-core` minor or major version bump, re-run Phase 0 schema-verification (Docling JSONs in the wild reflect whatever producer version generated them; a schema bump can break our assumptions).

No other new dependencies.

## Architecture

```text
parse_docling(path, *, parser=None, **knobs)
  │
  ├─→ doc = DoclingDocument.load_from_json(path)
  │
  ├─→ harvest = harvest_docling_text(doc, knobs)
  │     # walks iterate_items(traverse_pictures=True, included_content_layers=...);
  │     # concatenates text, records (self_ref, start, end) per harvested span.
  │     # tables: NOT in harvest.full_text; their self_refs do NOT appear in any HarvestSpan.
  │
  ├─→ boundaries = detect_boundaries(doc, knobs)
  │     # walks Docling structure; ordered list of Boundary entries with
  │     # id / kind / label / parent_self_ref / self_refs. Source-format dispatch.
  │     # one table-N boundary per TableItem in every source format.
  │
  ├─→ parser = parser or Parser(...)           # injection point for batch consumers
  ├─→ rst_tree = parser(harvest.full_text)['rst'][0]
  │
  └─→ result = map_tree_to_refs(rst_tree, harvest, boundaries)
        # for each tree node: overlap-rule → refs.
        # for each relation: boundary_memberships = ids of boundaries whose
        #   self_refs intersect the relation's refs.
        # flatten tree → relations[] + edus[]; hierarchy preserved via left_id/right_id.

  return DoclingRstResult(metadata, boundaries, relations, edus)
```

Boundary detection is independent of RST parsing. Boundaries derive from the Docling structure; the tree derives from the harvested text; they meet at the mapper. The `Parser` instance is injectable so batch consumers can construct once and reuse weights.

## Module structure

```text
isanlp_rst/docling/
  __init__.py          # exports: parse_docling, DoclingRstResult, Boundary, RstRelation, RstEdu
  harvester.py         # harvest_docling_text(), HarvestSpan, HarvestResult
  boundaries.py        # detect_boundaries(), Boundary; per-format detection rules
  mapper.py            # map_tree_to_refs(), compute_overlap_refs(), tree flattening
  schema.py            # DoclingRstResult, Boundary, RstRelation, RstEdu (typed dataclasses)
  errors.py            # EmptyDoclingError, EmptyHarvestError, InputTooLargeError
  _entry.py            # parse_docling() orchestrator
```

The existing `Parser` facade is reused unchanged.

## Decisions (internalised — to be reflected in code)

Each item below was an open question in `.claude/memory/`. Decisions land here so Phase 1 has a closed contract. Memory files are kept as historical record.

### Parser caching / injection
`parse_docling(path, *, parser: Parser | None = None, ...)`. If `parser` is `None`, instantiate one from the model knobs (catastrophic for batch use — every call reloads ~2 GB of weights). Document that batch consumers must construct once and inject. **Rejected:** process-global `@functools.cache` on the Parser constructor — hides cost, surprises long-running services.

### Input path — harvest-and-segment vs `from_edus`
**Chosen:** harvest-and-segment. One `parser(harvest.full_text)` call; the parser does its own EDU segmentation. **Rejected:** treating each Docling `TextItem` as a pre-segmented EDU via `Parser.from_edus(edus)`. **Why:** Docling TextItems are layout-derived, not discourse-derived. A bullet list with five points is five TextItems but rarely five EDUs; a long paragraph is one TextItem but often multiple EDUs. The parser's segmentation is authoritative. Cost: EDUs can straddle `self_ref` boundaries → overlap rule handles it; `note` field documents lopsided cases.

### Table references
**Chosen:** `#/tables/N` **never** appears in `nucleus_refs` / `satellite_refs`. Tables are excluded from `harvest.full_text`, so no `HarvestSpan` carries `#/tables/N`, so the overlap rule cannot emit it. Tables are visible only via `boundaries[]` (one `table-N` per `TableItem`). **Rejected:** injecting a `[TABLE]` placeholder span — adds synthetic prose to RST input; muddies what the parser sees. **Proposal impact:** the proposal's §Tables paragraph claiming "the table's `self_ref` may still appear in a relation's `nucleus_refs` / `satellite_refs`" contradicts this. To be struck in a follow-up edit to the proposal.

### `boundary_memberships` semantics
**Chosen: "touches"** — `boundary_memberships` lists every boundary whose `self_refs` intersect the relation's refs. Cross-boundary relations have multi-element lists; consumers filter via `len(boundary_memberships) > 1`. **Rejected:** "contained-within" semantics (empty list for cross-boundary) — less informative for "this slide's discourse arc" queries. A separate `is_cross_boundary: bool` field is **not** added in v1.

### Section nesting
**Chosen:** sibling-flat `Boundary` list. Add `Boundary.level: int | None` (pass-through from Docling's `section_header.level`; `None` for non-section boundaries). Consumers reconstruct nesting from `level`. **Rejected:** `Boundary.parent_boundary_id` — adds graph structure no consumer has asked for.

### Page boundaries
**Chosen:** do **not** emit `kind: "page"` boundaries. Add `Boundary.page_no: int | None` as metadata (populated for PDF / PPTX where applicable; `None` for VTT / Markdown). **Rejected:** separate page boundaries — creates boundary overlap with sections and slides; consumer pain.

### `relations[]` and `edus[]` ordering, id space
- `relations[]`: pre-order DFS (root first; relation 0 is always the tree root).
- `edus[]`: left-to-right reading order (ascending start offset in the harvest).
- Id space: **shared sequential namespace** across `relations[]` and `edus[]`. `left_id` / `right_id` resolves uniformly to either. Deterministic given the same parser output.

### `tool_version` format
Resolution chain (first match wins, cached at module import):
1. `git describe --always --dirty` (when running in a git checkout).
2. `importlib.metadata.version("isanlp_rst")` (PyPI install / wheel).
3. Literal `"unknown"` (neither available).

Never raises.

### `source` field
**Chosen:** basename only (e.g. `"deck.docling.json"`). Full provenance lives in `source_origin`. **Rejected:** absolute path (leaks paths, breaks reproducibility).

### `source_origin` serialisation
`doc.origin` is a Pydantic model. Serialise via `doc.origin.model_dump(mode="json")` → `dict[str, Any]`. Pydantic guarantees JSON-safe primitives.

**Caveat:** `origin.binary_hash` is a 64-bit Python integer. Python's `json` round-trips it losslessly. JavaScript consumers parsing the JSON via `JSON.parse` will lose precision above 2^53. Documented in the public README; not changed in v1.

### JSON serialisation
- `indent: int | None = 2` as a serialiser knob; default 2 for readability.
- `sort_keys=True` — stable cross-run ordering.
- `ensure_ascii=False` — preserve UTF-8.
- `note=None` is **omitted from JSON output** (not emitted as `"note": null`). Affects byte-equality tests: relations without a note have no `note` key at all.
- UTF-8 no BOM; LF; trailing newline.

### Empty / degenerate cases
- Empty Docling JSON (no body content): raise `EmptyDoclingError`.
- Document with only `TableItem`s (no prose): raise `EmptyHarvestError`.
- One TextItem (one EDU after parser): valid output — one `RstEdu`, zero `RstRelation`, one `document` boundary.
- Empty boundary (consecutive section_headers with nothing between): **filtered out** of `boundaries[]`. Documented.
- `coalesce_speaker_turns=False` on short-turn VTT: mostly-empty output. Documented; default `True`.

### Long-input fallback
**Chosen:** option 1 — raise `InputTooLargeError` when `len(harvest.full_text)` exceeds a documented threshold. Threshold set empirically in Phase 0 step 6; initial guess 200,000 chars; refine after measurement. **Rejected:** per-section parse + merge (reintroduces parse-per-boundary), sliding-window vote aggregation (complex, non-standard). **Reopen trigger:** if a real consumer hits the limit and cannot chunk upstream, revisit.

### Device API
`parse_docling(..., device: str = "auto")`. Translation to `Parser`'s `cuda_device: int`:

| `device` value | Translation |
|---|---|
| `"auto"` | `cuda_device=0` (Parser then auto-selects CUDA → MPS → error per existing behaviour) |
| `"cpu"` | `cuda_device=-1` |
| `"mps"` | `cuda_device=0` (on Apple Silicon the integer is ignored) |
| `"cuda"` or `"cuda:0"` | `cuda_device=0` |
| `"cuda:N"` (N > 0) | `cuda_device=N` |
| any other string | `ValueError` |

Future `Parser` migration to a string `device` API is tracked separately ([[open-device-api]]); the mapping lives in `parse_docling` for now.

### Default model / inventory
**Chosen:** `hf_model_version="gumrrg"` (DMRST, English; trained on GUM corpus — essays, news, biographies, fiction).
**Caveat:** RST quality on non-prose (slides, transcripts) is unverified — Phase 0 step 5 is the empirical gate. If quality on slide content is poor, **the default may need to change** or the entry-point documentation must warn explicitly.
**For multilingual / Russian content:** caller passes `hf_model_version="unirst", relinventory="..."` explicitly. The original docstring claim "required for unirst" is misleading — the Parser falls back silently to `relinventory_idx=0`. Reword: "should be set when `hf_model_version="unirst"`; otherwise the model's first inventory is used."

### Python floor
`isanlp_rst/docling/` uses modern Python 3.13+ idioms (frozen-slots dataclasses, `X | None`, `match`). Current `requires-python = ">=3.8"` in `pyproject.toml` is too low; new module won't import on 3.8 / 3.9.
**Chosen:** bump `requires-python = ">=3.10"` and use `from __future__ import annotations` to defer hint evaluation (sufficient for 3.10 / 3.11). PEP 695 syntax (`type X = ...`, `def f[T](...)`) is **not** available below 3.12 — use old-style aliases / `TypeVar` in this module if Python 3.10 / 3.11 support matters. Phase 1 lint pass enforces.

## Public API

```python
from pathlib import Path
from isanlp_rst.parser import Parser
from isanlp_rst.docling import parse_docling, DoclingRstResult

# One-off use (loads model once, may be slow):
result: DoclingRstResult = parse_docling(
    Path("source.docling.json"),
    hf_model_version="gumrrg",
    device="auto",
)

# Batch use (load model once, reuse):
parser = Parser(hf_model_version="gumrrg", cuda_device=-1)
for path in paths:
    result = parse_docling(path, parser=parser)
```

Full signature:

```python
parse_docling(
    path: str | Path,
    *,
    # Parser injection (recommended for batch use)
    parser: Parser | None = None,
    # Model selection (used only when parser is None)
    hf_model_name: str = "tchewik/isanlp_rst_v3",
    hf_model_version: str = "gumrrg",
    relinventory: str | None = None,         # should be set when hf_model_version="unirst"
    # Device (used only when parser is None)
    device: str = "auto",                    # "auto" | "cpu" | "cuda:N" | "mps"
    # Harvest policy (what enters the RST input)
    include_picture_captions: bool = True,
    include_slide_notes: bool = True,        # ContentLayer.NOTES
    include_furniture: bool = False,         # ContentLayer.FURNITURE
    harvest_separator: str = "\n\n",
    # Boundary policy (annotation only)
    coalesce_speaker_turns: bool = True,
    # Overlap rule
    note_threshold: float = 0.90,
) -> DoclingRstResult: ...
```

## Internal types (modern Python idioms)

```python
from __future__ import annotations
from dataclasses import dataclass
from typing import Any

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
    self_refs: tuple[str, ...]               # self_refs this boundary covers
    level: int | None = None                 # section level passthrough (None if not a section)
    page_no: int | None = None               # page number passthrough where applicable

@dataclass(frozen=True, slots=True)
class RstRelation:
    id: int                                  # unique within DoclingRstResult; shared namespace with RstEdu.id
    relation: str                            # e.g. "Elaboration"
    nuclearity: str                          # "NS" / "NN" / ""
    nucleus_refs: tuple[str, ...]
    satellite_refs: tuple[str, ...]
    depth: int
    left_id: int                             # child node id (relation or edu)
    right_id: int                            # child node id (relation or edu)
    boundary_memberships: tuple[str, ...]    # ids of boundaries this relation touches
    note: str | None = None                  # populated for ≥ 90% lopsided overlaps; omitted from JSON when None

@dataclass(frozen=True, slots=True)
class RstEdu:
    id: int                                  # unique within DoclingRstResult; shared namespace with RstRelation.id
    self_refs: tuple[str, ...]
    depth: int

@dataclass(frozen=True, slots=True)
class DoclingRstResult:
    schema_name: str                         # "isanlp_rst_docling"
    schema_version: str                      # "1.0"
    tool: str                                # "isanlp_rst"
    tool_version: str                        # see §Decisions: tool_version
    model_version: str                       # e.g. "gumrrg"
    inventory: str                           # e.g. "eng.rst.rstdt"
    source: str                              # basename of input path
    source_origin: dict[str, Any]            # doc.origin.model_dump(mode="json")
    boundaries: tuple[Boundary, ...]
    relations: tuple[RstRelation, ...]
    edus: tuple[RstEdu, ...]
```

## Output schema (canonical form)

See proposal's "Output shape" section. Two changes from the proposal version, both per §Decisions above:

- Tables never appear in relation refs (proposal §Tables paragraph to be struck in a follow-up edit).
- `Boundary` carries `level` and `page_no` as optional metadata.

## Implementation phases

### Phase 0 — Empirical validation

**Status:** outstanding. API and schema verified at source / sample-scope; empirical questions below are gating.

1. **Pin `docling-core`** via `pixi add --pypi docling-core`. Record version in §Phase 0 verification log. Trivial — do first so subsequent steps run inside the pixi env.
2. **Smoke-iterate per fixture.** Short script: load each of the four existing fixtures, print `(self_ref, text_preview, content_layer, label, depth)` for items yielded by `iterate_items(traverse_pictures=True, included_content_layers={BODY, FURNITURE, NOTES})`. Eyeball canonical order, no surprises, expected items reachable. Confirm picture children appear in the iteration for the 24 picture-children in `pdf.docling.json`.
3. **OCR-PDF coverage decision (recommended: skip dedicated fixture).** The existing PDF fixture exercises `traverse_pictures=True` for `bar_chart`, `icon`, `table`, etc.; it does **not** contain a populated `full_page_image`. Iteration code path is the same regardless of classification per the `docling-core` walker — record this as ASSUMED in §Verified facts and add a Phase 1 unit test on picture-children yield. Only commit a dedicated `pdf.ocr.docling.json` if Phase 0 step 5 reveals OCR-specific oddities.
4. **Schema-detail verification** per `.claude/memory/open_schema_detail_verifications.md`. Still-open items: VTT multi-speaker behaviour (single-speaker fixture only), `TextItem.text` vs `.orig` (pick which to harvest — verify on a fixture with normalised text), section_header on OCR-extracted text (skipped if step 3 = yes).
5. **Empirical RST quality check (gating).** For each fixture, harvest body text (no `parse_docling()` infra — just `iterate_items` + concatenate) and feed to existing `Parser` with `gumrrg`. Eyeball each `DiscourseUnit` tree:
   - Slide content: does the tree make any semantic sense?
   - VTT transcript: useful relations or noise?
   - Mixed prose + bullets + captions: graceful or fragmented?
   - Obviously wrong relations (e.g. "Elaboration" between unrelated slides)?
   If any major source format produces noise, **redesign before any further code**. This is the most important step; redesign is preferable to building atop a broken assumption.
6. **Long-input smoke.** Run existing `Parser` on the largest harvested text (~50K chars from the 965 KB PDF fixture). Outcomes:
   - Coherent tree → set `InputTooLargeError` threshold above the tested size.
   - Tree returned but quality degrades → document the practical limit at the quality boundary.
   - OOM, hang, garbage → reopen §Decisions: Long-input fallback.
7. **Determinism check.** Run `parser(text)` twice on the same input under the same device + dtype; diff tree shapes. If byte-different, the Phase 3 reproducibility test must compare structurally (tree shape + node attributes) rather than byte-by-byte; record the decision in the verification log.

**Output:** populate § Phase 0 verification log with findings from each step.

**Success criterion:** every step has a documented outcome; no step has "we don't know"; if any step exposes a failure mode, the proposal / build plan are updated before Phase 1 starts.

### Phase 1 — Harvester + schema + boundary detection

**Files:** `harvester.py`, `schema.py`, `boundaries.py`, `errors.py`.

**Implementation:**

- `harvest_docling_text(doc, *, include_picture_captions, include_slide_notes, include_furniture, harvest_separator) -> HarvestResult` — walks `iterate_items(traverse_pictures=True, included_content_layers=...)` with the layer set built from the boolean knobs (always includes `BODY`; conditionally `NOTES` / `FURNITURE`). Concatenates text, records `HarvestSpan`s with `(self_ref, start, end)`. Skips `TableItem`s (cells excluded from RST input).
- `detect_boundaries(doc, *, coalesce_speaker_turns) -> tuple[Boundary, ...]` — source-format-aware dispatch on `doc.origin.mimetype`:
  - PPTX mimetypes → slide detection (one `slide-N` boundary per slide group; one `slide-N-notes` per slide containing any `content_layer: "notes"` descendant).
  - `text/vtt` → speaker-turn coalescing (consecutive same-voice runs).
  - `application/pdf`, `text/markdown`, `text/html` → section detection (new boundary at each `section_header`; carries `level`).
  - default → single `document` boundary covering everything.
- One `table-N` boundary per `TableItem` regardless of mimetype.
- Empty boundaries filtered.
- Typed dataclasses in `schema.py`; custom exceptions in `errors.py`.

**Tests:** `tests/test_docling_harvester.py`, `tests/test_docling_boundaries.py`.

Harvester:

- **Round-trip:** for each fixture, concatenated harvest matches a recorded golden text.
- **Self-ref coverage:** every text-carrying `self_ref` reachable through iteration appears in `HarvestResult.spans` exactly once (subject to filter policy).
- **Determinism:** same source twice → byte-identical `full_text`.
- **Offsets consistent:** `full_text[span.start:span.end] == span.text` for every span.
- **Table exclusion:** no `#/tables/N` or `#/tables/N/grid/...` self_refs in `HarvestResult.spans`.
- **Picture children:** for `pdf.docling.json`, all 130 picture child refs appear in `HarvestResult.spans` when `include_picture_captions=True`.

Boundaries:

- **PPTX:** N slides → 2N + (table count) boundaries (`slide-N`, `slide-N-notes`, `table-K`).
- **PDF:** every `section_header` opens a new boundary; pre-header content covered by a `document` boundary.
- **VTT:** contiguous same-voice runs coalesce; speaker change opens new boundary.
- **Tables:** each `TableItem` emits exactly one `table-N` boundary in every source format.
- **Empty boundaries filtered.**
- **No source-format special-casing in client code:** `detect_boundaries(doc)` works on every fixture.

**Success criterion:** all harvester + boundary tests pass; harvester is < 80 lines of code.

### Phase 2 — Mapper

**Files:** `mapper.py`.

**Implementation:**

- `compute_overlap_refs(start: int, end: int, spans: tuple[HarvestSpan, ...]) -> tuple[tuple[str, ...], str | None]` — pure function: returns `self_ref`s with any non-empty overlap, plus optional note for ≥ 90% lopsided overlaps. `NOTE_THRESHOLD = 0.90` named module-level constant.
- `flatten_tree(rst_tree, harvest_spans, boundaries) -> tuple[tuple[RstRelation, ...], tuple[RstEdu, ...]]` — walks the `DiscourseUnit` tree in pre-order; assigns sequential ids in a shared namespace; computes refs via overlap rule; computes `boundary_memberships` by intersecting each relation's refs with each boundary's `self_refs`. Leaves → `RstEdu`s; internal nodes → `RstRelation`s with `left_id` / `right_id` set.

**Tests:** `tests/test_docling_mapper.py`.

Overlap rule:

- Exact match: range coincides with one span → single ref, no note.
- 50/50 split: range spans two spans evenly → both refs, no note.
- 92/8 lopsided: → both refs + note describing the 8% spill.
- Three-span coverage: 30/40/30 across three → all three refs, no note.
- Threshold edges: 89% / 90% / 91% → note fires only at ≥ 90%.
- Edge of document: range at offset 0 or `len(full_text)` → no off-by-one.

Tree flattening:

- Leaf detection: `unit.left is None and unit.right is None` → `RstEdu`; otherwise `RstRelation`.
- Id stability: sequential and deterministic.
- Boundary memberships: relation spanning two known boundaries → `boundary_memberships` contains both ids.
- Single-boundary relation: `boundary_memberships` has exactly one id.

**Success criterion:** all tests pass; `compute_overlap_refs` is pure; the 0.90 threshold is a named module-level constant.

### Phase 3 — Orchestrator + entry

**Files:** `_entry.py`, `__init__.py`.

**Implementation:**

- `parse_docling(path, *, parser=None, **knobs) -> DoclingRstResult` orchestrates `load → harvest → boundaries → parse → flatten`. When `parser is None`, instantiates one from the model knobs.
- `_resolve_device(device: str) -> int` — pure helper mapping the string device API to `cuda_device: int` per §Decisions.
- `_resolve_tool_version() -> str` — `git describe` → `importlib.metadata.version` → `"unknown"` chain; cached at module import.
- `__init__.py` exports `parse_docling`, `DoclingRstResult`, `Boundary`, `RstRelation`, `RstEdu`, and the three error types.

**Tests:** `tests/test_docling_entry.py`.

- End-to-end smoke per fixture: real Docling source → non-empty `DoclingRstResult` with `len(relations) >= 1`.
- Schema name / version stamped correctly.
- Tree reconstructibility: for every relation, `left_id` / `right_id` exist in the union of `relations` and `edus`.
- Boundary tagging: every relation has non-empty `boundary_memberships`; every listed id exists.
- Table refs absent: `#/tables/...` never appears in any relation's refs.
- Path handling: `Path` and `str` inputs both work.
- Parser-injection path: a pre-constructed `Parser` is reused; second call does not redownload weights.
- Empty / degenerate cases: `EmptyDoclingError`, `EmptyHarvestError` raised on the right inputs.
- Long-input: `InputTooLargeError` raised above the configured threshold.

**Success criterion:** all fixture smoke tests pass; output passes a JSON-schema validation pass if we add one.

### Phase 4 — Docs

**Files:** `README.md` (new section), `docs/examples/docling-native.md` (usage walkthrough).

**Implementation:**

- "Docling-native output" section in `README.md` with the public API, the batch-injection idiom, and a short tree-reconstruction example.
- Walkthrough showing: parse → group by boundary → filter cross-boundary relations → reconstruct tree.
- Note on `binary_hash` JS precision; note on the empirical RST-on-slides caveat from Phase 0 step 5.

**Success criterion:** README example runs verbatim against a real Docling source.

## Testing strategy

- **Unit:** harvester (Phase 1), boundaries (Phase 1), mapper (Phase 2) — pure-function tests, fast, no model load.
- **Integration:** end-to-end via `parse_docling` (Phase 3) — slower; tagged `@pytest.mark.slow` so nightly CI picks it up.
- **Fixtures:** four Docling JSONs under `tests/fixtures/docling/` (pptx, pdf, vtt, markdown). OCR-PDF iteration assumed equivalent and covered by a picture-children unit test. Golden harvest text + golden boundary list recorded alongside each fixture.
- **Fixture size:** keep individual fixtures manageable for git diff (target < 1 MB; trim larger ones during fixture refresh). The current PDF fixture is 965 KB and the PPTX is 333 KB — both inside this budget.

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| `docling-core` schema bumps to a breaking version mid-implementation | Hard-pin via `pixi add --pypi docling-core`; track changelog; reassess at each upstream release. |
| EDU boundaries chronically straddle Docling spans | Overlap rule + `note` field. If note rates exceed ~30% on real corpora, revisit threshold or harvest separator. |
| Long inputs degrade or fail | Phase 0 step 6 measures; `InputTooLargeError` is the documented contract. |
| RST quality on non-prose (slides / transcripts) is poor | Phase 0 step 5 is gating; redesign before code if quality is unacceptable. |
| Source-format edge cases | Format-coverage fixtures catch most; `iterate_items()` abstracts most variance. |
| Cross-boundary RST relations confuse consumers | Documented behaviour; `boundary_memberships` annotation lets consumers filter. |
| Batch consumers reload weights on every call | Parser-injection contract documented; integration test verifies single-load behaviour. |
| Determinism not byte-equivalent | Phase 0 step 7 measures; reproducibility test compares structurally if needed. |

## Out of scope

- Table cell-level RST. Tables are grids; cells excluded from RST input.
- Parse-per-boundary architecture. Rejected (see proposal Revisions).
- Contributing back to `tchewik/isanlp_rst`. Not the default workflow.
- Pedagogic / domain judgement. RST is descriptive linguistics.
- Embedding outputs. Separate scaffold layer.
- Streaming / async API. Synchronous only.
- Custom relation taxonomies. Whatever the RST model emits, we relay.
- CLI entry point. Python API only.
- Bump `Parser` device API to strings. Tracked separately ([[open-device-api]]).

## Acceptance test for the whole feature

```python
from pathlib import Path
from isanlp_rst.parser import Parser
from isanlp_rst.docling import parse_docling

PATH = Path("tests/fixtures/docling/pptx.docling.json")

# One-off call
result = parse_docling(PATH, device="cpu")

assert result.schema_name == "isanlp_rst_docling"
assert result.schema_version == "1.0"
assert len(result.relations) > 0
assert len(result.edus) > 0
assert len(result.boundaries) > 0

# every self_ref in relations exists in the source's self_ref set
input_refs = load_self_refs_from_docling(PATH)
for relation in result.relations:
    for ref in (*relation.nucleus_refs, *relation.satellite_refs):
        assert ref in input_refs, f"unknown self_ref: {ref}"

# table refs never appear in relation refs (decision: tables are boundary-only)
for relation in result.relations:
    for ref in (*relation.nucleus_refs, *relation.satellite_refs):
        assert not ref.startswith("#/tables/"), f"table ref leaked: {ref}"

# tree is reconstructible: every left_id / right_id resolves
all_ids = {r.id for r in result.relations} | {e.id for e in result.edus}
for relation in result.relations:
    assert relation.left_id in all_ids
    assert relation.right_id in all_ids

# every relation has non-empty boundary_memberships; every id exists
boundary_ids = {b.id for b in result.boundaries}
for relation in result.relations:
    assert len(relation.boundary_memberships) > 0
    for bid in relation.boundary_memberships:
        assert bid in boundary_ids

# parser injection: same parser instance reused across two calls
parser = Parser(hf_model_version="gumrrg", cuda_device=-1)
result_a = parse_docling(PATH, parser=parser)
result_b = parse_docling(PATH, parser=parser)
assert result_a.schema_name == result_b.schema_name
# (byte-equality between result_a and result_b only asserted if Phase 0 step 7 confirms determinism)
```

## Phase sequencing

1. **Phase 0** (each step gates the next):
   1. Pin `docling-core` via `pixi add --pypi docling-core`.
   2. Smoke-iterate per fixture.
   3. OCR-PDF coverage decision.
   4. Schema-detail verification.
   5. Empirical RST quality check (gating; redesign if poor).
   6. Long-input smoke.
   7. Determinism check.
2. Update §Decisions if any Phase 0 outcome changes the answer.
3. **Phase 1:** harvester + schema + boundaries.
4. **Phase 2:** mapper (tree flattening + boundary tagging).
5. **Phase 3:** orchestrator + entry + integration tests.
6. **Phase 4:** docs.
7. Cut a release tag.

Each phase has its own success criterion above. No phase counts as done until its tests pass.

## Phase 0 verification log

**Investigated 2026-05-15** against `docling-core` `main` (raw GitHub) and the four real Docling JSONs at `tests/fixtures/docling/` (pptx, pdf, vtt, markdown).

**Verified at source level (`docling-core` `main`):**

- `DoclingDocument.iterate_items(...)` at `document.py:5535`.
- `DoclingDocument.load_from_json(filename)` at `document.py:5778`.
- `DEFAULT_CONTENT_LAYERS = {ContentLayer.BODY}` at `document.py:1291`.
- `ContentLayer` enum `BODY/FURNITURE/BACKGROUND/INVISIBLE/NOTES` at `document.py:1281-1289`.
- `PictureClassificationLabel.FULL_PAGE_IMAGE` is a defined value at `document.py:~6408`.

**Verified at fixture level (four files):**

- All emit `DoclingDocument` v1.10.0 with identical top-level keys.
- `origin.binary_hash` is a Python integer on all four.
- `pdf.docling.json`: 684 texts; 48 pictures (24 with non-empty children, 130 child refs total). Classifications observed: `bar_chart`, `icon`, `table`, `logo`, `photograph`, `screenshot_from_computer`, `full_page_image` (zero children in this fixture).
- `pptx.docling.json`: 8 texts, 9 groups, 20 tables, 5 pictures. Slide notes at `content_layer: "notes"`, parented to slide groups.
- `markdown.docling.json`: 51 texts, 8 groups, 0 tables. Section headers at levels `[2, 3]` (no `level: 1`).
- `vtt.docling.json`: 37 texts, single distinct voice (`SPEAKER_00`).

**Verified at this codebase:**

- `Parser.__call__(text)` returns `{'rst': [tree]}`; tree is strictly binary; `remap_tree_offsets` produces character offsets into input text (`isanlp_rst/parser.py:148`, `dmrst_parser/predictor.py:248-316`, `base_predictor.py:126-167`).
- `Parser.from_edus(edus)` exists and returns the same shape (`parser.py:151`).
- No `docling-core` dependency present (`grep -n docling pyproject.toml` returns nothing; no separate `pixi.toml`).

**Outstanding (Phase 0 work to complete before Phase 1):**

- Pin `docling-core` version via `pixi add --pypi docling-core`.
- Run `iterate_items` smoke test per fixture under the pixi env (confirm what was inferred from source).
- Resolve `TextItem.text` vs `.orig` (verify on a fixture with normalised text).
- VTT multi-speaker: add or source a multi-speaker fixture if needed.
- Empirical RST quality check on each fixture (gating).
- Long-input smoke on the largest fixture.
- Determinism check (twice-run `parser(text)` diff).

---

*Generated 2026-05-15; revised 2026-05-15 after critical review: status corrected, decisions internalised, table-refs contradiction resolved (now consistent: tables are boundary-only), parser injection added, fixture-size budget relaxed to match reality, OCR-PDF fixture deferred behind ASSUMED-equivalence, dependency-add steps grounded in actual `pyproject.toml` layout, acceptance test fixed. Companion to the proposal at [`./2026-05-15-docling-native-rst.md`](./2026-05-15-docling-native-rst.md).*
