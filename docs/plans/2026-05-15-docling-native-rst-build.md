# Docling-native RST output — build plan

**Status:** Ready to start (pending Phase 0 verification)
**Date:** 2026-05-15
**Driver:** Steve Allison
**Proposal:** [`./2026-05-15-docling-native-rst.md`](./2026-05-15-docling-native-rst.md)
**Estimated effort:** 1–3 days of focused work

---

## Goal

Ship a new public entry point `isanlp_rst.docling.parse_docling(path)` that accepts a Docling JSON file and emits RST relations indexed by `self_ref` instead of character offsets, per the approved proposal at the link above.

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

### Phase 0 — Verify the `docling-core` contract (no code)

**Why:** the whole design hangs on `docling-core` exposing a canonical, stable iteration API. Verify before writing the harvester.

**Verifications:**

- Confirm `DoclingDocument.iterate_items()` (or equivalent) exists and is part of the documented public surface, not internal.
- Confirm the iteration order is deterministic and documented.
- Enumerate the text-carrying node types: `TextItem`, `SectionHeaderItem`, `ListItem`, `PictureItem.captions`, `TableItem.data.grid[].text`. Pin to the version in this fork's pixi env.
- Load a real Docling source (e.g. one from CSM's corpus) and print `(self_ref, text_preview)` in canonical order — eyeball it for sanity.

**Output:** a short addendum at the bottom of this build plan recording the verified API surface and version pin.

**Success criterion:** the harvester can be implemented as a single `for item in doc.iterate_items(): ...` loop with no node-type-specific drilling.

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
- **Fixtures:** one small Docling JSON fixture committed under `tests/fixtures/docling/` (chosen to be < 100 KB and free of sensitive content). Golden harvest text recorded alongside it.

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| `docling-core` iteration is not actually stable / public | Phase 0 verifies; if not, vendor a small canonical traversal here, pinned per `docling-core` version. |
| EDU boundaries chronically straddle Docling spans | Overlap rule + note field already handle this; if note rates exceed ~30% in practice, revisit threshold. |
| Performance: large Docling sources cause RST OOM | Out of scope for v1; document the limit. RST parsing on multi-MB text is already a known limitation upstream. |
| Schema collision with CSM's existing consumer | CSM has not yet shipped the consumer; the field shape is additive. Coordinate the cutover with one CSM session after v1 ships. |

## Out of scope (v1)

- **Cue-awareness.** Notes-vs-body candidate relations, table-skipping, picture-description anchoring — all per the proposal's "Optional — Docling-cue awareness (later phase)" section. Don't do this in v1.
- **Upstream PR to `tchewik/isanlp_rst`.** Per the fork's CLAUDE.md.
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

1. Phase 0: verify `docling-core` iteration API + node-type coverage + version pin.
2. Resolve the three open questions above.
3. Phase 1: harvester + schema + their tests.
4. Phase 2: mapper + tests.
5. Phase 3: orchestrator + entry + integration test.
6. Phase 4: docs.
7. Cut a fork release (tag) so CSM has a pinable reference for its cutover.

Each phase has its own success criterion above. No phase counts as done until its tests pass; no phase starts until the prior phase's success criterion is met.

## Phase 0 verification log

*(populate during Phase 0)*

- `docling-core` version pinned: TBD
- Canonical iteration API: TBD
- Text-carrying node types confirmed: TBD
- Sample Docling source eyeball-checked: TBD

---

*Generated 2026-05-15. Companion to the proposal at [`./2026-05-15-docling-native-rst.md`](./2026-05-15-docling-native-rst.md).*
