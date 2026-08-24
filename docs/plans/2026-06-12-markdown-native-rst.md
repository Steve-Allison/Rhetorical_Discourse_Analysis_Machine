# Markdown-native RST output

**Status:** Shipped (revised same day — two-level table analysis, see § Revisions)
**Date:** 2026-06-12
**Driver:** Steve Allison
**Target consumers:** any downstream tool that wants RST relations indexed against a raw `.md` source — static-site discourse summarisation, README/spec analysis, MkDocs / MyST corpora, prose-mining of internal docs.

---

## Revisions

**2026-06-12 (revision 2 — two-level table analysis, same day):** The initial build harvested table cells inline into the global prose stream. Critical review flagged the risk: the binary document tree must attach every cell somewhere, distorting relations between the prose units flanking the table. Steve selected **Option 2 (two-level analysis)**: cells are excluded from the main document harvest; each table gets its own RST mini-parse whose relations land in `MarkdownRstResult.table_analyses`. Everything is still analysed — table discourse just no longer pollutes prose discourse. The same architecture now applies to `parse_docling` and `parse_doclang` (see their plan revisions).

Same revision also landed, from the same review: blockquote containment for all constructs (not just paragraphs), quoted headings no longer open section boundaries, HTML blocks stripped to text, GFM strikethrough enabled (no literal `~~` in the harvest), `device="auto"` CPU fallback, `dtype` pass-through, an optional on-disk result cache, and shared `_rst_common` flatten/overlap machinery (iterative — survives degenerate deep trees; bisect-backed overlap).

**2026-06-12 (revision 1):** Initial proposal + build.

---

## Why this exists

Markdown is already parseable via the Docling route (`docling-core` is a hard dep), but a consumer with a plain `.md` file must first push it through the heavy `docling` runtime to produce a `*.docling.json` before calling `parse_docling`.

A native `parse_markdown(path)` entry point closes that gap:

- No `docling` runtime dep. CommonMark parsing is a pure-Python concern (`markdown-it-py`).
- Symmetric with the existing native paths. `_rst_common/` carries the shared overlap, flatten, runtime, and cache machinery.
- Stable per-block addresses (`#/blocks/N`) parallel to Docling's `#/texts/N`.

## What we ship

`isanlp_rst.markdown.parse_markdown(path)`:

1. **Accepts** a path to a `.md` (or `.markdown`) file directly.
2. **Tokenises** via `markdown-it-py` with the front-matter plugin plus (under `gfm=True`) the `table` and `strikethrough` rules. Source-line ranges come free on block tokens via `token.map`.
3. **Harvests** the main document text (headings, paragraphs, list items, blockquote content, code blocks, HTML-stripped blocks) into one input with `(block_ref, kind, text, start, end, …)` spans — tables excluded.
4. **Harvests each table separately** — one `TableHarvest` per table, cells row-major with `#/tables/T/cells/K` refs.
5. **Detects boundaries** (`section-N` with `level`, `table-T`, `code_block-N`, `document`).
6. **Runs RST once over the main harvest** and **once per table harvest** via the (injectable) `Parser`.
7. **Maps offsets to refs** with the shared bisect-backed overlap rule.
8. **Emits** one `MarkdownRstResult`: document tree + `table_analyses` + boundary metadata. Serialise with `result.to_dict()` / `result.to_json()`.

## Supported source format

