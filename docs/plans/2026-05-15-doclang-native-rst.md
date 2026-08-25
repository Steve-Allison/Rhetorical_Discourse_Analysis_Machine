# DocLang-native RST output

**Status:** Phase 2 complete (modules + tests landed; lint + pyright clean); Phase 3 ready. Phase 9 (2026-06-12) added per-cell `<table>` harvest — see Revision below.
**Date:** 2026-05-15 (Phase 0); 2026-06-10 (Phases 1 + 2); 2026-06-12 (cross-format table-cell directive)
**Driver:** Steve Allison
**Companion:** [`2026-05-15-docling-native-rst.md`](./2026-05-15-docling-native-rst.md) (the Docling JSON entry point that already exists); [`2026-06-12-markdown-native-rst.md`](./2026-06-12-markdown-native-rst.md) (the markdown-native entry point and source of the cross-format directive).
**Sibling memories:** [[verified-doclang-spec]] (spec citations); [[verified-doclang-fixtures]] (fixture-evidence for the answers below).

---

## Revision — 2026-06-12 (two-level table analysis, Option 2)

`<table>` content is fully analysed without polluting the document tree. Cells are EXCLUDED from the main harvest; each `<table>` gets its own RST mini-parse whose relations/edus land in `DoclangRstResult.table_analyses` (id matches the `table-N` boundary). Cells are addressed by their marker xpath (`<ched/>` / `<fcel/>` / `<rhed/>` / `<corn/>`) and carry `kind` + `row_idx`/`col_idx` grid positions; `<ecel/>` (empty) and the span-continuation markers (`<lcel/>` / `<ucel/>` / `<xcel/>`) occupy grid columns and terminate the previous cell's text but never yield spans; `<nl/>` delimits rows. `<index>` / `<tabular>` remain boundary-only. Knob `include_table_cells: bool = True` toggles the per-table analyses.

Same change set: **thread-aware joins** — main-harvest spans sharing a `thread_id` with their predecessor join with a single space instead of the paragraph separator (a `<thread>` marks paragraph continuation across page breaks; a hard break mid-paragraph made the segmenter split one sentence in two). Plus `dtype` pass-through, `device="auto"` CPU fallback, optional `cache_dir` result cache, and the shared `_rst_common` flatten (iterative) / overlap (bisect) machinery. Driven by Steve's "analyse EVERYTHING" directive; the markdown plan ([`2026-06-12-markdown-native-rst.md`](./2026-06-12-markdown-native-rst.md)) is the cross-format anchor.

## Goal

Add `isanlp_rst.doclang.parse_doclang(path)` as a first-class entry point alongside `parse_docling`. **First-class** means: DocLang gets its own native data model, not synthetic Docling self_refs. Each format's output schema reflects its source idioms honestly.

## Verified facts driving the design

From reading the full DocLang 0.5 spec, the `doclang` Python package, and two real `.dclg` fixtures (see [[verified-doclang-spec]] for line citations):

1. **DocLang is XML** (`.dclg`), namespace optional with default `https://www.doclang.ai/ns/v0`. Root `<doclang>`.
2. **The `doclang` PyPI package is validator-only.** It exposes `validate(path)` and `ValidationError`. No DOM, no parser, no object model. We parse XML ourselves (`lxml` is already in our deps).
3. **No stable per-element identifiers.** `thread_id` exists only for fragment continuation (cross-page/cross-column linking), not for unique element identity. All `<thread>` instances sharing a thread_id MUST be under the same host element type.
4. **`<layer value="...">` has three values**: `body`, `background`, `furniture` (default `body`). **No `notes` layer.** No equivalent of Docling's `ContentLayer.NOTES`.
5. **No slide concept in the spec.** `<group>` is the only generic container. PPTX-via-DocLang loses slide structure.
6. **Pages via `<page_break/>`** empty-element markers (only allowed as child of `<doclang>`).
7. **Sections via `<heading level="N">`** — positive integer, no upper bound.
8. **Tables use OTSL inline cell tokens** (`<fcel/>`, `<ched/>`, `<rhed/>`, `<lcel/>`, `<ucel/>`, `<xcel/>`, `<nl/>`, …) inline within `<table>` body. Different from Docling's separate `TableItem` blocks.
9. **`<picture>`** carries `<src uri="...">`; no `meta.description` equivalent. Captions live in the element head as `<caption>`.
10. **Virtual `<text>`**: `<list>` items and `<table>` cells can contain raw text without an explicit `<text>` wrapper.
11. **`<head>` is schema-free in v0.5.** Producer-chosen children. Rich metadata (`<title>`, `<author>`, governance) is Appendix C future work.

