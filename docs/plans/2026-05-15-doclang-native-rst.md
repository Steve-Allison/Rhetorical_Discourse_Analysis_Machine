# DocLang-native RST output

**Status:** Phase 0 in progress (spec verified; design open)
**Date:** 2026-05-15
**Driver:** Steve Allison
**Companion:** [`2026-05-15-docling-native-rst.md`](./2026-05-15-docling-native-rst.md) (the Docling JSON entry point that already exists)
**Sibling memory:** [[verified-doclang-spec]] — file:line citations against `doclang-project/doclang` `main`.

---

## Goal

Add `isanlp_rst.doclang.parse_doclang(path)` as a first-class entry point alongside `parse_docling`. **First-class** means: DocLang gets its own native data model, not synthetic Docling self_refs. Each format's output schema reflects its source idioms honestly.

## Verified facts driving the design

From reading the full DocLang 0.5 spec, the `doclang` Python package, and two real `.dclg.xml` fixtures (see [[verified-doclang-spec]] for line citations):

1. **DocLang is XML** (`.dclg.xml`), namespace optional with default `https://www.doclang.ai/ns/v0`. Root `<doclang>`.
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

## DocLang-native addressing scheme

DocLang has no stable identifiers in the spec. Our addressing must be reproducible from the parsed XML alone. Proposed:

- **Primary key: canonical XPath** — e.g. `/doclang[1]/heading[2]` or `/doclang[1]/text[7]`. Reproducible from the document order. Position predicates per tag name (XPath 1.0 style, 1-based).
- **Secondary key: `thread_id`** — when present, captured as a separate `thread_ids: tuple[int, ...]` field on the span (a fragment may belong to multiple threads — e.g. an outer container thread and an inner item thread per `spec.md:1893-1916`).

So a `DoclangHarvestSpan` carries both: XPath as the structural address, `thread_ids` for cross-fragment grouping.

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
    xpath: str                          # e.g. "/doclang[1]/text[3]"
    thread_ids: tuple[int, ...]         # empty tuple when no <thread> present
    text: str
    start: int
    end: int

@dataclass(frozen=True, slots=True)
class DoclangHarvestResult:
    full_text: str
    spans: tuple[DoclangHarvestSpan, ...]

@dataclass(frozen=True, slots=True)
class DoclangBoundary:
    id: str                             # e.g. "heading-3", "page-2", "group-1", "table-0"
    kind: str                           # heading | page | group | table | field_region | document
    label: str | None                   # heading text where applicable
    parent_xpath: str | None
    xpaths: tuple[str, ...]
    level: int | None = None            # for headings
    page_no: int | None = None          # for page boundaries

@dataclass(frozen=True, slots=True)
class DoclangRstRelation:
    id: int
    relation: str
    nuclearity: str
    nucleus_xpaths: tuple[str, ...]
    satellite_xpaths: tuple[str, ...]
    nucleus_thread_ids: tuple[int, ...]      # only those that carry a thread
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
    thread_ids: tuple[int, ...]
    depth: int