| Source | Treatment |
|---|---|
| **Markdown (CommonMark)** | `section-N` boundary at each ATX / Setext heading; `level` ∈ {1..6}. Pre-heading content → leading `document` boundary. |
| **GFM tables** | two-level analysis: each table is its own `table-T` boundary AND its own RST mini-parse in `table_analyses`. Cells are addressed `#/tables/T/cells/K` (K counts every grid position, so refs stay stable past empty cells). The synthetic `#/tables/T` marker carries no harvest span — it can never land in relation refs. |
| **Blockquotes** | all quoted constructs (paragraphs, headings, lists, code, HTML, tables) are gated together by `include_blockquotes`. A quoted heading harvests as `blockquote_heading` and never opens a section. |
| **Fenced / indented code blocks** | harvested as `code_block` spans + own `code_block-N` boundary. Default on. |
| **Raw HTML blocks** | tags stripped, remaining text harvested as `html_block` spans. Default on. |
| **GFM strikethrough** | enabled under `gfm=True`; wrappers dropped, text kept (no literal `~~`). |
| **Front-matter** | YAML (`---...---`) only — the `mdit-py-plugins` front-matter plugin supports nothing else. Stripped from the harvest; raw text in `source_origin.front_matter`, `front_matter_format == "yaml"`. No structured parsing (no PyYAML dep). |
| **Inline images** | alt text flattens into the parent block's text (no separate span, no knob — decision: alt text is inline content, same as emphasis). |

**Cross-format consistency directive (2026-06-12):** ALL format-native entry points analyse everything in the source — not just prose — via the same two-level shape. `parse_docling` and `parse_doclang` were aligned in the same change set (see their plan revisions).

## Output shape

```json
{
  "schema_name": "isanlp_rst_markdown",
  "schema_version": "1.0",
  "tool": "isanlp_rst",
  "tool_version": "<git describe / package version / 'unknown'>",
  "model_version": "gumrrg",
  "inventory": "gumrrg",
  "source": "design-notes.md",
  "source_origin": {
    "format": "markdown",
    "gfm": true,
    "front_matter": "title: Design notes\nauthor: Steve\n",
    "front_matter_format": "yaml"
  },
  "boundaries": [
    {"id": "section-0", "kind": "section", "label": "Introduction",
     "parent_block_ref": null, "block_refs": ["#/blocks/0", "#/blocks/1"], "level": 1},
    {"id": "table-0", "kind": "table", "label": null, "parent_block_ref": null,
     "block_refs": ["#/tables/0", "#/tables/0/cells/0", "#/tables/0/cells/1"], "level": null}
  ],
  "relations": [
    {"id": 0, "relation": "elaboration", "nuclearity": "NS",
     "nucleus_refs": ["#/blocks/0"], "satellite_refs": ["#/blocks/1"],
     "depth": 0, "left_id": 1, "right_id": 2,
     "boundary_memberships": ["section-0"], "note": null}
  ],
  "edus": [
    {"id": 1, "block_refs": ["#/blocks/0"], "depth": 1},
    {"id": 2, "block_refs": ["#/blocks/1"], "depth": 1}
  ],
  "table_analyses": [
    {"id": "table-0",
     "relations": [],
     "edus": [{"id": 0, "block_refs": ["#/tables/0/cells/0", "#/tables/0/cells/1"], "depth": 0}]}
  ]
}
```

Key design points:

- **Same flat `relations` list with `left_id` / `right_id`** as the other entry points.
- **`table_analyses[].id` matches the `table-T` boundary id**; analysis ids are a namespace local to each analysis; cell refs resolve against the boundary's `block_refs`.
- **The main tree never references table content** — cells live only in analyses; the marker lives only in the boundary.
- **`source_origin.front_matter`** is raw text; parsing is the consumer's choice.

## Architecture

```text
parse_markdown(path, *, parser=None, cache_dir=None, **knobs)
  │
  ├─→ cache check (sha256 of source bytes + model identity + knobs) — return on hit
  │
  ├─→ tokens, front_matter = load_markdown(text, gfm=True)
  │
  ├─→ harvest        = harvest_markdown_text(tokens, knobs)      # prose only
  ├─→ table_harvests = harvest_markdown_tables(tokens, knobs)    # one per table
  │
  ├─→ boundaries = detect_boundaries(harvest.spans, table_harvests)
  │
  ├─→ parser = parser or Parser(..., cuda_device=resolve_device(device), dtype=dtype)
  ├─→ main tree  = parser(harvest.full_text)        when non-empty
  ├─→ per-table  = parser(th.full_text) per harvest — flattened against the table boundary
  │
  └─→ MarkdownRstResult(..., relations, edus, table_analyses)  → cache store
```

