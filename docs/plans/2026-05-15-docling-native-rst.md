# Docling-native RST output

**Status:** Approved (consumer-agnostic framing; see § Revisions)
**Date:** 2026-05-15 (revised same day — consumer-agnostic rewrite)
**Driver:** Steve Allison (fork owner)
**Target consumers:** any downstream tool requiring RST relations indexed by Docling `self_ref` — RAG knowledge-graph builders, document-summarisation pipelines, transcript discourse analysers, slide-deck rhetoric mappers, structured-doc Q&A systems.
**Estimated effort:** 1–3 days of focused work

---

## Revisions

**2026-05-15 (revision 3 — consumer-agnostic rewrite, same day):** Dropped the framing anchor that treated this work as scaffold for a specific consumer. Repositioned as a general-purpose entry point: "Docling JSON in → RST relations indexed by `self_ref` → out", agnostic to consumer. The "What X does in response" and "Coordination with X" sections were removed; consumer-side adaptation belongs in each consumer's docs, not here.

Verified facts now baked into the proposal (previously assumed):

- `docling-core` ships `DoclingDocument.load_from_json(path)` (loader, line 5778) and `DoclingDocument.iterate_items(...)` (canonical pre-order DFS walker, line 5535).
- The walker resolves `$ref` references via `child_ref.resolve(self)`, filters by `ContentLayer` (default `{ContentLayer.BODY}` excludes page headers/footers), supports `page_no` filtering, and yields `(NodeItem, depth)` tuples.
- All Docling sources inspected (pptx, pdf, vtt, html/markdown) emit schema `DoclingDocument` v1.10.0 with uniform top-level shape. Source-format differences are which fields are *populated*, not which fields *exist*.
- `.texts[]` flat-array ordering is **not** canonical reading order. The body-rooted tree walk is.
- `docling-core` is **not** currently a dependency of this fork; adding it is real new work in `pyproject.toml` + `pixi.toml`.

**2026-05-15 (revision 2 — same day as proposal):** Three pre-implementation decisions, now superseded in framing by revision 3 but retained in substance:

- Harvester anchored on the canonical `docling-core` spec.
- `docling_binary_hash` dropped from the output (the field `origin.binary_hash` already exists in every Docling JSON; consumers compute their own hash if they need one).
- Overlap rule formalised: any non-empty intersection → include; `note` field for ≥ 90% lopsided overlaps.

Build plan: [`./2026-05-15-docling-native-rst-build.md`](./2026-05-15-docling-native-rst-build.md).

---

## Why this exists

Docling JSON is a portable, validated, source-format-agnostic representation of structured documents — PDFs, PPTX decks, VTT transcripts, Markdown, HTML. Every text-carrying node has a stable `self_ref` identifier (`#/texts/47`, `#/groups/3`, etc.), and the document schema (`DoclingDocument`) is the same regardless of source format.

`isanlp_rst` produces RST (Rhetorical Structure Theory) discourse analyses, but currently emits relations indexed by **character offsets** into a plain-text input. That is the wrong currency for any consumer working with Docling JSON: every such consumer has to invert the character-offset arithmetic against its own re-walk of the Docling structure to recover stable `self_ref` references.

This is the **mapping problem**: brittle, repo-coupled, and identical for every consumer. Solve it once, here, by emitting RST relations indexed by `self_ref` directly. Anchor the implementation on `docling-core`'s canonical walker so the contract is the official library, not a hand-rolled convention.

## The current limitation

The parser works on plain text and emits relations indexed by character offsets:

```json
{
  "relation": "Elaboration",
  "nuclearity": "NS",
  "start": 0,
  "end": 7055,
  "depth": 0
}
```

Docling JSON identifies content by `self_ref`. To use this fork's RST output against a Docling source today, a consumer has to:

1. Concatenate text from the Docling source into a single string (in some defined order — body texts, picture captions, table cells, …).
2. Run this fork's parser on that concatenated string.
3. Match RST character offsets back to source `self_ref`s — requires re-walking Docling with a position-tracking harvester and inverting offset arithmetic.

Step 3 is brittle: any change to the harvest order or character-counting logic breaks the mapping. Owning step 3 inside this fork — anchored on `docling-core`'s canonical iteration — removes that brittleness for every consumer simultaneously.

