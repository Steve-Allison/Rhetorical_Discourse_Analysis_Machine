# Docling-native RST output — build plan

**Status:** Ready to start (Phase 0 mostly complete; see § Phase 0 verification log)
**Date:** 2026-05-15
**Driver:** Steve Allison
**Proposal:** [`./2026-05-15-docling-native-rst.md`](./2026-05-15-docling-native-rst.md)
**Estimated effort:** 1–3 days of focused work
**Target consumers:** consumer-agnostic; any tool wanting RST relations on `DoclingDocument`-shaped input.

---

## Goal

Ship a new public entry point `isanlp_rst.docling.parse_docling(path)` that accepts a Docling JSON file and emits RST relations indexed by `self_ref` instead of character offsets, per the approved proposal at the link above. Consumer-agnostic.

## Verified facts (post-investigation)

Investigated 2026-05-15 against `docling-core` `main` and a real-world Docling JSON corpus across pptx / pdf / vtt / html-markdown source formats. Key facts the design relies on:

- **Loader:** `DoclingDocument.load_from_json(filename: Union[str, Path]) -> DoclingDocument` — `docling_core/types/doc/document.py:5778`.
- **Walker:** `DoclingDocument.iterate_items(root=None, with_groups=False, traverse_pictures=False, page_no=None, included_content_layers=None) -> Iterable[tuple[NodeItem, int]]` — `document.py:5535`. Pre-order DFS through `body.children`, resolves `$ref` references via `child_ref.resolve(self)`, yields `(NodeItem, depth)` tuples.
- **Default filter:** `DEFAULT_CONTENT_LAYERS = {ContentLayer.BODY}` — `document.py:1291`. Page headers, footers, slide masters, and other furniture-layer content are excluded by default.
- **Schema:** all inspected sources emit `DoclingDocument` v1.10.0 with uniform top-level shape (`body`, `furniture`, `groups`, `texts`, `pictures`, `tables`, `pages`, `origin`, …). Source-format differences are which fields are *populated*, not which fields *exist*.
- **`.texts[]` order ≠ canonical reading order.** Must walk via `body.children`. `iterate_items()` does this; rolling our own walker reinvents the wheel.
- **`origin.binary_hash`** is already present in every Docling input — consumers wanting a source-cache key use it directly.

## Dependencies

This entry point adds **one** new runtime dependency:

- **`docling-core`** — pure Python + Pydantic. Used for `DoclingDocument` loading, validation, and canonical iteration. Added to `pyproject.toml` (runtime) and `pixi.toml` (locked env). Version pin: TBD during Phase 0 (use latest stable; record in verification log).

No other new dependencies.

## Architecture

```text
parse_docling(path)
  ├─→ HarvestResult = harvest_docling_text(path)
  │     ├─→ load DoclingDocument from path (docling-core)
  │     ├─→ iterate canonically; yield (text, self_ref) per text-carrying node
  │     ├─→ concatenate texts with a chosen separator
  │     └─→ return (full_text, [HarvestSpan(text, start, end, self_ref)])
  │
  ├─→ rst_tree = Parser(...).parse(full_text)
  │     (uses the existing isanlp_rst.Parser facade unchanged)
  │
  └─→ relations = map_tree_to_refs(rst_tree, harvest_spans)
        ├─→ flatten the tree into structured nodes (relation, nuclearity, start, end)
        ├─→ for each node: compute overlap with harvest spans
        ├─→ produce RstRelation with nucleus_refs / satellite_refs and optional note
        └─→ return list[RstRelation]

return DoclingRstResult(metadata, relations)
```

## Module structure

```text
isanlp_rst/docling/
  __init__.py          # exports: parse_docling, DoclingRstResult
  harvester.py         # harvest_docling_text(), HarvestSpan, HarvestResult
  mapper.py            # map_tree_to_refs(), compute_overlap_refs()
  schema.py            # DoclingRstResult, RstRelation (typed dataclasses)
  _entry.py            # parse_docling() orchestrator
```