## Architectural principles

### Two first-class formats, two honest schemas, no coercion

`parse_docling(path)` keeps its existing `DoclingRstResult` schema (with `self_ref` strings everywhere). `parse_doclang(path)` produces a separate `DoclangRstResult` whose addressing is **DocLang-native**, not Docling-shaped.

### Shared internal utilities

The overlap-rule maths and the tree-flatten skeleton in `isanlp_rst/docling/mapper.py` are format-agnostic — they only care about character ranges and span->string mappings. Extract them to `isanlp_rst/_rst_common/` (private) so the DocLang module can reuse them.

The `Parser` facade itself is shared as-is — RST is RST regardless of source.

### Module layout

```text
isanlp_rst/
  docling/        # existing — DoclingDocument.load_from_json → DoclingRstResult
  doclang/        # new      — DocLang XML loader              → DoclangRstResult
  _rst_common/    # new private — shared overlap-rule maths + tree-flatten skeleton
```

## DocLang-native addressing scheme — VERIFIED

DocLang has no stable identifiers in the spec. Our addressing must be reproducible from the parsed XML alone.

**Primary key: local-name canonical XPath** — e.g. `/doclang[1]/heading[2]`, `/doclang[1]/text[7]`. Each step is `local_name[i]` where `i` is the 1-based position among siblings sharing the same local name. Namespaces are stripped.