## The proposal

Add a Docling-aware entry point that:

1. **Accepts** a path to a Docling JSON file (`*.docling.json`) directly.
2. **Walks** the loaded `DoclingDocument` via `docling-core`'s `iterate_items()` API, harvesting text spans with `self_ref` preserved.
3. **Runs** RST parsing against the harvested text using the existing `Parser` facade unchanged.
4. **Emits** RST relations indexed by `self_ref`, not by character offset.

### Supported source formats

Any source format that Docling can convert to `DoclingDocument`. Verified shapes:

- **PPTX** — slides live as `groups` (`name: "slide-0"`, `label: "chapter"`); text labels include `title`, `text`. Tables and pictures common.
- **PDF** — texts either direct children of `body` or wrapped in semantic groups (`name: "list"`); text labels include `section_header`, `list_item`, `text`, `page_footer`; texts carry `level` for header hierarchy; pictures via `pictures[]`.
- **VTT / transcripts** — flat list of text items; each carries `source.start_time` / `source.end_time` instead of `prov` / bbox; single text label.
- **HTML / Markdown** — variant of the PDF shape with empty `pages` if the source has no native paging.

Schema uniformity is what makes this clean: one walker handles all flavours. Source-format-specific traversal logic is **not required** because `docling-core` already abstracts it.

### Output shape

```json
{
  "schema_name": "isanlp_rst_docling",
  "schema_version": "1.0",
  "tool": "isanlp_rst",
  "tool_version": "<fork commit hash>",
  "model_version": "gumrrg",
  "inventory": "eng.rst.rstdt",
  "source": "foo.docling.json",
  "relations": [
    {
      "relation": "Elaboration",
      "nuclearity": "NS",
      "nucleus_refs": ["#/texts/47"],
      "satellite_refs": ["#/texts/48", "#/texts/49"],
      "depth": 0
    },
    {
      "relation": "Cause",
      "nuclearity": "NS",
      "nucleus_refs": ["#/texts/52"],
      "satellite_refs": ["#/texts/53"],
      "depth": 1
    }
  ]
}
```

Key differences from the existing plain-text output:

- `nucleus_refs` / `satellite_refs` are lists of `self_ref` strings, not character offsets.
- A relation may span multiple `self_ref`s when EDU boundaries don't align with Docling spans.
- `nuclearity` field unchanged (NS / NN / empty).
- `schema_name` and `schema_version` let downstream consumers detect this richer format and version it independently of the existing plain-text output.

### Why list-of-refs, not single-ref

`isanlp_rst` segments by EDU (elementary discourse unit), which doesn't always align with Docling text item boundaries. An EDU might be half of `#/texts/N` plus half of `#/texts/N+1`. Modelling: a relation says "this set of `self_ref`s is the nucleus" / "this set is the satellite" — both as lists. A single-ref shortcut would lose information at EDU/span boundary mismatches.

## What we add

### 1. New entry point

```python
from pathlib import Path
from isanlp_rst.docling import parse_docling

result = parse_docling(
    Path("source.docling.json"),
    hf_model_name="tchewik/isanlp_rst_v3",
    hf_model_version="gumrrg",
    cuda_device=-1,
)
```

Returns a typed result (see build plan for type definitions). Defaults match the existing `Parser(...)` facade so the call shape is familiar.

### 2. Canonical harvester (uses `docling-core.iterate_items`)

```python
def harvest_docling_text(path: Path) -> tuple[str, list[tuple[int, int, str]]]:
    """Returns (full_text, [(start, end, self_ref), ...]).

    Loads the document via DoclingDocument.load_from_json(path), then walks
    text-carrying items in canonical reading order using
    DoclingDocument.iterate_items() with the default content-layer filter
    ({ContentLayer.BODY}, which excludes page headers/footers).

    v1 traversal policy:
      - TextItem and its subclasses (SectionHeaderItem, ListItem, ...) -> harvested.
      - PictureItem.captions -> NOT traversed (traverse_pictures=False is the
        iterate_items() default).
      - TableItem cells -> NOT included; tables contribute their self_ref to
        the harvest but no text content. Cell-text harvesting is a v2 concern.
    """
```

