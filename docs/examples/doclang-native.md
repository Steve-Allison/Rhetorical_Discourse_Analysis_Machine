# DocLang-native RST output — walkthrough

`isanlp_rst.doclang.parse_doclang()` turns a DocLang `.dclg.xml`
file into a flat list of RST relations and EDUs, each indexed by a
DocLang-native local-name XPath and annotated with the structural
boundaries (heading / page / group / table / field_region) its content
touches. This is the **DocLang twin** of [`parse_docling`](./docling-native.md);
both are first-class entry points with honestly different schemas — no
coercion of one shape into the other.

## Quick start

```python
from pathlib import Path
from isanlp_rst.doclang import parse_doclang

result = parse_doclang(Path("document.dclg.xml"), device="auto")

print(f"{len(result.edus)} EDUs, {len(result.relations)} relations, "
      f"{len(result.boundaries)} boundaries")
print(f"source: {result.source}, namespace: {result.source_origin['namespace']}")
```

`result` is a `DoclangRstResult` — a frozen dataclass. Its main attributes:

| Field | Type | Notes |
| :--- | :--- | :--- |
| `relations` | `tuple[RstRelation, ...]` | pre-order DFS; relation 0 is the tree root. |
| `edus` | `tuple[RstEdu, ...]` | left-to-right reading order. |
| `boundaries` | `tuple[Boundary, ...]` | headings / pages / groups / tables / field_regions, with a `document` fallback. |
| `source_origin` | `dict[str, Any]` | `{"format": "doclang", "namespace": ..., "version": ..., "head_children": [...]}`. |
| `schema_name`, `schema_version` | `str` | Always `"isanlp_rst_doclang"` / `"1.0"` for now. |
| `tool_version` | `str` | `git describe` when in a checkout; package version when installed; `"unknown"` otherwise. |

## How addresses work — local-name canonical XPath

Every harvested span, EDU, and relation carries an `xpath` (or
`*_xpaths`) of the form `"/doclang[1]/heading[2]/text[1]"`. The walker
that generates these paths uses 1-based position predicates per local
name and strips XML namespaces — so a document with
`xmlns="https://www.doclang.ai/ns/v0"` (the spec-recommended shape) and
a document without any `xmlns` produce identical addresses. The paths
are unique within a document and round-trip back to their elements via
plain sibling-position resolution.

> **Why not `lxml.etree.ElementTree.getpath()`?** On default-namespaced
> documents `getpath()` emits `/*/*[3]`-style wildcards because XPath 1.0
> has no concept of default namespaces. The local-name path is
> namespace-agnostic and human-readable. Verified Phase 1 against the
> then-40 upstream valid fixtures (464 elements in the comprehensive fixture
> alone, 100% round-trip). Remirror 2026-08-16 is 42 files.

## Batch parsing — inject one Parser

Constructing a `Parser` reloads ~2 GB of weights. For batch use, build
one and inject it:

```python
from isanlp_rst.parser import Parser
from isanlp_rst.doclang import parse_doclang

parser = Parser(hf_model_version="gumrrg", device="auto")

results = [
    parse_doclang(p, parser=parser)
    for p in Path("corpus").glob("*.dclg.xml")
]
```

The injected parser is reused for every call. Model knobs
(`hf_model_name`, `hf_model_version`, `relinventory`, `device`) are
ignored when `parser` is supplied — they only apply when `parse_doclang`
constructs its own.

## Tuning the harvest

```python
result = parse_doclang(
    "doc.dclg.xml",
    include_picture_captions=True,   # <picture><caption>...</caption>
    include_background=False,        # <layer value="background"/>
    include_furniture=False,         # <layer value="furniture"/> +
                                     # <page_header> / <page_footer>
    include_field_regions=False,     # <field_region> body
    include_code_blocks=False,       # <code> blocks (source code; not prose)
    include_formulas=False,          # <formula> blocks (LaTeX; not prose)
    harvest_separator="\n\n",        # inserted between spans
    note_threshold=0.90,             # ratio that triggers RstRelation.note
    validate_xml=True,               # gate the file through doclang.validate
    max_harvest_chars=200_000,       # raises InputTooLargeError above this
)
```

