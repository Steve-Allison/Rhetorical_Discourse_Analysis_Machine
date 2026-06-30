# Markdown-native RST output — walkthrough

`isanlp_rst.markdown.parse_markdown()` turns a `.md` file directly into a
flat list of RST relations and EDUs, each indexed by a stable
`#/blocks/N` reference and annotated with the structural boundaries
(section / table / code_block / document) its content touches. Tables
are analysed **two-level**: each table gets its own RST mini-parse in
`result.table_analyses`, so table discourse never distorts the document
tree. This walkthrough covers the common usage patterns.

## Quick start

```python
from pathlib import Path
from isanlp_rst.markdown import parse_markdown

result = parse_markdown(Path("design-notes.md"), device="auto")

print(f"{len(result.edus)} EDUs, {len(result.relations)} relations, "
      f"{len(result.boundaries)} boundaries, "
      f"{len(result.table_analyses)} table analyses")
```

`result` is a `MarkdownRstResult` — a frozen dataclass. Its main attributes:

| Field | Type | Notes |
| :--- | :--- | :--- |
| `relations` | `tuple[RstRelation, ...]` | document tree, pre-order DFS; relation 0 is the root. Never references table content. |
| `edus` | `tuple[RstEdu, ...]` | left-to-right reading order. |
| `table_analyses` | `tuple[TableAnalysis, ...]` | one RST mini-parse per table; `id` matches the `table-T` boundary; ids local per analysis. |
| `boundaries` | `tuple[Boundary, ...]` | sections / tables / code blocks + a `document` fallback. |
| `source_origin` | `dict[str, Any]` | `{format, gfm, front_matter, front_matter_format}` — raw YAML front-matter text preserved. |
| `schema_name`, `schema_version` | `str` | Always `"isanlp_rst_markdown"` / `"1.0"` for now. |
| `tool_version` | `str` | `git describe` when in a checkout; package version when installed; `"unknown"` otherwise. |

Serialise with `result.to_dict()` (JSON-shaped plain data) or
`result.to_json()`.

## Batch parsing — inject one Parser, add a cache

Constructing a `Parser` reloads ~2 GB of weights. For batch use, build
one and inject it; add `cache_dir=` so unchanged sources are never
re-parsed:

```python
from isanlp_rst.parser import Parser
from isanlp_rst.markdown import parse_markdown

parser = Parser(hf_model_version="gumrrg", device="auto")

results = [
    parse_markdown(p, parser=parser, cache_dir=".rst-cache")
    for p in Path("docs").rglob("*.md")
]
```

The cache key covers the source bytes, model identity, and every knob —
a changed file or knob re-parses; an unchanged one loads from disk
without touching the model. Model knobs (`hf_model_name`,
`hf_model_version`, `relinventory`, `device`, `dtype`) apply only when
`parse_markdown` constructs its own parser.

## Tuning the harvest

Defaults are "analyse everything":

```python
result = parse_markdown(
    "doc.md",
    gfm=True,                  # GFM tables + strikethrough (default on)
    include_blockquotes=True,  # gates ALL quoted constructs as one region
    include_table_cells=True,  # two-level table analysis (default on)
    include_code_blocks=True,  # fenced + indented (default on)
    include_html=True,         # raw HTML blocks, tags stripped to text
    harvest_separator="\n\n",
    note_threshold=0.90,       # ratio that triggers RstRelation.note
    max_harvest_chars=200_000, # checked for main + each table harvest
    device="auto",             # GPU when torch reports one, else CPU
    dtype=None,                # "bf16" / "fp16" mixed-precision override
)
```

`include_table_cells=False` drops the table analyses (and the `table-T`
boundaries — markdown boundaries derive from the harvests) — useful for
prose-only views.

## Working with table analyses

Each analysis is a self-contained mini-tree over one table's cells:

```python
for analysis in result.table_analyses:
    boundary = next(b for b in result.boundaries if b.id == analysis.id)
    print(f"{analysis.id}: {len(analysis.edus)} cell EDUs, "
          f"{len(analysis.relations)} relations")
    for edu in analysis.edus:
        print("  ", edu.block_refs)   # e.g. ('#/tables/0/cells/3',)
```