The fork does **not** vendor a custom walker. `docling-core`'s `iterate_items()` is the contract. Schema-version tracking is inherited from the `docling-core` version pin.

### 3. Offset-to-ref mapper

After RST parsing produces relations with character offsets, map each relation's nucleus and satellite character ranges to sets of `self_ref`s.

**Overlap rule (v1):** a relation's `nucleus_refs` (resp. `satellite_refs`) contains every `self_ref` whose harvest range has *any* non-empty intersection with the relation's nucleus (resp. satellite) span. No threshold for inclusion.

**Note field:** when a relation's span overlaps ≥ 90% with one `self_ref` but marginally touches an adjacent one, attach a `note` field describing the imbalance, for example:

```json
"note": "nucleus dominantly in #/texts/47; spills into #/texts/48 (8% overlap)"
```

The 90% threshold is the only knob; other `note` shapes are reserved for future use.

### 4. Schema versioning

Stamp the output with `"schema_name": "isanlp_rst_docling"` and `"schema_version": "1.0"`. Bump for breaking changes only; additive optional fields do not require a version bump.

### 5. New dependency: `docling-core`

`docling-core` becomes a hard dependency. It is pure Python + Pydantic, validates inputs against the official schema, and provides the canonical walker. The fork inherits its schema-version tracking; when Docling bumps its schema, the pin tells us. Added to both `pyproject.toml` (runtime) and `pixi.toml` (locked env).

### 6. Optional later: Docling-cue awareness

Out of scope for v1. The standard parser treats text as a flat stream; Docling exposes structural cues a cue-aware future version could exploit:

- **PPTX**: per-slide groups; speaker-notes vs slide-body as candidate `Elaboration` pairs.
- **PDF**: section_header `level` hierarchy; list-item nesting.
- **VTT**: per-turn speaker / timing boundaries as candidate discourse units.

v1 ships the structurally-naïve output first; cue-awareness is evaluated after.

## Testing

Smoke tests:

1. **Round-trip:** harvest a Docling source, run RST, verify every `self_ref` in `relations[].nucleus_refs` / `satellite_refs` exists in the source's `self_ref` set.
2. **Reproducibility:** parse the same source twice with the same `tool_version` and `model_version` — byte-identical relations (modulo metadata fields that intentionally vary, if any).
3. **Format coverage:** one committed fixture per source flavour (pptx, pdf, vtt, markdown). Each parses without source-format special-casing in the fork's code.

## Out of scope (v1)

- **Upstream PR to `tchewik/isanlp_rst`.** Per this fork's CLAUDE.md, feeding work back upstream is opt-in. The Docling-native entry point may or may not be generally useful upstream; default is to keep it in this fork.
- **Pedagogic / domain judgement.** RST is descriptive linguistics. The fork measures rhetorical structure; it does not judge relevance, importance, learner-difficulty, or pedagogic value.
- **Embedding outputs.** The fork emits structural relations, not vector representations. Embeddings are a separate scaffold layer.
- **Table cell text.** Tables yield only a `TableItem` `self_ref` in v1; cell-text harvesting is a v2 concern.
- **Picture caption text.** Picture captions are not traversed in v1; consumers needing caption-aware RST wait for v2 with `traverse_pictures=True`.

## Output contract for downstream consumers

The fork emits a single JSON object conforming to the schema above. Consumers:

- Read `schema_name` and `schema_version` to confirm format.
- Read `relations[].nucleus_refs` / `satellite_refs` as lists of `self_ref` strings.
- Cross-reference `self_ref`s against the original Docling source. The Docling input already carries `origin.binary_hash` if a hash anchor is needed for cache invalidation.
- Treat `note` field as optional free-form text describing overlap imbalance.

The fork does **not**:

- Emit consumer-specific business logic, fields, or metadata.
- Coordinate harvest order with any specific consumer's preferences.
- Make assumptions about how `self_ref` references will be used downstream.

---

*Last revised 2026-05-15 (consumer-agnostic rewrite). Build plan: [`./2026-05-15-docling-native-rst-build.md`](./2026-05-15-docling-native-rst-build.md).*
