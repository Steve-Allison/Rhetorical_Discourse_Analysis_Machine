# Docling-native RST output — walkthrough

`isanlp_rst.docling.parse_docling()` turns a Docling JSON file into a flat
list of RST relations and EDUs, each indexed by Docling `self_ref` and
annotated with the structural boundaries (slide / section / turn / table)
its content touches. This walkthrough covers the common usage patterns.

## Quick start

```python
from pathlib import Path
from isanlp_rst.docling import parse_docling

result = parse_docling(Path("deck.docling.json"), device="auto")

print(f"{len(result.edus)} EDUs, {len(result.relations)} relations, {len(result.boundaries)} boundaries")
print(f"source: {result.source}, mimetype: {result.source_origin.get('mimetype')}")
```

`result` is a `DoclingRstResult` — a frozen dataclass. Its main attributes:

| Field | Type | Notes |
| :--- | :--- | :--- |
| `relations` | `tuple[RstRelation, ...]` | pre-order DFS; relation 0 is the tree root. |
| `edus` | `tuple[RstEdu, ...]` | left-to-right reading order. |
| `boundaries` | `tuple[Boundary, ...]` | slides / sections / turns / tables + a `document` fallback. |
| `source_origin` | `dict[str, Any]` | `doc.origin.model_dump()` — mimetype, binary_hash, filename. |
| `schema_name`, `schema_version` | `str` | `"isanlp_rst_docling"` / `"1.1"`. |
| `tool_version` | `str` | `git describe` when in a checkout; package version when installed; `"unknown"` otherwise. |

## Batch parsing — inject one Parser

Constructing a `Parser` reloads ~2 GB of weights. For batch use, build one
and inject it:

```python
from isanlp_rst.parser import Parser
from isanlp_rst.docling import parse_docling

parser = Parser(hf_model_version="gumrrg", device="auto")

results = [parse_docling(p, parser=parser) for p in Path("corpus").glob("*.docling.json")]
```

The injected parser is reused for every call. Model knobs
(`hf_model_name`, `hf_model_version`, `relinventory`, `device`) are
ignored when `parser` is supplied — they only apply when `parse_docling`
constructs its own.

## Tuning the harvest

```python
result = parse_docling(
    "doc.docling.json",
    include_picture_descriptions=True,  # picture.meta.description.text where present
    include_slide_notes=True,  # ContentLayer.NOTES (PPTX speaker notes)
    include_furniture=False,  # ContentLayer.FURNITURE (PDF page headers / footers)
    harvest_separator="\n\n",  # inserted between spans
    coalesce_speaker_turns=True,  # VTT only
    note_threshold=0.90,  # ratio that triggers RstRelation.note
    max_harvest_chars=200_000,  # raises InputTooLargeError above this
)
```

## Group relations by boundary

`Boundary.self_refs` lists the `self_refs` belonging to a boundary;
`RstRelation.boundary_memberships` lists the ids of boundaries the
relation touches. Combine the two for per-slide / per-section views.

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

A relation may span two boundaries (e.g. a cross-slide narrative arc).
Filter on `len(boundary_memberships) == 1` to keep only within-boundary
relations:

```python
within = [r for r in result.relations if len(r.boundary_memberships) == 1]
cross = [r for r in result.relations if len(r.boundary_memberships) > 1]

print(f"within-boundary: {len(within)} relations")
print(f"cross-boundary:  {len(cross)} relations  ← typically slide-to-slide / section-to-section arcs")
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
        print(f"{indent}EDU {node.id}: {node.self_refs}")


walk(root.id)
```

## Errors to expect

| Exception | When | Mitigation |
| :--- | :--- | :--- |
| `EmptyDoclingError` | The loaded `DoclingDocument.body.children` is empty. | The Docling JSON has no body content — re-run Docling conversion. |
| `EmptyHarvestError` | Harvest produced no text (tables-only document, or all content layers filtered out). | Loosen the harvest knobs, or accept that this document has no prose to parse. |
| `InputTooLargeError` | `len(harvest.full_text) > max_harvest_chars`. | Chunk upstream, raise the limit, or split by section. |
| `ValueError` | `device` string isn't `"auto" / "cpu" / "mps" / "cuda" / "cuda:N"`. | Use one of the supported forms. |

All errors derive from `DoclingRstError`. Catch broadly with that base
class when you want to handle docling-specific failures uniformly.

## Table analyses (two-level)

Per the 2026-06-12 cross-format directive (Option 2), each `TableItem`
gets its own RST mini-parse in `result.table_analyses` — cells never
enter the main document harvest, so table discourse cannot distort the
document tree. Cell `self_ref`s are **real JSON pointers**
(`#/tables/N/data/table_cells/M`) that resolve mechanically against the
source document; the table's own `#/tables/N` remains a synthetic
boundary marker that no `HarvestSpan` carries. The `table-N` boundary's
`self_refs` is `(#/tables/N, <cell pointers>)`.

```python
result = parse_docling("doc.docling.json")  # analyses on by default
for analysis in result.table_analyses:
    print(analysis.id, len(analysis.edus), "cell EDUs")
```

Each cell span carries `kind` (`table_cell` / `table_header_cell`) and
`row_idx` / `col_idx` from `TableCell`. Set `include_table_cells=False`
to skip the analyses entirely (boundaries still emit).

Other spans carry `kind` from the Docling item label
(`"section_header"`, `"text"`, `"list_item"`, `"picture_description"`,
…), so consumers can classify content without re-opening the source.

## What's intentionally excluded

- **CLI entry point.** Python API only for now.
- **Streaming / async.** Synchronous only.
- **Custom relation taxonomies.** The RST model's emitted labels are
  relayed verbatim — switch models via `hf_model_version` to change the
  taxonomy.
- **Embedding outputs.** Out of scope; layer separately.

For the full design rationale see
[`docs/plans/2026-05-15-docling-native-rst.md`](../plans/2026-05-15-docling-native-rst.md)
and its companion build plan.