`validate_xml=True` (default) runs the file through the official
`doclang` PyPI package's `validate(path)` function before parsing. The
`doclang` package is validator-only (no DOM) — we parse with `lxml`
ourselves. If `doclang` is not importable in the active environment,
validation is silently skipped.

## Boundary kinds

DocLang doesn't model slides or speaker turns — neither concept exists
in the spec. The boundary set reflects what DocLang **does** model:

| Boundary kind | Detection rule |
|---|---|
| `heading-N` | Each `<heading level="N">` opens a `heading-N` boundary, in document order. `label` carries the heading text; `level` carries the attribute (default 1). |
| `page-N` | Content between successive `<page_break/>` markers (only allowed as children of `<doclang>`). The first boundary covers pre-break content. |
| `group-N` | Each top-level `<group>`. A nested group becomes `group-N-M` (one level of nesting). |
| `table-N` | Each `<table>` — cells are excluded from the prose harvest. |
| `field_region-N` | Each `<field_region>` — by default field content is excluded from prose. |
| `document` | Fallback covering all harvest-eligible xpaths when no structural boundary applies. |

There is no `slide-N` / `slide-N-notes` / `turn-N` — those exist in
`parse_docling`'s schema because Docling JSON models them. DocLang
doesn't. If you have PPTX or VTT input, use `parse_docling`.

## What `<thread>` means in the output

DocLang's `<thread thread_id="N"/>` is the **fragment-continuation**
primitive: two `<text>` elements with the same `thread_id` represent
two physical fragments of one logical paragraph (typically spanning a
`<page_break/>`). Each `HarvestSpan` carries `thread_id: int | None`
(at most one `<thread>` per host per spec). Each `RstRelation` /
`RstEdu` aggregates the deduplicated thread ids of its constituent
spans:

```python
for relation in result.relations:
    if relation.nucleus_thread_ids:
        print(f"{relation.relation}: nucleus spans threads "
              f"{relation.nucleus_thread_ids}")
```

A relation whose nucleus spans a page break will show
`nucleus_thread_ids=(1,)` and `boundary_memberships=("page-0", "page-1")`
together — the relation crosses pages but the spans share a single
logical thread.

## Group relations by boundary

```python
from collections import defaultdict

per_boundary = defaultdict(list)
for relation in result.relations:
    for bid in relation.boundary_memberships:
        per_boundary[bid].append(relation)

for boundary in result.boundaries:
    rels = per_boundary[boundary.id]
    print(f"{boundary.id} ({boundary.kind}): {len(rels)} relations touch this boundary")
```

## Filter for within-boundary relations only

```python
within = [r for r in result.relations if len(r.boundary_memberships) == 1]
cross  = [r for r in result.relations if len(r.boundary_memberships) >  1]

print(f"within-boundary: {len(within)} relations")
print(f"cross-boundary:  {len(cross)} relations  ← typically heading-to-heading "
      "arcs or thread-continuation across page breaks")
```

## Reconstruct the tree

`relations` and `edus` share a single id namespace. Every relation's
`left_id` and `right_id` resolves into one or the other. Build a
node-lookup dict and walk from the root:

```python
nodes = {r.id: r for r in result.relations}
nodes.update({e.id: e for e in result.edus})

root = result.relations[0]  # relations[] is pre-order DFS — root first

def walk(node_id: int, depth: int = 0) -> None:
    node = nodes[node_id]
    indent = "  " * depth
    if hasattr(node, "relation"):  # RstRelation
        print(f"{indent}{node.relation} [{node.nuclearity}]  ← {node.boundary_memberships}")
        walk(node.left_id, depth + 1)
        walk(node.right_id, depth + 1)
    else:  # RstEdu
        print(f"{indent}EDU {node.id}: {node.xpaths}")

walk(root.id)
```

## Errors to expect