No new top-level files; everything lives in `isanlp_rst/docling/`. The existing `Parser` facade is reused unchanged.

## Public API

```python
from pathlib import Path
from isanlp_rst.docling import parse_docling, DoclingRstResult

result: DoclingRstResult = parse_docling(
    Path("source.docling.json"),
    hf_model_name="tchewik/isanlp_rst_v3",
    hf_model_version="gumrrg",
    cuda_device=-1,
)
```

Defaults match the existing `Parser` defaults so the call shape is familiar.

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
class RstRelation:
    relation: str                  # e.g. "Elaboration"
    nuclearity: str                # "NS" / "NN" / ""
    nucleus_refs: tuple[str, ...]
    satellite_refs: tuple[str, ...]
    depth: int
    note: str | None = None        # populated only for lopsided overlaps

@dataclass(frozen=True, slots=True)
class DoclingRstResult:
    schema_name: str               # "isanlp_rst_docling"
    schema_version: str            # "1.0"
    tool: str                      # "isanlp_rst"
    tool_version: str              # fork commit hash
    model_version: str             # e.g. "gumrrg"
    inventory: str                 # e.g. "eng.rst.rstdt"
    source: str                    # input path
    harvest_hash: str | None       # optional; see Open Questions
    relations: tuple[RstRelation, ...]