@dataclass(frozen=True, slots=True)
class DoclangRstResult:
    schema_name: str                    # "isanlp_rst_doclang"
    schema_version: str
    tool: str
    tool_version: str
    model_version: str
    inventory: str
    source: str
    source_origin: dict[str, Any]       # doclang version, head metadata, namespace
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
    Path("source.dclg.xml"),
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
    include_field_regions=False,        # ASSUMED off; consumers can opt in
    include_code_blocks=False,          # ASSUMED off; code is not prose
    include_formulas=False,             # ASSUMED off; LaTeX is not prose
    harvest_separator="\n\n",
    # Overlap rule
    note_threshold=0.90,
    # Validation
    validate_xml=True,                  # call doclang.validate before parsing; raise on invalid
    max_harvest_chars=200_000,
)
```

## Open design questions

The following each need a verified answer before writing code. Marked `ASSUMED` per the no-assumptions rule:

1. **`<list>` granularity** — does each list item become a separate harvest span (granular: relations per item) or does the whole `<list>` become one span (coarser)? ASSUMED per-item. Verification: open a real fixture, eyeball whether RST on a per-item list reads sensibly.
2. **`<code>` and `<formula>` inclusion** — ASSUMED excluded as not-prose. Verification needed: run a small experiment with a fixture that has both, decide whether including them as opaque tokens helps or hurts RST quality.
3. **XPath dialect** — XPath 1.0 with positional predicates (`/doclang[1]/heading[2]`) per element name. ASSUMED reproducible across runs since position is determined by document order. Verify with `lxml.etree.ElementTree.getpath(elem)` to make sure the library's canonical path matches.
4. **Namespace handling** — DocLang fixtures may or may not declare the namespace. Our XPath generation must work in both cases. ASSUMED: pass through whatever the source uses; produce namespaceless XPath when source has none, namespaced XPath when source declares.
5. **Virtual text addressing** — list items / table cells without explicit `<text>` wrappers don't have their own element. ASSUMED: synthesise an XPath using the parent + position, e.g. `/doclang[1]/list[1]/ldiv[2]/.text()`. Verify against `lxml`'s text-node addressing semantics.
6. **`<thread>` semantics on cross-page continuations** — should a relation whose nucleus is in two thread fragments emit both thread_ids? ASSUMED yes (union).

## Phase plan

### Phase 0 — Verification (this commit)

- ✅ Read DocLang spec.md in full (3734 lines).
- ✅ Read `doclang` package source — verified validator-only API.
- ✅ Inspect at least two real `.dclg.xml` fixtures.
- ✅ Write [[verified-doclang-spec]] with file:line citations.
- ✅ Write this plan doc.

### Phase 1 — Fixture set + design verification (next session)

- Build fixture set under `tests/fixtures/doclang/`. Candidates from the official repo's `tests/data/valid/`:
  - `doclang_example.dclg.xml` (2.4 KB) — real fragment with table, picture, list, code, heading
  - `ok_comprehensive.dclg.xml` (18.6 KB) — exercises 48 example shapes
  - At least one fixture each of: namespace-present and namespace-absent
  - ASSUMED: add fixtures with `<thread>` continuations (`ok_*.dclg.xml` fixtures may already include them; verify)
- Resolve the 6 open design questions via fixture inspection.
- Update this plan doc with verified answers.

### Phase 2 — Implementation

- Extract shared maths to `isanlp_rst/_rst_common/`.
- Implement `isanlp_rst/doclang/` mirroring the Docling module structure.
- Tests: `tests/test_doclang_harvester.py`, `..._boundaries.py`, `..._mapper.py`, `..._entry.py`.
- Add `lxml` to runtime deps if not already present (it IS in `pyproject.toml` already as a transitive — verify direct dep).

### Phase 3 — Docs

- README section.
- `docs/examples/doclang-native.md` (companion to `docling-native.md`).

## Risks

| Risk | Mitigation |
|---|---|
| DocLang v0.5 is breaking-change territory (any `0.x.y` minor bump can break us per `spec.md:236-241`). | Pin a specific `doclang` package version; track changelog. |
| `lxml.etree.ElementTree.getpath()` may produce surprising XPath for elements with namespaces. | Phase 1 fixture verification confirms before Phase 2. |
| RST quality on DocLang-rendered prose is the same open question as for Docling (see [[open-rst-real-world-quality]]) — additionally, OTSL tables and code blocks inline within `<text>` may degrade the harvest signal. | Same empirical-quality-check pattern as `parse_docling`. |
| Fragment continuation via `<thread>` makes harvest spans non-contiguous in the source document but contiguous in our text concatenation. The mapper's overlap rule still works on offsets, but `boundary_memberships` may need to handle a relation whose nucleus is split across two `<thread>` fragments in different `page-N` boundaries. | Phase 1 inspection of a `<thread>`-bearing fixture clarifies. |

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
