# Docling-native RST output

**Status:** Approved (one tree per Docling JSON; see § Revisions)
**Date:** 2026-05-15 (revised same day — one-tree architecture, no parse-per-boundary)
**Driver:** Steve Allison
**Target consumers:** any downstream tool requiring RST relations indexed by Docling `self_ref` — RAG knowledge-graph builders, document-summarisation pipelines, transcript discourse analysers, slide-deck rhetoric mappers, structured-doc Q&A systems.
**Estimated effort:** 3–5 days of focused work.

---

## Revisions

**2026-05-15 (revision 5 — one tree per Docling JSON, same day):** The parse-per-boundary architecture from revision 4 has been retired. We emit one `DiscourseUnit` tree per Docling JSON — the natural output of the `Parser` facade — with each tree node's offsets mapped to `self_ref`s via the overlap rule, and boundary metadata (slide / page / section / turn / table) layered on top as annotations on each relation.

Why this is better than parse-per-boundary:

- **Standard RST output shape.** Consumers of an RST parser expect a hierarchical tree, not a flat relations list under a fake document root.
- **Preserves hierarchical structure.** A relation contains sub-relations; that nesting is the whole point of RST.
- **Cross-boundary relations are preserved when meaningful** (a deck's narrative arc, a conversation's cross-turn elaboration, section-to-section discourse). Consumers can filter via `boundary_memberships` annotation if they don't want them.
- **One Parser call per document**, model load amortised naturally.

Open empirical question: how well does the parser handle long, structurally-diverse inputs? Sliding-window encoding (`tokenizer.model_max_length = 1e9`) suggests it's designed for long inputs, but worth verifying with realistic Docling-sized inputs in Phase 0.

**2026-05-15 (revision 4 — retired by revision 5):** Parse-per-boundary architecture proposed and then rejected on the same day after challenge from Steve. Output would have been a flat relations list under per-boundary RST trees. Issue: non-standard, loses hierarchical structure, discards potentially meaningful cross-boundary relations.

**2026-05-15 (revision 3):** Consumer-agnostic framing. No coupling to a specific downstream consumer.

**2026-05-15 (revision 2):** Three pre-implementation decisions:

- Harvester anchored on canonical `docling-core` spec.
- `docling_binary_hash` dropped from output (Docling JSON already carries `origin.binary_hash`).
- Overlap rule formalised: any non-empty intersection → include; `note` field for ≥ 90% lopsided overlaps.

Verified facts (now baked in):

- `docling-core.DoclingDocument.load_from_json(...)` loads + validates.
- `docling-core.DoclingDocument.iterate_items(...)` is the canonical walker (pre-order DFS, resolves `$ref`s, filters by `ContentLayer`, supports `page_no` filtering).
- All inspected Docling sources (pptx, pdf, vtt, html/markdown) emit `DoclingDocument` v1.10.0 with uniform top-level shape.
- `docling-core` is **not** currently a dependency of this fork.

Build plan: [`./2026-05-15-docling-native-rst-build.md`](./2026-05-15-docling-native-rst-build.md).

---

## Why this exists

Docling JSON is a portable, validated, source-format-agnostic representation of structured documents — PDFs, PPTX decks, VTT transcripts, Markdown, HTML. Every text-carrying node has a stable `self_ref` identifier (`#/texts/47`, `#/groups/3`, etc.), and the document schema (`DoclingDocument`) is the same regardless of source format.

`isanlp_rst` produces RST (Rhetorical Structure Theory) discourse analyses, but currently emits relations indexed by **character offsets** into a plain-text input. That is the wrong currency for any consumer working with Docling JSON: every such consumer has to invert the character-offset arithmetic against its own re-walk of the Docling structure to recover stable `self_ref` references.

Solve it once, here, by emitting an RST tree where every node references `self_ref`s directly. Anchor the implementation on `docling-core`'s canonical walker so the contract is the official library, not a hand-rolled convention. Layer boundary metadata (slide, page, section, turn, table) on top so consumers can group and filter by source structure.