```

Frozen dataclasses with `slots=True` for value semantics and lower memory. Native exception propagation; no `Result[T, E]`, no defensive returns. Serialise via stdlib `json` after converting to dicts.

## Output schema (canonical form)

Identical to the proposal's "Output shape" section (with `docling_binary_hash` removed; `harvest_hash` optional per Open Questions).

## Implementation phases

### Phase 0 — Finalise the `docling-core` contract (mostly complete)

The big questions (does the walker exist? is it canonical? does it filter furniture? does the schema unify across source formats?) are answered in § Verified facts. Remaining Phase 0 work:

- **Pin `docling-core` version.** Pick the latest stable; record in the verification log below. Confirm v1.10.0 schema compatibility with the picked version.
- **Build the fixture set.** Commit one small Docling JSON per source flavour under `tests/fixtures/docling/`: pptx, pdf, vtt, markdown/html. Each < 100 KB, free of sensitive content. Source these by re-running Docling on small public-domain inputs, or by anonymising / trimming existing samples — do not commit corpus material from other projects without review.
- **Smoke-iterate.** Write a 10-line throwaway script that loads each fixture with `DoclingDocument.load_from_json` and prints `(self_ref, text_preview)` for each item yielded by `iterate_items()` with defaults. Eyeball the output: order looks canonical, no surprises, all text-carrying items reachable.

**Output:** populate § Phase 0 verification log.

**Success criterion:** harvester can be implemented as a single `for item, depth in doc.iterate_items(): ...` loop with no node-type-specific drilling; fixtures committed and load cleanly.

### Phase 1 — Harvester + schema

**Files:** `harvester.py`, `schema.py`.

**Implementation:**

- `harvest_docling_text(path: Path) -> HarvestResult` using the verified iteration API.
- `HarvestSpan`, `HarvestResult`, `DoclingRstResult`, `RstRelation` typed dataclasses in `schema.py`.

**Tests:** `tests/test_docling_harvester.py`

- **Round-trip:** for a fixture Docling source, concatenated harvest matches a recorded golden text.
- **Self-ref coverage:** every `self_ref` in the source appears in `HarvestResult.spans` exactly once (or is explicitly excluded by node-type policy).
- **Determinism:** harvesting the same source twice produces byte-identical `full_text`.
- **Offsets are consistent:** `full_text[span.start:span.end] == span.text` for every span.

**Success criterion:** all four tests pass; harvester delegates to `docling-core` iteration with no custom drilling.

### Phase 2 — Mapper

**Files:** `mapper.py`.

**Implementation:**

- `compute_overlap_refs(start: int, end: int, spans: tuple[HarvestSpan, ...]) -> tuple[tuple[str, ...], str | None]` — returns the list of `self_ref`s overlapping `[start, end]` (any non-empty intersection) plus an optional note when one span dominates ≥ 90%.
- `map_tree_to_refs(rst_tree, harvest_spans) -> tuple[RstRelation, ...]` — flattens the tree and produces `RstRelation`s.

**Tests:** `tests/test_docling_mapper.py`

- **Exact match:** range coincides with one span → single ref, no note.
- **Cross-boundary, even split:** 50/50 across two spans → both refs, no note.
- **Cross-boundary, lopsided:** 92/8 → both refs + note describing 8% spill.
- **Three-span span:** 30/40/30 across three → all three refs, no note.
- **Threshold edge:** 89% vs 90% vs 91% — verify the rule fires only at ≥ 90%.
- **Edge of document:** range at offset 0 or `len(full_text)` — verify no off-by-one.

**Success criterion:** all six tests pass; `compute_overlap_refs` is a pure function (no I/O, no model dependency); the 90% threshold is a named module-level constant.

### Phase 3 — Orchestrator + entry

**Files:** `_entry.py`, `__init__.py`.

**Implementation:**

- `parse_docling(path, ...)` orchestrates harvester → existing `Parser(...)` → mapper.
- `__init__.py` exports `parse_docling`, `DoclingRstResult`.

**Tests:** `tests/test_docling_entry.py`

- **End-to-end smoke:** real Docling source → non-empty `DoclingRstResult` with at least one relation; every `self_ref` in relations is in the harvest.
- **Schema name/version stamped:** result carries `schema_name="isanlp_rst_docling"`, `schema_version="1.0"`.
- **Path handling:** `Path` and `str` inputs both work.

**Success criterion:** smoke test passes against a real Docling sample; output passes a JSON schema check (if we add one).

### Phase 4 — Docs

**Files:** `README.md` (small new section), `docs/examples/` (optional usage example).

**Implementation:**

- Add a "Docling-native output" section to `README.md` with the public API and a short example.
- Drop a usage example in `docs/examples/docling-native.md` if useful.

**Success criterion:** README example runs verbatim against a real Docling source.

## Testing strategy

- **Unit:** harvester (Phase 1), mapper (Phase 2) — pure-function tests, fast, no model load.
- **Integration:** entry point (Phase 3) — slower, requires model download. Tag with `@pytest.mark.integration` so the nightly CI workflow picks it up.
- **Fixtures:** one small Docling JSON per source flavour committed under `tests/fixtures/docling/` (pptx, pdf, vtt, markdown). Each < 100 KB and free of sensitive content. Golden harvest text recorded alongside each.

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| `docling-core` schema bumps from v1.10.0 to a breaking version mid-implementation | Hard-pin the dependency. Track the changelog; reassess at each upstream release. The walker API is well-established and unlikely to break in patch/minor versions. |
| EDU boundaries chronically straddle Docling spans | Overlap rule + note field already handle this; if `note` field rates exceed ~30% in practice on a representative corpus, revisit the 90% threshold or the harvester separator. |
| Performance: large Docling sources cause RST OOM | Out of scope for v1; document the practical input-size limit. RST parsing on multi-MB text is a known upstream limitation. |
| Source-format-specific edge cases (e.g. empty `pages` map, missing `prov`, table-only documents) | Format-coverage tests in Phase 1 (one fixture per pptx/pdf/vtt/markdown flavour) catch this; `iterate_items()` already abstracts most source-format variance. |

## Out of scope (v1)

- **Cue-awareness.** Notes-vs-body candidate relations, table-skipping, picture-description anchoring — all per the proposal's "Optional — Docling-cue awareness (later phase)" section. Don't do this in v1.
- **Contributing back to `tchewik/isanlp_rst`** (Elena's original repo). This is Steve's project; sending work back to Elena's repo is not the default workflow and would only happen if Steve specifically asks.
- **CLI entry point.** Python API only in v1. Add later if needed.
- **Streaming / async API.** Synchronous only.
- **Embeddings.** Separate scaffold layer.

## Open questions to close before Phase 1

1. **`harvest_hash` field on the output:** include for reproducibility testing, or rely on `tool_version` + `model_version` + `source` to imply determinism? Default lean: include, SHA-256 of `full_text`.
2. **Separator between concatenated spans in the harvester:** `\n\n`, `\n`, or a sentinel like `\n<P>\n`? Affects how the existing parser segments. Default lean: `\n\n` (matches existing flat-text usage).
3. **Malformed source policy:** when `docling-core` iterates a node with `self_ref = None` or empty text, skip with a warning, or raise `MalformedDoclingError`? Default lean: raise (per the no-defensive-coding rule).

Resolve these in the session that starts Phase 1; do not let them block Phase 0.

## Acceptance test for the whole feature

```python
from pathlib import Path
from isanlp_rst.docling import parse_docling

