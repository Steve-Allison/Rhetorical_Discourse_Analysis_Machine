# Boundary-Partitioned Long-Input Parsing

**Status:** Design (not yet implemented). **2026-08-16:** do **not** treat PPTX slides as parse partitions. A slide is a page; the deck is the book; one tree over the deck is the product. Partitioning by `slide-N` would treat pages as chapters. Revisit only if `rst-diag` shows length degradation on whole-deck harvests.
**Date:** 2026-06-12
**Driver:** Steve Allison
**Trigger:** CSM project failing on large slide decks — `content_supply_chain_customer_presentation.docling.json` (98 slides, 1.26 MB) and others exceeding the `max_harvest_chars=200_000` document-level limit.

---

## 1. Problem

All three entry points (`parse_docling`, `parse_doclang`, `parse_markdown`) currently:

1. Harvest the full document into one `full_text` string.
2. Check `len(full_text) > max_harvest_chars` → raise `InputTooLargeError`.
3. Call `parser(full_text)` once.

The default `max_harvest_chars=200_000` (~40k words) is treating the problem as if the input is raw unstructured text. But all three formats deliver **pre-structured** documents: PPTX decks via Docling carry explicit slide groups; PDFs carry section headers; DocLang documents carry heading/page/group hierarchies; Markdown files carry heading-delimited sections.

For a 98-slide deck with 2,000 chars per slide, the total harvest is ~196,000 chars — barely over the limit. Each individual slide is ~2,000 chars. The limit is firing on a normal deck.

---

## 2. Root Cause

The `max_harvest_chars` guard was added as an honest acknowledgement that **hierarchical long-input parsing** hadn't been built: rather than silently returning a suspect RST tree for a book-length document, fail loudly. That reasoning is sound for structurally flat text.

For structured documents it is wrong because:

- The natural chunking units — slides, sections, headings — are **already present** in the document's structural metadata.
- The boundary detector (`detect_boundaries`) runs **before** the parse and already identifies exactly those units.
- RST relations **across** slides or top-level sections are almost never meaningful for the CSM use case (discourse within a slide or section is what matters; cross-slide relations are generally uninformative `joint`s).
- The sliding-window transformer at the model level can already handle long inputs; the limit was about tree-quality uncertainty, not model capacity.

---

## 3. Proposed Architecture: Boundary-Partitioned Parse

### Core change

Instead of one `parser(harvest.full_text)` call → **N calls**, one per primary boundary region.

```
Current:  harvest all → check total size → parse one big string → flatten
Proposed: harvest all → detect boundaries → partition spans by boundary →
          parse each partition → offset IDs → concatenate → flatten each partition
```

Each primary boundary (slide, section, heading, page, group) gets its own:

- sub-harvest: the spans belonging to that boundary, with offsets rebased to start at 0
- `parser()` call
- `flatten_tree()` call against the **full** boundary list (so `boundary_memberships` resolve correctly)
- ID offset applied to keep a globally unique ID namespace across all partitions

Tables remain separately handled (two-level analysis, unchanged).

### When to partition

`parse_mode` parameter controls the behaviour:

| `parse_mode` | Behaviour |
|---|---|
| `"auto"` (new default) | Partition when `len(harvest.full_text) > max_harvest_chars`; else document mode |
| `"document"` (current behaviour) | Always one parse; raise `InputTooLargeError` if total > `max_harvest_chars` |
| `"boundary"` (new) | Always partition, regardless of size |

`max_harvest_chars` changes semantics:

- In `"document"` mode: hard error threshold (current semantics, preserved for backward compat).
- In `"auto"` mode: trigger threshold — above it, switch to boundary mode.
- In `"boundary"` mode: ignored for the total; used as per-partition guard.

A new `max_section_chars` (default `2_000_000`) replaces the per-section hard guard — fires only for a single pathologically large partition (e.g., a 500-slide deck crammed into one Docling group with no sub-structure).

### What doesn't change for consumers

- Output types: `DoclingRstResult`, `DoclangRstResult`, `MarkdownRstResult` — **unchanged**.
- Output fields: `relations`, `edus`, `table_analyses`, `boundaries` — **unchanged**.
- `boundary_memberships` on each relation: still references the full global boundary list.
- ID semantics: globally unique across the whole result (offset arithmetic, see §5).
- `table_analyses`: unchanged; tables were already partitioned separately.