| Exception | When | Mitigation |
| :--- | :--- | :--- |
| `InvalidDoclangError` | `validate_xml=True` and the file failed `doclang.validate(path)`. | Inspect `.__cause__` for the upstream `ValidationError` — its `.xsd_errors` and `.schematron_errors` localise the problem. |
| `EmptyDoclangError` | The root `<doclang>` has no body content (or only `<head>`). | The XML has no body — check the producer. |
| `EmptyHarvestError` | Harvest produced no text (table-only document, or all eligible content excluded by knobs). | Loosen the knobs (`include_code_blocks`, `include_field_regions`, …) or accept that this document has no prose to parse. |
| `InputTooLargeError` | `len(harvest.full_text) > max_harvest_chars`. | Chunk upstream, raise the limit, or split by heading. |
| `ValueError` | `device` string isn't `"auto" / "cpu" / "mps" / "cuda" / "cuda:N"`, or a `<heading>` has a non-integer `level`. | Use one of the supported device forms; fix the producer's heading attribute. |

All errors except `ValueError` derive from `DoclangRstError`. Catch
broadly with that base class when you want to handle DocLang-specific
failures uniformly.

## Table analyses (two-level)

Per the 2026-06-12 cross-format directive (Option 2), each `<table>`
gets its own RST mini-parse in `result.table_analyses` — cells never
enter the main document harvest, so table discourse cannot distort the
document tree. Cells are addressed by the cell marker's xpath (e.g.
`/doclang[1]/table[1]/ched[1]` for a column header,
`/doclang[1]/table[1]/fcel[3]` for a body cell) and carry `kind` plus
`row_idx` / `col_idx` grid positions. `<ecel/>` (empty by grammar) and
the span-continuation markers (`<lcel/>` / `<ucel/>` / `<xcel/>`)
occupy grid columns but never yield spans; `<nl/>` delimits rows. The
`table-N` boundary's `xpaths` is `(table_xpath, <cell marker xpaths>)`;
the table xpath itself is the synthetic boundary marker and carries no
harvest span.

```python
result = parse_doclang("doc.dclg.xml")              # analyses on by default
for analysis in result.table_analyses:
    print(analysis.id, len(analysis.edus), "cell EDUs")
```

Set `include_table_cells=False` to skip the analyses entirely
(boundaries still emit). `<index>` and `<tabular>` remain boundary-only
in either mode — they're rare in the Phase 1 corpus and use different
internal grammars.

## Thread-aware joins

Main-harvest spans sharing a `thread_id` with their predecessor join
with a single space instead of the paragraph separator: a `<thread>`
marks paragraph continuation across page breaks, and a hard break
mid-paragraph would make the segmenter split one sentence in two. A
table-only document is valid: the main tree is empty, the content lives
in `table_analyses`.

## What's intentionally excluded

- **Slide and speaker-turn boundaries.** DocLang doesn't model slides
  or speaker turns — for PPTX or VTT input, use `parse_docling` on
  Docling JSON.
- **Field content.** `<field_region>` content stays boundary-only
  unless `include_field_regions=True` — key/value form data is
  structurally distinct from prose. (`<table>` cells now harvest by
  default — see § Table cells.)
- **`<code>` and `<formula>` by default.** `<code>` is source code (R,
  Python, SQL, …); `<formula>` is raw LaTeX. Neither is natural-language
  prose. Both are toggleable via `include_code_blocks=True` /
  `include_formulas=True`.
- **CLI entry point.** Python API only for now.
- **Streaming / async.** Synchronous only.
- **Round-trip back to DocLang XML.** Output is a flat data structure,
  not an editable DocLang tree.
- **Custom relation taxonomies.** The RST model's emitted labels are
  relayed verbatim — switch models via `hf_model_version` to change the
  taxonomy.

For the full design rationale and the Phase 0–2 verification chain see
[`docs/plans/2026-05-15-doclang-native-rst.md`](../plans/2026-05-15-doclang-native-rst.md)
and the project-memory at
[`.claude/memory/verified_doclang_spec.md`](../../.claude/memory/verified_doclang_spec.md)

+ [`.claude/memory/verified_doclang_fixtures.md`](../../.claude/memory/verified_doclang_fixtures.md).