result = parse_docling(
    Path("tests/fixtures/docling/sample.docling.json"),
    cuda_device=-1,
)

assert result.schema_name == "isanlp_rst_docling"
assert result.schema_version == "1.0"
assert len(result.relations) > 0

# every referenced self_ref must exist in the input
input_refs = load_self_refs_from_docling("tests/fixtures/docling/sample.docling.json")
for relation in result.relations:
    for ref in (*relation.nucleus_refs, *relation.satellite_refs):
        assert ref in input_refs, f"unknown self_ref: {ref}"
```

## Phase sequencing

1. Phase 0: pin `docling-core` version + build fixture set (pptx/pdf/vtt/markdown) + smoke-iterate.
2. Resolve the three open questions above.
3. Phase 1: harvester + schema + their tests (incl. format-coverage tests on all four fixtures).
4. Phase 2: mapper + tests.
5. Phase 3: orchestrator + entry + integration test.
6. Phase 4: docs.
7. Cut a fork release (tag) so downstream consumers have a pinable reference.

Each phase has its own success criterion above. No phase counts as done until its tests pass; no phase starts until the prior phase's success criterion is met.

## Phase 0 verification log

**Investigated 2026-05-15** against `docling-core` `main` and the Docling JSON corpus at `/Users/steveallison/AI_Projects+Code/Content_Structuring_Machine/project/sources/`.

- **Canonical iteration API confirmed:** `DoclingDocument.iterate_items(...)` at `docling_core/types/doc/document.py:5535`. Pre-order DFS through `body.children`; resolves `$ref` via `child_ref.resolve(self)`. Yields `(NodeItem, depth)` tuples.
- **Loader confirmed:** `DoclingDocument.load_from_json(filename)` at `document.py:5778`.
- **Default filter confirmed:** `DEFAULT_CONTENT_LAYERS = {ContentLayer.BODY}` (document.py:1291). Furniture-layer items (page headers/footers, slide masters) excluded automatically.
- **Schema uniformity confirmed:** five Docling JSONs across four source formats (pptx / pdf / vtt / html-markdown) all emit `DoclingDocument` v1.10.0 with identical top-level shape. Differences are populated-vs-empty fields, not structural.
- **Text-carrying node types observed:** `TextItem` (with subclass-level labels `text`, `section_header`, `list_item`, `title`, `page_footer`). `PictureItem.captions` carries `$ref`s to text items (skipped by default; `traverse_pictures=False`). `TableItem.data.grid[].text` is cell-level content (not yielded by `iterate_items`; v2 concern).
- **`origin.binary_hash`** is already a field in every Docling input JSON — consumers needing a source-cache key use it directly.

**Outstanding Phase 0 work:**

- Pick and commit `docling-core` version pin (latest stable as of implementation start).
- Build and commit the four fixture files under `tests/fixtures/docling/`.
- Run the smoke-iterate script on each fixture; record any surprises here.

---

*Generated 2026-05-15. Companion to the proposal at [`./2026-05-15-docling-native-rst.md`](./2026-05-15-docling-native-rst.md).*