The only consumer-visible behavioural change: in `"auto"` mode, for large documents, relations will not span primary-boundary seams. For slide decks this is correct; for long PDFs with cross-section elaboration it is a trade-off. The `parse_mode="document"` escape hatch preserves current behaviour for callers that need cross-boundary relations.

---

## 4. Primary Boundary Kinds (per format)

These are the partition units. Tables and sub-boundaries are excluded.

| Format | Primary kinds | Excluded from partitioning |
|---|---|---|
| Docling | `"slide"`, `"section"`, `"turn"`, `"document"` | `"table"`, `"slide-notes"` |
| DocLang | `"heading"`, `"page"`, `"group"`, `"document"` | `"table"`, `"field_region"` |
| Markdown | `"section"`, `"document"` | `"table"`, `"code_block"` |

When only one primary boundary exists (e.g., a document with no headings gets a single `"document"` boundary), boundary mode is equivalent to document mode — one parse. If that single boundary's text exceeds `max_section_chars`, `InputTooLargeError` fires.

---

## 5. New `_rst_common` Helpers

Two generic helpers added to `isanlp_rst/_rst_common/`. These operate purely on `start`, `end`, `text`, `id`, `left_id`, `right_id` fields — present in all three formats — and use `dataclasses.replace()` to produce new frozen instances without touching format-specific fields.

### `_partition.py`

```python
"""Generic helpers for boundary-partitioned parse orchestration.

Works with any frozen dataclass that carries:
  - HarvestSpan: ``text``, ``start``, ``end`` (+ format-specific fields)
  - RstRelation: ``id``, ``left_id``, ``right_id`` (+ format-specific fields)
  - RstEdu: ``id`` (+ format-specific fields)

Uses ``dataclasses.replace()`` — frozen dataclasses are supported.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Sequence
from typing import Any, TypeVar

S = TypeVar("S")
R = TypeVar("R")
E = TypeVar("E")


def offset_ids(
    relations: tuple[Any, ...],
    edus: tuple[Any, ...],
    offset: int,
) -> tuple[tuple[Any, ...], tuple[Any, ...]]:
    """Add ``offset`` to every ``id``, ``left_id``, ``right_id`` in relations
    and every ``id`` in edus.

    Works for all three format schemas (Docling, DocLang, Markdown) because
    all share these field names. Format-specific fields are untouched.
    """
    if offset == 0:
        return relations, edus
    new_relations = tuple(
        dataclasses.replace(
            r,
            id=r.id + offset,
            left_id=r.left_id + offset,
            right_id=r.right_id + offset,
        )
        for r in relations
    )
    new_edus = tuple(dataclasses.replace(e, id=e.id + offset) for e in edus)
    return new_relations, new_edus


def rebase_spans_uniform(
    spans: Sequence[Any],
    separator: str,
) -> tuple[str, tuple[Any, ...]]:
    """Rebuild ``spans`` with offsets starting at 0, joined by ``separator``.

    For Docling and Markdown, where every inter-span gap is the same
    ``harvest_separator``.

    Returns ``(full_text, rebased_spans)``.
    """
    pieces: list[str] = []
    new_spans: list[Any] = []
    cursor = 0
    sep_len = len(separator)

    for i, span in enumerate(spans):
        if i > 0:
            cursor += sep_len
        new_spans.append(dataclasses.replace(span, start=cursor, end=cursor + len(span.text)))
        pieces.append(span.text)
        cursor += len(span.text)

    return separator.join(pieces), tuple(new_spans)


def rebase_spans_doclang(
    spans: Sequence[Any],
    harvest_separator: str,
) -> tuple[str, tuple[Any, ...]]:
    """Rebuild DocLang spans with offsets starting at 0.

    Thread-continuation spans (consecutive spans sharing a non-None
    ``thread_id``) are joined with a single space; all other gaps use
    ``harvest_separator``.

    Returns ``(full_text, rebased_spans)``.
    """
    parts: list[str] = []
    new_spans: list[Any] = []
    cursor = 0

    for i, span in enumerate(spans):
        if i > 0:
            prev = spans[i - 1]
            continuation = span.thread_id is not None and prev.thread_id == span.thread_id
            sep = " " if continuation else harvest_separator
            parts.append(sep)
            cursor += len(sep)
        new_spans.append(dataclasses.replace(span, start=cursor, end=cursor + len(span.text)))
        parts.append(span.text)
        cursor += len(span.text)

    return "".join(parts), tuple(new_spans)


def partition_spans_by_refs(
    spans: Sequence[Any],
    primary_boundaries: Sequence[Any],
    *,
    ref_of: Any,  # attrgetter or lambda — span → str
    boundary_refs_of: Any,  # boundary → frozenset[str]
) -> dict[str, list[Any]]:
    """Group ``spans`` by which primary boundary they belong to.

    Returns ``{boundary_id: [span, ...]}`` in boundary order.
    Spans whose ref does not appear in any primary boundary are dropped
    (they are typically the boundary marker itself, e.g. a section header
    whose self_ref appears in the boundary but carries no HarvestSpan).

    Precondition: primary boundaries are non-overlapping (each ref
    appears in at most one boundary).
    """
    ref_to_bid: dict[str, str] = {}
    result: dict[str, list[Any]] = {b.id: [] for b in primary_boundaries}

    for b in primary_boundaries:
        for ref in boundary_refs_of(b):
            ref_to_bid[ref] = b.id

    for span in spans:
        bid = ref_to_bid.get(ref_of(span))
        if bid is not None:
            result[bid].append(span)

    return result


__all__ = [
    "offset_ids",
    "partition_spans_by_refs",
    "rebase_spans_doclang",
    "rebase_spans_uniform",
]
```