## What we ship

A new entry point `isanlp_rst.docling.parse_docling(path)` that:

1. **Accepts** a path to a Docling JSON file directly.
2. **Walks** the loaded `DoclingDocument` via `docling-core.iterate_items(...)` with full cue awareness (section headers, slide notes, picture captions, all included).
3. **Concatenates** the harvested text into one input, recording `(self_ref, start, end)` for every span.
4. **Detects boundaries** appropriate to the source format and annotates each `self_ref` with its boundary memberships.
5. **Runs RST once** over the full harvested text via the existing `Parser` facade.
6. **Maps offsets to `self_ref`s** using the overlap rule on each tree node.
7. **Annotates each relation** with the boundaries its content spans.
8. **Emits** one `DoclingRstResult` — a single RST tree with boundary metadata, serialised to JSON.

## Supported source formats

Verified shapes (see [`verified_docling_schema`](../../.claude/memory/verified_docling_schema.md)):

| Source | Boundary detection |
|---|---|
| **PPTX** | one `slide-N` boundary per `groups[name=slide-N].label=chapter`; one `slide-N-notes` boundary per slide for `content_layer == "furniture"` items parented to the slide group. |
| **PDF** | one `section-N` boundary opened at each `TextItem` with `label == "section_header"`. Document-level `document` boundary covers any pre-header content. |
| **VTT** | one `turn-N` boundary per contiguous-same-speaker run (consecutive `TextItem`s sharing the same `source[*].voice`). |
| **HTML / Markdown** | same as PDF (`section_header` levels). If no section headers exist, the whole document is one `document` boundary. |
| **Tables** | each `TableItem` is its own `table-N` boundary; cell content is NOT included in the RST input text (see § Tables). |
| **OCR-PDFs** | `traverse_pictures=True` is the default, so layout-model-wrapped texts inside top-level `PictureItem`s enter the harvest and boundary detection works the same as PDF. |

Picture captions (separate from OCR-wrapped text) enter the harvest as regular text spans; their boundary membership is whatever boundary contains the picture's parent.

## Output shape

```json
{
  "schema_name": "isanlp_rst_docling",
  "schema_version": "1.0",
  "tool": "isanlp_rst",
  "tool_version": "<fork commit hash>",
  "model_version": "gumrrg",
  "inventory": "eng.rst.rstdt",
  "source": "foo.docling.json",
  "source_origin": {
    "mimetype": "application/vnd.ms-powerpoint",
    "binary_hash": 4387776670278522503,
    "filename": "deck.pptx"
  },
  "boundaries": [
    {
      "id": "slide-0",
      "kind": "slide",
      "label": "GenAI Creation",
      "parent_self_ref": "#/groups/0",
      "self_refs": ["#/texts/0", "#/texts/1"]
    },
    {
      "id": "slide-0-notes",
      "kind": "slide-notes",
      "label": null,
      "parent_self_ref": "#/groups/0",
      "self_refs": ["#/texts/42"]
    },
    {
      "id": "table-0",
      "kind": "table",
      "label": null,
      "parent_self_ref": "#/groups/1",
      "self_refs": ["#/tables/0"]
    }
  ],
  "relations": [
    {
      "id": 21,
      "relation": "Elaboration",
      "nuclearity": "NS",
      "nucleus_refs": ["#/texts/0"],
      "satellite_refs": ["#/texts/1"],
      "depth": 0,
      "left_id": 14,
      "right_id": 20,
      "boundary_memberships": ["slide-0"]
    },
    {
      "id": 99,
      "relation": "Background",
      "nuclearity": "NS",
      "nucleus_refs": ["#/texts/0"],
      "satellite_refs": ["#/texts/120"],
      "depth": 2,
      "left_id": 21,
      "right_id": 87,
      "boundary_memberships": ["slide-0", "slide-3"]
    }
  ],
  "edus": [
    {
      "id": 14,
      "self_refs": ["#/texts/0"],
      "depth": 1
    }
  ]
}
```