Cell refs (`#/tables/T/cells/K`) resolve against the table boundary's
`block_refs`; `K` counts every grid position in row-major order
(including empty cells), so refs stay stable. The synthetic
`#/tables/T` marker carries no harvest span and can never appear in any
relation.

## Front-matter

YAML front-matter (`---...---`) is stripped from the RST input and
surfaced as raw text (this is YAML-only — the front-matter plugin
supports no other delimiter):

```python
result = parse_markdown("post-with-front-matter.md")
print(result.source_origin)
# {'format': 'markdown', 'gfm': True,
#  'front_matter': 'title: Design notes\nauthor: Steve\n',
#  'front_matter_format': 'yaml'}

# Parse the YAML yourself if you need it (no PyYAML dep in this package):
import yaml
meta = yaml.safe_load(result.source_origin['front_matter'])
```

## Group relations by boundary

`Boundary.block_refs` lists the refs belonging to a boundary;
`RstRelation.boundary_memberships` lists the ids of boundaries the
relation touches:

```python
from collections import defaultdict

per_boundary = defaultdict(list)
for relation in result.relations:
    for bid in relation.boundary_memberships:
        per_boundary[bid].append(relation)

for boundary in result.boundaries:
    rels = per_boundary[boundary.id]
    print(f"{boundary.id} ({boundary.kind}, level={boundary.level}): "
          f"{len(rels)} relations touch this boundary")
```

## Reconstruct the tree

`relations` and `edus` share a single id namespace. Every relation's
`left_id` and `right_id` resolves into one or the other:

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
        print(f"{indent}EDU {node.id}: {node.block_refs}")

walk(root.id)
```

The same pattern applies inside each `TableAnalysis` (its ids are local
to that analysis).

## Addressing scheme

| Construct | `kind` | Address | Boundary membership |
| :--- | :--- | :--- | :--- |
| heading | `"heading"` | `#/blocks/N` | section it opens |
| paragraph | `"paragraph"` | `#/blocks/N` | enclosing section |
| list item | `"list_item"` | `#/blocks/N` | enclosing section |
| quoted paragraph | `"blockquote_paragraph"` | `#/blocks/N` | enclosing section |
| quoted heading | `"blockquote_heading"` | `#/blocks/N` | enclosing section (never opens one) |
| code block | `"code_block"` | `#/blocks/N` | enclosing section + `code_block-N` |
| HTML block (stripped) | `"html_block"` | `#/blocks/N` | enclosing section |
| table cell | `"table_cell"` / `"table_header_cell"` | `#/tables/T/cells/K` | `table-T` only |
| table marker | (no span) | `#/tables/T` | `table-T` only |

Image alt text flattens into the parent block's text — inline content,
like emphasis.

## Errors to expect

| Exception | When | Mitigation |
| :--- | :--- | :--- |
| `EmptyMarkdownError` | The source has only whitespace or only front-matter — no body tokens. | The file has no content; nothing to parse. |
| `EmptyHarvestError` | Body tokens existed but neither the main harvest nor any table harvest produced text. | Loosen the knobs or accept the document has no harvestable content. |
| `InputTooLargeError` | The main harvest or a table harvest exceeds `max_harvest_chars`. | Chunk upstream, raise the limit, or split by section. |
| `ValueError` | `device` string isn't `"auto" / "cpu" / "mps" / "cuda" / "cuda:N"`. | Use one of the supported forms. |

All errors derive from `MarkdownRstError`. A table-only document is
valid: the main tree is empty (`relations == ()`), the content lives in
`table_analyses`.

## What's intentionally excluded

- **MyST / Pandoc / custom dialects.** Only CommonMark + GFM tables and
  strikethrough.
- **TOML / JSON front-matter.** YAML delimiters only.
- **Front-matter parsing.** Raw text only.
- **CLI entry point.** Python API only (see `pixi run rst-diag` for
  corpus diagnostics).
- **Streaming / async.** Synchronous only.

For the full design rationale see
[`docs/plans/2026-06-12-markdown-native-rst.md`](../plans/2026-06-12-markdown-native-rst.md).