Export from `_rst_common/__init__.py` (additions only):

```python
# add to existing imports:
from ._partition import (
    offset_ids,
    partition_spans_by_refs,
    rebase_spans_doclang,
    rebase_spans_uniform,
)

# add to __all__:
("offset_ids",)
("partition_spans_by_refs",)
("rebase_spans_doclang",)
("rebase_spans_uniform",)
```

---

## 6. Changes: `docling/_entry.py`

### New constant and imports

```python
# add after DEFAULT_MAX_HARVEST_CHARS
DEFAULT_MAX_SECTION_CHARS = 2_000_000
DEFAULT_PARSE_MODE = "auto"

# Boundary kinds that define partition units
_PARTITION_KINDS: frozenset[str] = frozenset({"slide", "section", "turn", "document"})

# add to _rst_common imports:
from .._rst_common import (
    offset_ids,
    partition_spans_by_refs,
    rebase_spans_uniform,
    # ... existing imports
)
```

### Signature change

```python
def parse_docling(
    path: str | Path,
    *,
    parser: "Parser | None" = None,
    hf_model_name: str = "tchewik/isanlp_rst_v3",
    hf_model_version: str = "gumrrg",
    relinventory: str | None = None,
    device: str = "auto",
    dtype: str | None = None,
    include_picture_descriptions: bool = True,
    include_slide_notes: bool = True,
    include_furniture: bool = False,
    include_table_cells: bool = True,
    harvest_separator: str = "\n\n",
    coalesce_speaker_turns: bool = True,
    note_threshold: float = 0.90,
    parse_mode: str = DEFAULT_PARSE_MODE,          # NEW
    max_harvest_chars: int = DEFAULT_MAX_HARVEST_CHARS,
    max_section_chars: int = DEFAULT_MAX_SECTION_CHARS,  # NEW
    cache_dir: str | Path | None = None,
) -> DoclingRstResult:
```

### Parse dispatch (replaces the current size-check + single parse block)

Current code (lines ~172–198 in `_entry.py`):

```python
# CURRENT — replace this entire block
for label, text in (("main", harvest.full_text), ...):
    if len(text) > max_harvest_chars:
        raise InputTooLargeError(...)

...

if harvest.full_text:
    rst_tree = parser(harvest.full_text)["rst"][0]
    relations, edus = flatten_tree(rst_tree, harvest.spans, boundaries, note_threshold=note_threshold)
else:
    relations, edus = (), ()
```

Replacement:

```python
# Table harvests: size guard is unchanged (tables are already partitioned)
for label, text in ((th.marker_ref, th.full_text) for th in table_harvests):
    if text and len(text) > max_section_chars:
        raise InputTooLargeError(
            f"Table harvest for {label} is {len(text)} chars, exceeds "
            f"max_section_chars={max_section_chars}. Chunk upstream or raise the limit."
        )

# ---- Main document parse ------------------------------------------------

if not harvest.full_text:
    relations, edus = (), ()
elif _should_partition(harvest.full_text, boundaries, parse_mode, max_harvest_chars):
    relations, edus = _partitioned_parse_docling(
        harvest=harvest,
        boundaries=boundaries,
        parser=parser,
        harvest_separator=harvest_separator,
        note_threshold=note_threshold,
        max_section_chars=max_section_chars,
    )
else:
    # Document mode: current behaviour
    if len(harvest.full_text) > max_harvest_chars:
        raise InputTooLargeError(
            f"Harvested text is {len(harvest.full_text)} chars, exceeds "
            f"max_harvest_chars={max_harvest_chars}. "
            f"Use parse_mode='boundary' or raise the limit."
        )
    rst_tree = parser(harvest.full_text)["rst"][0]
    relations, edus = flatten_tree(rst_tree, harvest.spans, boundaries, note_threshold=note_threshold)
```

### `_should_partition` helper (module-level, not exported)

```python
def _should_partition(
    full_text: str,
    boundaries: tuple[Boundary, ...],
    parse_mode: str,
    max_harvest_chars: int,
) -> bool:
    """True when the entry point should use boundary-partitioned parsing."""
    if parse_mode == "document":
        return False
    if parse_mode == "boundary":
        return True
    if parse_mode == "auto":
        return len(full_text) > max_harvest_chars
    raise ValueError(f"Unknown parse_mode={parse_mode!r}. Expected 'document', 'boundary', or 'auto'.")
```

### `_partitioned_parse_docling` helper (module-level, not exported)

```python
from operator import attrgetter as _attrgetter

_self_ref_of = _attrgetter("self_ref")


def _partitioned_parse_docling(
    *,
    harvest: HarvestResult,
    boundaries: tuple[Boundary, ...],
    parser: "Parser",
    harvest_separator: str,
    note_threshold: float,
    max_section_chars: int,
) -> tuple[tuple[RstRelation, ...], tuple[RstEdu, ...]]:
    """Parse the document harvest partition-by-partition.

    Primary boundaries (slide / section / turn / document) define the
    partitions. Each partition's spans are rebased to offset-0, parsed
    independently, and the resulting IDs are offset to form a globally
    unique namespace across the whole result.
    """
    primary = [b for b in boundaries if b.kind in _PARTITION_KINDS]
    if not primary:
        # Degenerate — no structural boundaries; parse as one unit.
        # (Should not happen given detect_boundaries always emits at least
        # one primary boundary, but be safe.)
        rst_tree = parser(harvest.full_text)["rst"][0]
        return flatten_tree(rst_tree, harvest.spans, boundaries, note_threshold=note_threshold)

    partitions = partition_spans_by_refs(
        harvest.spans,
        primary,
        ref_of=_self_ref_of,
        boundary_refs_of=lambda b: frozenset(b.self_refs),
    )

    all_relations: list[RstRelation] = []
    all_edus: list[RstEdu] = []
    id_offset = 0

    for b in primary:
        part_spans = partitions.get(b.id, [])
        if not part_spans:
            continue

        full_text, rebased = rebase_spans_uniform(part_spans, harvest_separator)
        if not full_text:
            continue

        if len(full_text) > max_section_chars:
            raise InputTooLargeError(
                f"Partition '{b.id}' harvest is {len(full_text)} chars, exceeds "
                f"max_section_chars={max_section_chars}. "
                f"Split the source or raise the limit."
            )

        rst_tree = parser(full_text)["rst"][0]
        part_rels, part_edus = flatten_tree(
            rst_tree,
            rebased,
            boundaries,  # full boundary list — memberships reference global ids
            note_threshold=note_threshold,
        )

        part_rels, part_edus = offset_ids(part_rels, part_edus, id_offset)
        id_offset += len(part_rels) + len(part_edus)

        all_relations.extend(part_rels)
        all_edus.extend(part_edus)

    return tuple(all_relations), tuple(all_edus)
```

### `knobs` dict update (cache key must include new parameters)

```python
knobs: dict[str, object] = {
    ...
    "parse_mode": parse_mode,           # NEW
    "max_harvest_chars": max_harvest_chars,
    "max_section_chars": max_section_chars,  # NEW
}
```

---

## 7. Changes: `doclang/_entry.py`

Symmetric to Docling. Key differences:

- `_PARTITION_KINDS = frozenset({"heading", "page", "group", "document"})`
- Uses `rebase_spans_doclang` (thread-continuation-aware) instead of `rebase_spans_uniform`
- Boundary ref field is `b.xpaths`, span ref attribute is `span.xpath`
- Imports `rebase_spans_doclang` from `_rst_common`