Shared machinery in `isanlp_rst/_rst_common/`: `SpanIndex` (bisect overlap), iterative `flatten_tree` (explicit stacks — no RecursionError on degenerate joint-chains), `resolve_device` (with CPU fallback for `"auto"`), `resolve_tool_version`, result cache helpers.

## Public API

```python
from pathlib import Path
from isanlp_rst.markdown import parse_markdown, MarkdownRstResult

result: MarkdownRstResult = parse_markdown(
    Path("design-notes.md"),
    parser: Parser | None = None,           # inject for batch use
    hf_model_name: str = "tchewik/isanlp_rst_v3",
    hf_model_version: str = "gumrrg",
    relinventory: str | None = None,
    device: str = "auto",                   # auto → GPU when available, else CPU
    dtype: str | None = None,               # mixed-precision override
    gfm: bool = True,                       # tables + strikethrough
    include_blockquotes: bool = True,       # gates ALL quoted constructs
    include_table_cells: bool = True,       # two-level table analysis on/off
    include_code_blocks: bool = True,
    include_html: bool = True,              # tags stripped to text
    harvest_separator: str = "\n\n",
    note_threshold: float = 0.90,
    max_harvest_chars: int = 200_000,       # checked per harvest (main + each table)
    cache_dir: str | Path | None = None,    # on-disk result cache
)
```

Defaults reflect the cross-format directive: everything analysed by default. `include_table_cells=False` drops table analyses entirely (and, for markdown, the `table-T` boundaries — they derive from the harvests).

## Testing

Shipped suites (`tests/test_markdown_*.py`, `tests/test_rst_common.py`):

- **Harvester:** inline flattening (emphasis/link/strikethrough/image), blockquote containment for every construct, quoted-heading reclassification, HTML stripping, table grid positions (row-major, stable refs past empty cells), offset tiling.
- **Boundaries:** section levels, quoted headings excluded, two-level table boundary shape, no orphan spans, cells outside sections.
- **Entry:** error-path guards, stub-parser two-level orchestration (call counts, analysis/boundary ref resolution, knob-off behaviour), on-disk cache (hit skips reparse; knob and source changes miss), `to_dict`/`to_json`, golden-output regression (`tests/fixtures/markdown/golden_two_para.rst.json`), `device="auto"` follows torch backends.
- **Shared:** 5000-deep tree flatten without RecursionError; exhaustive bisect-vs-linear overlap equivalence; cache key sensitivity.
- **Slow (model-loading):** metadata smoke, id-resolution, table-analysis end-to-end on `gfm-rich.md`, round-trip ref closure, injection idempotence.

Fixtures: `minimal.md`, `multi-level.md`, `gfm-rich.md` + the golden JSON.

## Quality measurement

`pixi run rst-diag <paths>` parses any mix of `.md` / `*.docling.json` / `*.dclg` sources and emits per-document proxy metrics (joint-chain ratio, tree skew, cross-boundary ratio, note ratio, table-analysis count) plus corpus summaries — the measuring stick for any future harvest-policy change. See `scripts/rst_diag.py`.

## Out of scope

- **Custom dialects beyond GFM.** No MyST, no admonitions, no Pandoc extensions.
- **TOML / JSON front-matter.** The front-matter plugin is YAML-delimiter only.
- **Front-matter parsing.** Raw text only — no PyYAML / tomllib dependency here.
- **`docling` runtime as a dep.**
- **Hierarchical long-input parsing.** Flagged in the 2026-06-12 review (B3) as a spike *gated on rst-diag evidence of degradation at length* — deliberately not built until the measurement says so.
- **Pandoc AST input.**

## Dependencies

- `markdown-it-py>=3` — CommonMark parser, source-line maps, enableable `table` / `strikethrough` rules.
- `mdit-py-plugins>=0.4` — front-matter plugin.

Both pure Python, MIT-licensed.

---

*Companion revisions: [`2026-05-15-docling-native-rst.md`](./2026-05-15-docling-native-rst.md) (revision 6), [`2026-05-15-doclang-native-rst.md`](./2026-05-15-doclang-native-rst.md) (2026-06-12 revision).*