Key design points:

- **One flat `relations` list with `left_id` / `right_id`** preserves the full tree shape — consumers can reconstruct the hierarchy in one pass.
- **`edus` list** carries leaf-node identity so consumers can resolve EDU-level references (`left_id` / `right_id` of depth-bottom relations point into `edus[]`).
- **`boundary_memberships`** is the list of `boundaries[].id` values whose `self_refs` intersect the relation's nucleus or satellite refs. Single-element list when the relation is fully within one boundary; multi-element when it spans.
- **`boundaries` list is metadata** — it doesn't affect what RST relations are emitted, only annotates them.
- **`boundary.kind` is enumerated.** Currently: `"slide" | "slide-notes" | "page" | "section" | "turn" | "table" | "document"`. Extensible.
- **`source_origin`** preserves the Docling `origin` block so consumers don't have to re-open the source.
- **Overlap rule unchanged:** any non-empty intersection between a relation's char-range and a `self_ref`'s harvest range → include in `nucleus_refs` / `satellite_refs`. Lopsided ≥ 90% gets a `note` field (omitted from sample above for brevity).

## Architecture

```text
parse_docling(path, **knobs)
  │
  ├─→ doc = DoclingDocument.load_from_json(path)
  │
  ├─→ harvest = harvest_docling_text(doc, knobs)
  │     # walks iterate_items(); concatenates text; records (self_ref, start, end) spans
  │     # cue-aware: includes section headers, slide notes, picture captions per knobs
  │
  ├─→ boundaries = detect_boundaries(doc, harvest, knobs)
  │     # produces list of Boundary entries with id/kind/label/parent_self_ref/self_refs
  │     # source-format-aware: slides for pptx, sections for pdf, turns for vtt, etc.
  │     # tables emit boundary entries but their cells are NOT in `harvest.full_text`
  │
  ├─→ rst_tree = Parser(...).parse(harvest.full_text)
  │     # ONE Parser call; one DiscourseUnit tree
  │
  └─→ result = map_tree_to_refs(rst_tree, harvest, boundaries)
        # for each tree node: map node.start/end → self_refs via overlap rule
        # for each relation: compute boundary_memberships
        # flatten tree to relations[] + edus[]; preserve tree shape via left_id/right_id

  return DoclingRstResult(metadata, boundaries, relations, edus)
```

The `Parser(...)` facade is loaded once and called once per document. Boundary detection is independent of RST parsing — boundaries are derived from the Docling structure, the RST tree is derived from the harvested text. Boundary memberships are computed at the end by intersecting each relation's `self_refs` with each boundary's `self_refs`.

## Public API

```python
from pathlib import Path
from isanlp_rst.docling import parse_docling, DoclingRstResult

result: DoclingRstResult = parse_docling(
    Path("source.docling.json"),
    # Model selection
    hf_model_name: str = "tchewik/isanlp_rst_v3",
    hf_model_version: str = "gumrrg",
    relinventory: str | None = None,        # required for unirst
    # Device
    device: str = "auto",                   # "auto" | "cpu" | "cuda:N" | "mps"
    # Harvest policy (what enters the RST input text)
    include_picture_captions: bool = True,
    include_furniture: bool = False,
    harvest_separator: str = "\n\n",
    # Boundary policy (annotation only — doesn't affect RST input)
    coalesce_speaker_turns: bool = True,    # contiguous same-voice runs → one turn boundary
    # Overlap rule
    note_threshold: float = 0.90,
)
```

Every previously-hard-coded policy is now a parameter with a default. Table-cell text is structurally excluded from the harvest (not a parameter; see § Tables).

## Tables

Tables are structurally different from prose — a grid, not a flow. Running RST over flattened table cells produces relations that don't correspond to discourse phenomena, so:

- **Each `TableItem` is emitted as a `boundary` entry** with `kind: "table"` and `self_refs: ["#/tables/N"]`. Consumers know the table exists and where it sits in document structure.
- **Table cell text is NOT included in `harvest.full_text`.** No spurious RST relations are emitted for table-internal content.
- **The table's `self_ref`** may still appear in a relation's `nucleus_refs` / `satellite_refs` if the table-as-whole participates in document-level discourse (e.g. a paragraph "Elaboration"s a table). The relation refers to the table by its `self_ref`, not by its cells.

Cell-text harvesting is rejected because it would force a design choice (linearise cells in row-major vs column-major) that any choice is wrong for some tables.

## Cue-aware harvest specifics

For each source format, the harvest concatenates text from:

| Source | What's harvested | What's not |
|---|---|---|
| **PPTX** | slide body texts (titles + bodies), slide notes, picture captions within slides | table cells, furniture-layer items outside slide notes |
| **PDF** | body texts, section_header texts, list-item texts, picture captions | page headers/footers (furniture by default), table cells |
| **VTT** | every `TextItem` (single text label, single content layer) | n/a |
| **HTML / Markdown** | body texts, section_header texts, list-item texts | table cells |
| **OCR-PDF** | texts wrapped in top-level `PictureItem`s (via `traverse_pictures=True`) | n/a |

The `include_furniture` knob (default `False`) flips whether `content_layer == "furniture"` items are harvested. `include_picture_captions` (default `True`) controls `traverse_pictures` indirectly (we always pass `True` to access OCR-PDF text; the knob filters out non-OCR caption text downstream of iteration).

## Testing

Smoke tests:

1. **Round-trip:** every `self_ref` in `relations[].nucleus_refs` / `satellite_refs` exists in the source's `self_ref` set or the `boundaries[]` cell-ref extension.
2. **Reproducibility:** same source twice → byte-identical output (modulo `tool_version`).
3. **Tree completeness:** for every relation with `left_id != null`, the referenced id exists in `relations[]` or `edus[]`.
4. **Boundary completeness:** every boundary in `boundaries` has at least one `self_ref`.
5. **Boundary tagging:** every relation's `boundary_memberships` is non-empty, and every listed boundary id exists in `boundaries[]`.
6. **Format coverage:** one fixture per source flavour (pptx, pdf, vtt, markdown, OCR-PDF). Each parses without source-format special-casing in client code.
7. **Edge cases:** single-speaker VTT, table-heavy PPTX, multi-section PDF with `level: 2`+ subdivisions, document with no section headers (single `document` boundary), and a deliberately-long input (one of the larger Docling fixtures) to verify sliding-window behaviour.

## Out of scope

- **Parse-per-boundary architecture.** Considered and rejected (see Revisions).
- **Table cell-level RST.** Tables are structurally grids; RST is for prose.
- **Contributing back to `tchewik/isanlp_rst`** (Elena's original repo). Steve's project; not the default workflow.
- **Pedagogic / domain judgement.** RST is descriptive linguistics; we don't judge relevance / importance / pedagogic value.
- **Embedding outputs.** Separate scaffold layer.
- **Streaming / async API.** Synchronous only.
- **Custom relation taxonomies.** Whatever the RST model emits, we relay.

## Output contract for downstream consumers

The fork emits a single JSON object conforming to the schema above. Consumers:

- Read `schema_name` and `schema_version` to confirm format.
- Read `relations[]` as a flat list; walk `left_id` / `right_id` to reconstruct the tree if needed.
- Filter by `boundary_memberships` to scope analysis to specific slides / sections / turns.
- Cross-reference `self_ref`s against the original Docling source. `source_origin.binary_hash` is the cache-invalidation anchor.
- Treat the `note` field on relations as optional free-form caveat text.

The fork does NOT:

- Emit consumer-specific business logic, fields, or metadata.
- Make assumptions about how `self_ref` references will be used downstream.
- Coordinate with any specific consumer's data model.

---

*Last revised 2026-05-15 (one tree per Docling JSON; see revision 5). Build plan: [`./2026-05-15-docling-native-rst-build.md`](./2026-05-15-docling-native-rst-build.md).*