```python
# _PARTITION_KINDS for doclang
_PARTITION_KINDS: frozenset[str] = frozenset({"heading", "page", "group", "document"})

_xpath_of = _attrgetter("xpath")


def _partitioned_parse_doclang(
    *,
    harvest: HarvestResult,
    boundaries: tuple[Boundary, ...],
    parser: "Parser",
    harvest_separator: str,
    note_threshold: float,
    max_section_chars: int,
) -> tuple[tuple[RstRelation, ...], tuple[RstEdu, ...]]:
    primary = [b for b in boundaries if b.kind in _PARTITION_KINDS]
    if not primary:
        rst_tree = parser(harvest.full_text)["rst"][0]
        return flatten_tree(rst_tree, harvest.spans, boundaries, note_threshold=note_threshold)

    partitions = partition_spans_by_refs(
        harvest.spans,
        primary,
        ref_of=_xpath_of,
        boundary_refs_of=lambda b: frozenset(b.xpaths),
    )

    all_relations: list[RstRelation] = []
    all_edus: list[RstEdu] = []
    id_offset = 0

    for b in primary:
        part_spans = partitions.get(b.id, [])
        if not part_spans:
            continue

        full_text, rebased = rebase_spans_doclang(part_spans, harvest_separator)
        if not full_text:
            continue

        if len(full_text) > max_section_chars:
            raise InputTooLargeError(
                f"Partition '{b.id}' harvest is {len(full_text)} chars, exceeds max_section_chars={max_section_chars}."
            )

        rst_tree = parser(full_text)["rst"][0]
        part_rels, part_edus = flatten_tree(
            rst_tree,
            rebased,
            boundaries,
            note_threshold=note_threshold,
        )

        part_rels, part_edus = offset_ids(part_rels, part_edus, id_offset)
        id_offset += len(part_rels) + len(part_edus)

        all_relations.extend(part_rels)
        all_edus.extend(part_edus)

    return tuple(all_relations), tuple(all_edus)
```

---

## 8. Changes: `markdown/_entry.py`

Symmetric to Docling. Key differences:

- `_PARTITION_KINDS = frozenset({"section", "document"})`
- Span ref attribute is `span.block_ref`
- Boundary ref field is `b.block_refs`
- Uses `rebase_spans_uniform`

```python
_PARTITION_KINDS: frozenset[str] = frozenset({"section", "document"})

_block_ref_of = _attrgetter("block_ref")


def _partitioned_parse_markdown(
    *,
    harvest: HarvestResult,
    boundaries: tuple[Boundary, ...],
    parser: "Parser",
    harvest_separator: str,
    note_threshold: float,
    max_section_chars: int,
) -> tuple[tuple[RstRelation, ...], tuple[RstEdu, ...]]:
    primary = [b for b in boundaries if b.kind in _PARTITION_KINDS]
    if not primary:
        rst_tree = parser(harvest.full_text)["rst"][0]
        return flatten_tree(rst_tree, harvest.spans, boundaries, note_threshold=note_threshold)

    partitions = partition_spans_by_refs(
        harvest.spans,
        primary,
        ref_of=_block_ref_of,
        boundary_refs_of=lambda b: frozenset(b.block_refs),
    )

    all_relations: list[RstRelation] = []
    all_edus: list[RstEdu] = []
    id_offset = 0

    for b in primary:
        part_spans = partitions.get(b.id, [])
        if not part_spans:
            continue

        full_text, rebased = rebase_spans_uniform(part_spans, harvest_separator)
        if not full_text:
            continue

        if len(full_text) > max_section_chars:
            raise InputTooLargeError(
                f"Partition '{b.id}' harvest is {len(full_text)} chars, exceeds max_section_chars={max_section_chars}."
            )

        rst_tree = parser(full_text)["rst"][0]
        part_rels, part_edus = flatten_tree(
            rst_tree,
            rebased,
            boundaries,
            note_threshold=note_threshold,
        )

        part_rels, part_edus = offset_ids(part_rels, part_edus, id_offset)
        id_offset += len(part_rels) + len(part_edus)

        all_relations.extend(part_rels)
        all_edus.extend(part_edus)

    return tuple(all_relations), tuple(all_edus)
```

---

## 9. Error class changes

`InputTooLargeError` stays in each format's `errors.py`. Its docstring and message update to reflect the new semantics:

```python
class InputTooLargeError(DoclingRstError):
    """A single partition's harvested text exceeds ``max_section_chars``.

    In ``parse_mode='document'``, this also fires when the full document
    harvest exceeds ``max_harvest_chars``.

    Callers hitting this error should either:
    - Use ``parse_mode='boundary'`` to activate per-section parsing (the
      document will be partitioned at its natural structural boundaries).
    - Raise ``max_section_chars`` to allow larger individual sections.
    - Pre-split the source document before calling.
    """
```

---

## 10. `knobs` / cache key

All three `_entry.py` files: add `"parse_mode"` and `"max_section_chars"` to the `knobs` dict so cached results are invalidated when these change.

---

## 11. Docstring updates

Each entry point's docstring gains:

```
parse_mode: ``"auto"`` (default) — switch to boundary mode when total
    harvest exceeds ``max_harvest_chars``; ``"boundary"`` — always
    partition at structural boundaries (slides, sections, headings, pages,
    groups); ``"document"`` — one parse over the full harvest (pre-2026-06
    behaviour, raises ``InputTooLargeError`` if total exceeds
    ``max_harvest_chars``).
max_harvest_chars: in ``parse_mode='auto'``, the threshold above which
    boundary mode activates (default 200_000). In ``parse_mode='document'``,
    the hard error limit (unchanged semantics).
max_section_chars: raise ``InputTooLargeError`` when any single boundary
    partition's text exceeds this limit (default 2_000_000). Protects
    against structurally flat documents where no useful partitioning exists.
```

---

## 12. Testing

### New unit tests (no model loading)

**`tests/test_partition_helpers.py`** — exercises `_partition.py` helpers in isolation:

- `test_rebase_spans_uniform_two_spans` — two spans, gap = `"\n\n"`, verify rebased offsets start at 0
- `test_rebase_spans_uniform_single_span` — degenerate: one span, offset stays 0
- `test_rebase_spans_doclang_thread_continuation` — two spans with same `thread_id`: gap = `" "`
- `test_rebase_spans_doclang_no_thread` — two spans, different `thread_id`: gap = harvest_separator
- `test_offset_ids_docling_relation` — `RstRelation` from docling schema, offsets applied to `id`, `left_id`, `right_id`
- `test_offset_ids_markdown_edu` — `RstEdu` from markdown schema, `id` offset applied
- `test_offset_ids_doclang_relation` — DocLang `RstRelation` (has `nucleus_thread_ids` etc.), verify only ID fields change
- `test_offset_ids_zero` — offset=0 returns same objects (identity shortcut)
- `test_partition_spans_by_refs_docling` — three boundaries, six spans, verify correct grouping
- `test_partition_spans_by_refs_unassigned` — span with self_ref not in any boundary is dropped
- `test_partition_spans_preserves_order` — output order matches boundary order, not span order

### New unit tests (stub parser)

In `tests/test_docling_entry.py`, `tests/test_doclang_entry.py`, `tests/test_markdown_entry.py` — add:

- `test_parse_mode_document_raises_on_large` — `parse_mode="document"` raises `InputTooLargeError` when total > `max_harvest_chars`
- `test_parse_mode_boundary_does_not_raise_on_large` — `parse_mode="boundary"` with total > `max_harvest_chars` succeeds; stub parser called N times (once per non-empty primary boundary)
- `test_parse_mode_auto_partitions_when_large` — `parse_mode="auto"` with total > `max_harvest_chars` uses N parser calls; total < `max_harvest_chars` uses 1
- `test_partitioned_ids_globally_unique` — two-section document, partitioned; all `id` values across `relations + edus` are distinct
- `test_partitioned_boundary_memberships_correct` — relation inside section-0 has `"section-0"` in `boundary_memberships`
- `test_max_section_chars_fires` — single large section exceeds `max_section_chars`, raises `InputTooLargeError`
- `test_cache_key_includes_parse_mode` — knobs dict contains `parse_mode`; changing it produces a different cache key

### Existing tests

No changes expected. The existing entry-point tests use small fixtures that stay under `max_harvest_chars=200_000` — they will continue to exercise `parse_mode="auto"` in document mode (total < threshold).

### Integration / slow tests

Add a `@pytest.mark.slow` test in `tests/test_integration.py`:

- `test_parse_docling_boundary_mode_on_large_deck` — load one of the CSM fixtures from `Content_Structuring_Machine/project/sources/` (specifically `content_supply_chain_customer_presentation.docling.json`), call `parse_docling` with `parse_mode="boundary"`, verify result is a valid `DoclingRstResult`, verify `len(result.relations) > 0`, verify IDs are unique.

This test requires the CSM path to be accessible and is marked slow (model load). Run with `pixi run test-all`.

---

## 13. Backwards Compatibility

| Consumer behaviour | Impact |
|---|---|
| Calling with defaults | `parse_mode="auto"` — for small documents (< 200k chars) behaviour is identical to today. For large documents, boundary mode activates silently. |
| Calling with `max_harvest_chars=N` to raise the limit | Still honoured in `"auto"` and `"document"` modes. |
| Catching `InputTooLargeError` | Still raised; semantics updated (fires on per-section size in boundary/auto modes). |
| Result schema | Unchanged. Relations across boundary seams simply don't exist in boundary mode — which is correct for slide decks. |
| Callers that depend on cross-section relations | Pass `parse_mode="document"` to preserve current behaviour (one parse, one tree, cross-section relations present). |

---

## 14. Open Questions

1. **Slide-notes partitions.** `slide-N-notes` boundaries are currently excluded from `_PARTITION_KINDS`. Notes content lands in `slide-N`'s harvest (their self_refs appear in `slide-N`'s boundary). Is that correct, or should notes be excluded from both the main harvest and the partition? Answer requires checking what CSM expects.

2. **Headings as section-starters vs section-members (DocLang).** A `heading-N` boundary currently lists only the heading element's own xpath. Body text under that heading belongs to the document or group boundary, not `heading-N`. This means DocLang headings may produce very short (often single-span) partitions. Should the DocLang boundary detector be changed to bucket body items under headings (like the Docling section detector does)? Or is section-level partitioning better at the `group` level for DocLang?

3. **Cross-boundary relation loss.** In boundary mode, no RST relation will cross a slide/section boundary. For CSM's ingest-and-classify use case this is fine. For downstream tools that want to detect when one section elaborates another (e.g., "slide 3 is a background for slide 5"), boundary mode loses this signal entirely. `parse_mode="document"` recovers it but at the cost of re-enabling the size limit.

4. **`rst-diag` on partitioned results.** The quality proxy metrics (joint ratio, tree skew, cross-boundary ratio) need to be interpreted differently for partitioned results — a high cross-boundary ratio for document mode on a 98-slide deck is expected; the same metric on a single slide's parse is informative. Should `rst-diag` be partition-aware?

---

## 15. File Change Summary

| File | Change |
|---|---|
| `isanlp_rst/_rst_common/_partition.py` | **NEW** — `offset_ids`, `rebase_spans_uniform`, `rebase_spans_doclang`, `partition_spans_by_refs` |
| `isanlp_rst/_rst_common/__init__.py` | Import + export the four new helpers |
| `isanlp_rst/docling/_entry.py` | Add `parse_mode`, `max_section_chars` params; add `_should_partition`, `_partitioned_parse_docling`; update size-check + parse block; update `knobs` dict |
| `isanlp_rst/doclang/_entry.py` | Same changes; use `rebase_spans_doclang` and `b.xpaths` |
| `isanlp_rst/markdown/_entry.py` | Same changes; use `b.block_refs` and `span.block_ref` |
| `isanlp_rst/docling/errors.py` | Update `InputTooLargeError` docstring |
| `isanlp_rst/doclang/errors.py` | Same |
| `isanlp_rst/markdown/errors.py` | Same |
| `tests/test_partition_helpers.py` | **NEW** — 11 unit tests for `_partition.py` |
| `tests/test_docling_entry.py` | 7 new tests (stub-parser, no model load) |
| `tests/test_doclang_entry.py` | 7 new tests |
| `tests/test_markdown_entry.py` | 7 new tests |
| `tests/test_integration.py` | 1 new `@slow` test against CSM fixture |
| `CLAUDE.md` | Update "Active roadmap" to note hierarchical long-input parsing shipped |

---

*Companion plans: [`2026-05-15-docling-native-rst-build.md`](./2026-05-15-docling-native-rst-build.md), [`2026-05-15-doclang-native-rst.md`](./2026-05-15-doclang-native-rst.md), [`2026-06-12-markdown-native-rst.md`](./2026-06-12-markdown-native-rst.md).*