This is **not** `lxml.etree.ElementTree.getpath()`. We confirmed in Phase 1 that `getpath()` produces `/*/*[3]`-style wildcard paths on default-namespaced documents (the spec-recommended shape per [`spec.md:219-241`](https://github.com/doclang-project/doclang/blob/main/spec.md#L219-L241)) — unusable as a human-readable identifier. We build the path ourselves: a one-screen `local_path(el)` function, round-trips 464 / 464 elements on [`ok_comprehensive.dclg`](../../tests/fixtures/doclang/ok_comprehensive.dclg), 4 / 4 on [`ok_no_namespace.dclg`](../../tests/fixtures/doclang/ok_no_namespace.dclg). All paths unique within a document. See [[verified-doclang-fixtures]] item 1.

**Secondary key: `thread_id`** — when present, captured as `thread_id: int | None` on the span. Phase 1 confirmed that across the then-current valid-fixture corpus, every host element has **exactly one** `<thread>` child (5 hosts in total). The element-head ordering at [`spec.md:147-157`](https://github.com/doclang-project/doclang/blob/main/spec.md#L147-L157) specifies `<thread>` as a single optional slot, and the corpus matches. Schema simplified from `tuple[int, ...]` to `int | None`.

## DocLang-native boundary kinds

Boundary detection on DocLang reflects what the spec actually models:

| Boundary kind | Detection rule |
|---|---|
| `heading-N` | Each `<heading>` opens a new section boundary, indexed in document order. `level` attribute (default 1) preserved on the boundary. |
| `page-N` | Content between successive `<page_break/>` markers. First boundary covers pre-break content. |
| `group-N` | Each top-level (or near-top-level) `<group>` is its own boundary. Nested groups become nested-id boundaries (`group-N-M`). |
| `table-N` | Each `<table>` is one boundary. Cell content excluded from harvest (parallel to Docling tables-as-boundary policy). |
| `field_region-N` | Each `<field_region>` is one boundary. Field-internal text (keys/values) excluded from RST harvest. |
| `document` | Fallback — entire body when no other boundary kinds apply. |

NOT detected (because DocLang doesn't model them):

- `slide-N` / `slide-N-notes` — DocLang has no slide concept.
- `turn-N` — DocLang has no speaker/turn concept.

This is **honest divergence** from Docling's boundary set. Consumers that need slide/turn boundaries should use `parse_docling` on Docling JSON.

## Harvest policy

Walk the parsed XML tree in document order, emitting one `DoclangHarvestSpan` per text-bearing element. Filter on `<layer value="...">` (element-head property) per knobs:

- `<text>` → harvest text content (excluding any inline children that are also separately harvested)
- `<heading>` → harvest text content; also opens a section boundary
- `<list>` items (virtual text or `<text>` wrapper) → harvest each item; whole `<list>` is a single span unit OR each item separately (design decision below)
- `<formula>` → ASSUMED skipped from RST harvest (LaTeX is structurally distinct prose)
- `<code>` → ASSUMED skipped from RST harvest (code is not natural-language prose)
- `<picture>` → harvest `<caption>` text if present and `include_picture_captions=True`
- `<table>` → SKIPPED from harvest (boundary-only); table cell text is not added
- `<field_region>` → SKIPPED from harvest (boundary-only); key/value text is structurally distinct from prose
- `<page_header>`, `<page_footer>` → SKIPPED unless `include_furniture=True`

Filter by `<layer>`:

- `body` → always (default `BODY` layer)
- `background` → opt-in via `include_background` (rare)
- `furniture` → opt-in via `include_furniture` (default off)

## Schema (proposed)

```python
@dataclass(frozen=True, slots=True)
class DoclangHarvestSpan:
    xpath: str  # e.g. "/doclang[1]/text[3]" — local-name canonical
    thread_id: int | None  # None when host has no <thread> (most spans)
    layer: str  # "body" | "background" | "furniture"
    text: str
    start: int
    end: int


@dataclass(frozen=True, slots=True)
class DoclangHarvestResult:
    full_text: str
    spans: tuple[DoclangHarvestSpan, ...]


@dataclass(frozen=True, slots=True)
class DoclangBoundary:
    id: str  # e.g. "heading-3", "page-2", "group-1", "table-0"
    kind: str  # heading | page | group | table | field_region | document
    label: str | None  # heading text where applicable
    parent_xpath: str | None
    xpaths: tuple[str, ...]
    level: int | None = None  # for headings
    page_no: int | None = None  # for page boundaries


@dataclass(frozen=True, slots=True)
class DoclangRstRelation:
    id: int
    relation: str
    nuclearity: str
    nucleus_xpaths: tuple[str, ...]
    satellite_xpaths: tuple[str, ...]
    nucleus_thread_ids: tuple[int, ...]  # only those nucleus spans carrying a thread (deduplicated)
    satellite_thread_ids: tuple[int, ...]
    depth: int
    left_id: int
    right_id: int
    boundary_memberships: tuple[str, ...]
    note: str | None = None


@dataclass(frozen=True, slots=True)
class DoclangRstEdu:
    id: int
    xpaths: tuple[str, ...]
    thread_ids: tuple[int, ...]  # only spans carrying a thread
    depth: int


@dataclass(frozen=True, slots=True)
class DoclangRstResult:
    schema_name: str  # "isanlp_rst_doclang"
    schema_version: str
    tool: str
    tool_version: str
    model_version: str
    inventory: str
    source: str
    source_origin: dict[str, Any]  # doclang version, head metadata, namespace
    boundaries: tuple[DoclangBoundary, ...]
    relations: tuple[DoclangRstRelation, ...]
    edus: tuple[DoclangRstEdu, ...]
```

Consumers distinguish the two outputs via `schema_name` (`isanlp_rst_docling` vs `isanlp_rst_doclang`) and the type itself.

## Public API

```python
from pathlib import Path
from isanlp_rst.doclang import parse_doclang, DoclangRstResult

result: DoclangRstResult = parse_doclang(
    Path("source.dclg"),
    # Model selection (same as parse_docling)
    parser=None,
    hf_model_name="tchewik/isanlp_rst_v3",
    hf_model_version="gumrrg",
    relinventory=None,
    device="auto",
    # Harvest policy (DocLang-specific)
    include_picture_captions=True,
    include_background=False,
    include_furniture=False,
    include_field_regions=False,  # ASSUMED off; consumers can opt in
    include_code_blocks=False,  # ASSUMED off; code is not prose
    include_formulas=False,  # ASSUMED off; LaTeX is not prose
    harvest_separator="\n\n",
    # Overlap rule
    note_threshold=0.90,
    # Validation
    validate_xml=True,  # call doclang.validate before parsing; raise on invalid
    max_harvest_chars=200_000,
)
```

## Design questions — RESOLVED in Phase 1

All six questions were verified against the then-current valid-fixture corpus pulled into [`tests/fixtures/doclang/`](../../tests/fixtures/doclang/). Evidence per question lives in [[verified-doclang-fixtures]].

1. **`<list>` granularity** — **RESOLVED: per-item.** 30 lists across the corpus; 2 nested-list cases at depth 1 (`<list>` whose ancestor is `<list>`, not nested via `<ldiv>`). Each `<ldiv/>` marker produces one harvest span; nested lists are harvested independently at their own XPath. Evidence: `ok_list_with_unwrapped_text.dclg`, `ok_comprehensive.dclg`.
2. **`<code>` and `<formula>` inclusion** — **RESOLVED: default OFF, both knobs preserved.** 3 `<formula>` blocks in the corpus, all pure LaTeX (`E = mc^2`, `x = \frac{-b \pm \sqrt{b^{2} - 4ac}}{2a}`). 12 `<code>` blocks across R / Python / SQL / Java — bulk is source code, a minority is mixed-prose-with-`<bold>` markup. Default-off is correct for both; `include_code_blocks` / `include_formulas` knobs handle the opt-in cases.
3. **XPath dialect** — **RESOLVED: local-name canonical path, NOT `lxml.getpath()`.** Verified `lxml.etree.ElementTree.getpath()` emits `/*/*[N]` wildcards on default-namespaced documents. Our own `local_path(el)` walker produces `/doclang[1]/heading[2]`-style paths that round-trip 100% across all 464 elements of `ok_comprehensive.dclg`.
4. **Namespace handling** — **RESOLVED: transparent.** Local-name path is identical regardless of whether the source declares `xmlns`. No per-format dialect, no per-format knob.
5. **Virtual text addressing** — **RESOLVED: marker XPath is the address.** `<ldiv/>` / `<fcel/>` / `<ched/>` are self-closing markers whose item / cell content lives in the marker's `.tail` plus the `itertext()` and `.tail` of intervening siblings up to the next marker. The item / cell IS the marker; its XPath is the marker's own XPath. No synthetic text-node addressing needed.
6. **`<thread>` semantics** — **RESOLVED: 1 thread per host (max).** Verified across all 40 fixtures: every host element with a `<thread>` carries exactly one. The element-head ordering at [`spec.md:147-157`](https://github.com/doclang-project/doclang/blob/main/spec.md#L147-L157) defines a single optional slot. Schema simplified to `thread_id: int | None`. For relations whose nucleus straddles two thread-carrying spans, the relation's `nucleus_thread_ids` is the deduplicated tuple of those spans' thread ids — a union over span-level scalars, not per-span tuples.

## Phase plan

### Phase 0 — Verification (this commit)

- ✅ Read DocLang spec.md in full (3734 lines).
- ✅ Read `doclang` package source — verified validator-only API.
- ✅ Inspect at least two real `.dclg` fixtures.
- ✅ Write [[verified-doclang-spec]] with file:line citations.
- ✅ Write this plan doc.

### Phase 1 — Fixture set + design verification (2026-06-10)

- ✅ Mirrored the then-current valid fixtures from `doclang-project/doclang/tests/data/valid` into [`tests/fixtures/doclang/`](../../tests/fixtures/doclang/) with provenance README.
- ✅ Resolved Q1–Q6 against the corpus; updated the addressing-scheme and schema sections above.
- ✅ Wrote [[verified-doclang-fixtures]] with reproducer commands and fixture:line citations.
- ✅ Updated this plan doc with verified answers.

### Phase 2 — Implementation (2026-06-10)

- ✅ Extracted shared overlap maths and nuclearity split into [`isanlp_rst/_rst_common/`](../../isanlp_rst/_rst_common/). Refactored [`isanlp_rst/docling/mapper.py`](../../isanlp_rst/docling/mapper.py) to delegate to the shared helpers while preserving its public API (all 183 prior Docling tests still pass).
- ✅ Implemented [`isanlp_rst/doclang/`](../../isanlp_rst/doclang/) — `schema`, `errors`, `loader`, `harvester`, `boundaries`, `mapper`, `_entry`, `__init__`.
- ✅ Added [`types-lxml`](https://pypi.org/project/types-lxml/) as a dev dependency (lxml is already direct via `pyproject.toml`).
- ✅ Wrote 115 new tests across 5 files: `tests/test_doclang_loader.py` (15), `_harvester.py` (31), `_boundaries.py` (25), `_mapper.py` (14), `_entry.py` (30 fast + 6 slow integration). Total test count: 298 fast + 48 slow.
- ✅ Updated `tool.pyright.include` with the new module dirs.
- Lint clean (ruff). Pyright clean (strict). Slow integration tests behind `@pytest.mark.slow` so they don't run on every commit.

### Phase 3 — Docs

- README section.
- `docs/examples/doclang-native.md` (companion to `docling-native.md`).

## Risks

| Risk | Mitigation |
|---|---|
| DocLang v0.5 is breaking-change territory (any `0.x.y` minor bump can break us per `spec.md:236-241`). | Pin a specific `doclang` package version; track changelog. |
| ~~`lxml.etree.ElementTree.getpath()` may produce surprising XPath for elements with namespaces.~~ | **Retired by Phase 1**: `getpath()` is unusable on namespaced docs (`/*/*[3]`-style wildcards); we own a `local_path()` walker that round-trips 100% on the corpus. |
| RST quality on DocLang-rendered prose is the same open question as for Docling (see [[open-rst-real-world-quality]]) — additionally, OTSL tables and code blocks inline within `<text>` may degrade the harvest signal. | Same empirical-quality-check pattern as `parse_docling`. |
| Fragment continuation via `<thread>` makes harvest spans non-contiguous in the source document but contiguous in our text concatenation. The mapper's overlap rule still works on offsets, but `boundary_memberships` may need to handle a relation whose nucleus is split across two `<thread>` fragments in different `page-N` boundaries. | Phase 1 confirmed shape (`ok_thread.dclg` shows two `<text>` hosts sharing `thread_id=1`). Phase 2 mapper assigns spans to all `page-N` boundaries whose page-range contains their character offsets; the union of those memberships shows up in `relation.boundary_memberships` naturally. |

## Out of scope

- Round-trip conversion (RST output back to DocLang XML).
- DocLang 1.x compatibility (does not exist yet).
- Slide / speaker-turn boundaries — DocLang does not model these.
- Rich governance metadata extraction from `<head>` (Appendix C future).
- `<index>` and `<field_region>` content harvest into RST (boundary-only by design).

## Companion notes

- The Docling-native pattern is documented in [`2026-05-15-docling-native-rst.md`](./2026-05-15-docling-native-rst.md) and [`2026-05-15-docling-native-rst-build.md`](./2026-05-15-docling-native-rst-build.md).
- The no-assumptions rule (`.claude/rules/no-assumptions.md`) applies in full — any claim in this doc not backed by a `spec.md:N` citation or by reading a verified-source artefact must be marked `ASSUMED`.

Related memory: [[verified-doclang-spec]], [[verified-docling-core-api]], [[decision-one-tree-per-document]], [[decision-consumer-agnostic]], [[open-rst-real-world-quality]].
