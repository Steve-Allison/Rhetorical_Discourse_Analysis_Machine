"""Harvest text from a parsed DocLang document for RST parsing.

Two harvesters:

- ``harvest_doclang_text`` — the main document harvest. Walks the lxml
  element tree and emits one ``HarvestSpan`` per text-bearing unit,
  addressed by its local-name canonical XPath. ``<table>`` / ``<index>``
  / ``<tabular>`` are boundary-only here — tables are analysed
  separately (two-level analysis, 2026-06-12 directive Option 2).
  Consecutive spans sharing a ``thread_id`` are joined with a single
  space rather than the harvest separator: ``<thread>`` marks paragraph
  continuation across page breaks, and a hard break mid-paragraph would
  make the segmenter treat one sentence as two.
- ``harvest_doclang_tables`` — one ``TableHarvest`` per ``<table>``,
  in document order, cells addressed by their marker xpaths with
  row/col grid positions.

Virtual-text container shapes (``<list>``) are partitioned at the
self-closing ``<ldiv/>`` marker tokens. Table cells partition at the
OTSL grid markers: ``<ched/>`` / ``<rhed/>`` / ``<corn/>`` (header
cells), ``<fcel/>`` (body cells), ``<ecel/>`` (empty — occupies a grid
position, never yields a span), ``<lcel/>`` / ``<ucel/>`` / ``<xcel/>``
(span-continuation — occupy positions, never yield), ``<nl/>`` (row
break).

Off by default in the main harvest (opt-in via knobs):
  - ``<formula>`` — LaTeX; not natural-language prose
  - ``<code>``    — source code; not natural-language prose
  - ``<page_header>`` / ``<page_footer>`` — furniture-by-position
  - ``<layer value="background">`` / ``<layer value="furniture">`` items
"""

from __future__ import annotations

from collections.abc import Iterable

from lxml import etree

from .loader import local_name, local_path
from .schema import HarvestResult, HarvestSpan, TableHarvest

# Element-head children whose own text must NOT enter the harvest — they
# are metadata, not prose.
_HEAD_LOCALS: frozenset[str] = frozenset({
    "label",
    "thread",
    "xref",
    "href",
    "layer",
    "location",
    "caption",
    "custom",
})

# Top-level semantic elements that we treat as discrete harvest units.
_HARVEST_AS_BLOCK: frozenset[str] = frozenset({
    "text", "heading", "footnote",
})

# OTSL-style cell markers per the DocLang table model.
_HEADER_CELL_MARKERS: frozenset[str] = frozenset({"ched", "rhed", "corn"})
_BODY_CELL_MARKERS: frozenset[str] = frozenset({"fcel"})
_POSITION_ONLY_MARKERS: frozenset[str] = frozenset({"ecel", "lcel", "ucel", "xcel"})
_GRID_MARKERS: frozenset[str] = (
    _HEADER_CELL_MARKERS | _BODY_CELL_MARKERS | _POSITION_ONLY_MARKERS
)
_ROW_BREAK: str = "nl"


def _element_layer(element: etree._Element) -> str:
    """Return the effective ``<layer value="...">`` for ``element``.

    DocLang's ``<layer>`` lives in the element-head as a child of the
    semantic element. Default ``"body"`` per spec when no head child
    declares it.
    """
    for child in element:
        if isinstance(child.tag, str) and local_name(child) == "layer":
            value = child.get("value")
            if value:
                return value
    return "body"


def _thread_id(element: etree._Element) -> int | None:
    """Return the element's ``<thread thread_id="N"/>`` value, if any."""
    for child in element:
        if isinstance(child.tag, str) and local_name(child) == "thread":
            value = child.get("thread_id")
            if value is not None:
                return int(value)
    return None


def _prose_itertext(element: etree._Element) -> Iterable[str]:
    """Yield prose text under ``element``, excluding head-property children.

    Walks ``element``'s body. For each non-head child, yields its
    ``itertext()``. The element's own ``.text`` (before any children) and
    every child's ``.tail`` are included as prose.
    """
    if element.text:
        yield element.text
    for child in element:
        if not isinstance(child.tag, str):
            continue
        if local_name(child) in _HEAD_LOCALS:
            # head property — its tail is still prose (text after the head),
            # but its own subtree is not.
            if child.tail:
                yield child.tail
            continue
        yield from child.itertext()
        if child.tail:
            yield child.tail


def _list_items(list_el: etree._Element) -> Iterable[tuple[etree._Element, str]]:
    """Yield ``(marker, item_text)`` for each ``<ldiv/>`` in a ``<list>`` body.

    Item text accumulates from the marker's ``.tail`` plus the full
    ``itertext()`` and ``.tail`` of all following siblings up to (but not
    including) the next ``<ldiv/>`` marker.
    """
    children = list(list_el)
    n = len(children)
    i = 0
    while i < n:
        child = children[i]
        if isinstance(child.tag, str) and local_name(child) == "ldiv":
            marker = child
            pieces: list[str] = []
            if marker.tail:
                pieces.append(marker.tail)
            j = i + 1
            while j < n:
                sib = children[j]
                if isinstance(sib.tag, str) and local_name(sib) == "ldiv":
                    break
                if isinstance(sib.tag, str):
                    if local_name(sib) in _HEAD_LOCALS:
                        if sib.tail:
                            pieces.append(sib.tail)
                    else:
                        pieces.extend(sib.itertext())
                        if sib.tail:
                            pieces.append(sib.tail)
                j += 1
            text = "".join(pieces).strip()
            yield marker, text
            i = j
        else:
            i += 1


def _table_cells(
    table_el: etree._Element,
) -> Iterable[tuple[etree._Element, str, str, int, int]]:
    """Yield ``(marker, kind, text, row, col)`` per non-empty cell in a ``<table>``.

    Cell text accumulates from the marker's ``.tail`` plus subsequent
    siblings' text up to the next grid marker or ``<nl/>`` row break.
    Position-only markers (``<ecel/>``, ``<lcel/>``, ``<ucel/>``,
    ``<xcel/>``) occupy a grid column and terminate the previous cell's
    accumulation but never yield. Rows are delimited by ``<nl/>``.
    """
    children = list(table_el)
    n = len(children)
    row = 0
    col = 0
    i = 0
    while i < n:
        child = children[i]
        if not isinstance(child.tag, str):
            i += 1
            continue
        tag = local_name(child)
        if tag == _ROW_BREAK:
            row += 1
            col = 0
            i += 1
            continue
        if tag not in _GRID_MARKERS:
            i += 1
            continue
        if tag in _POSITION_ONLY_MARKERS:
            col += 1
            i += 1
            continue
        marker = child
        marker_col = col
        col += 1
        pieces: list[str] = []
        if marker.tail:
            pieces.append(marker.tail)
        j = i + 1
        while j < n:
            sib = children[j]
            if not isinstance(sib.tag, str):
                j += 1
                continue
            sib_local = local_name(sib)
            if sib_local in _GRID_MARKERS or sib_local == _ROW_BREAK:
                break
            if sib_local in _HEAD_LOCALS:
                if sib.tail:
                    pieces.append(sib.tail)
            else:
                pieces.extend(sib.itertext())
                if sib.tail:
                    pieces.append(sib.tail)
            j += 1
        text = "".join(pieces).strip()
        if text:
            kind = "table_header_cell" if tag in _HEADER_CELL_MARKERS else "table_cell"
            yield marker, kind, text, row, marker_col
        i = j
    return


def harvest_doclang_text(
    tree: etree._ElementTree,
    *,
    include_picture_captions: bool = True,
    include_background: bool = False,
    include_furniture: bool = False,
    include_field_regions: bool = False,
    include_code_blocks: bool = False,
    include_formulas: bool = False,
    harvest_separator: str = "\n\n",
) -> HarvestResult:
    """Produce the main document harvest with per-span xpath mapping.

    Args:
        tree: a parsed DocLang document (``lxml.etree._ElementTree``).
        include_picture_captions: include each ``<picture>``'s
            ``<caption>...</caption>`` text when present.
        include_background: include items in layer ``"background"``.
        include_furniture: include items in layer ``"furniture"`` plus
            ``<page_header>`` and ``<page_footer>``.
        include_field_regions: harvest text inside ``<field_region>``
            (default: skipped — boundary-only).
        include_code_blocks: harvest ``<code>`` element text.
        include_formulas: harvest ``<formula>`` element text.
        harvest_separator: inserted between consecutive harvested spans —
            except between spans sharing a ``thread_id``, which join with
            a single space (paragraph continuation).

    Returns:
        ``HarvestResult`` whose ``full_text`` is the document-level input
        for the RST parser, and whose ``spans`` map each text range back
        to its source ``xpath`` in document order. Tables are never
        included — see ``harvest_doclang_tables``.
    """
    root = tree.getroot()
    allowed_layers: set[str] = {"body"}
    if include_background:
        allowed_layers.add("background")
    if include_furniture:
        allowed_layers.add("furniture")

    parts: list[str] = []
    spans: list[HarvestSpan] = []
    cursor = 0

    def _emit(xpath: str, kind: str, thread_id: int | None, layer: str, text: str) -> None:
        nonlocal cursor
        if not text:
            return
        if spans:
            prev = spans[-1]
            continuation = thread_id is not None and prev.thread_id == thread_id
            sep = " " if continuation else harvest_separator
            parts.append(sep)
            cursor += len(sep)
        start = cursor
        end = start + len(text)
        spans.append(HarvestSpan(
            xpath=xpath,
            thread_id=thread_id,
            layer=layer,
            text=text,
            start=start,
            end=end,
            kind=kind,
        ))
        parts.append(text)
        cursor = end

    def _walk(element: etree._Element) -> None:
        if not isinstance(element.tag, str):
            return
        tag = local_name(element)

        if tag == "list":
            layer = _element_layer(element)
            if layer in allowed_layers:
                for marker, item_text in _list_items(element):
                    _emit(local_path(marker), "list_item", _thread_id(element), layer, item_text)
            # nested lists / structural children are handled within _list_items;
            # we still recurse into nested lists for their own boundaries.
            for child in element:
                if isinstance(child.tag, str) and local_name(child) == "list":
                    _walk(child)
            return

        if tag in {"table", "index", "tabular"}:
            # Boundary-only in the main harvest; tables are analysed
            # per-table via harvest_doclang_tables (two-level analysis).
            return

        if tag == "field_region":
            if not include_field_regions:
                return
            for child in element:
                _walk(child)
            return

        if tag in {"page_header", "page_footer"}:
            if not include_furniture:
                return
            layer = _element_layer(element)
            text = "".join(_prose_itertext(element)).strip()
            _emit(local_path(element), tag, _thread_id(element), layer, text)
            return

        if tag == "formula":
            if not include_formulas:
                return
            layer = _element_layer(element)
            if layer not in allowed_layers:
                return
            text = "".join(_prose_itertext(element)).strip()
            _emit(local_path(element), "formula", _thread_id(element), layer, text)
            return

        if tag == "code":
            if not include_code_blocks:
                return
            layer = _element_layer(element)
            if layer not in allowed_layers:
                return
            text = "".join(_prose_itertext(element)).strip()
            _emit(local_path(element), "code", _thread_id(element), layer, text)
            return

        if tag == "picture":
            if not include_picture_captions:
                return
            layer = _element_layer(element)
            if layer not in allowed_layers:
                return
            for child in element:
                if isinstance(child.tag, str) and local_name(child) == "caption":
                    caption_text = "".join(child.itertext()).strip()
                    _emit(local_path(child), "caption", _thread_id(element), layer, caption_text)
            return

        if tag in _HARVEST_AS_BLOCK:
            layer = _element_layer(element)
            if layer not in allowed_layers:
                return
            text = "".join(_prose_itertext(element)).strip()
            _emit(local_path(element), tag, _thread_id(element), layer, text)
            return

        if tag == "group":
            for child in element:
                _walk(child)
            return

        # Unknown / unhandled element — descend without harvesting it as
        # a block (sub-elements may still be harvest-worthy).
        for child in element:
            _walk(child)

    for child in root:
        if isinstance(child.tag, str) and local_name(child) == "head":
            continue
        _walk(child)

    return HarvestResult(full_text="".join(parts), spans=tuple(spans))


def _walk_tables(element: etree._Element) -> Iterable[etree._Element]:
    """Yield every ``<table>`` under ``element`` in document order."""
    if isinstance(element.tag, str) and local_name(element) == "table":
        yield element
        return
    for child in element:
        if isinstance(child.tag, str):
            yield from _walk_tables(child)


def harvest_doclang_tables(
    tree: etree._ElementTree,
    *,
    include_background: bool = False,
    include_furniture: bool = False,
    harvest_separator: str = "\n\n",
) -> tuple[TableHarvest, ...]:
    """Produce one ``TableHarvest`` per ``<table>``, in document order.

    Document order matches ``detect_boundaries``'s ``table-N``
    numbering. Cells are addressed by their marker xpaths with row/col
    grid positions; offsets are local to each table's ``full_text``.
    Tables in excluded layers produce an empty harvest (no spans).
    """
    root = tree.getroot()
    allowed_layers: set[str] = {"body"}
    if include_background:
        allowed_layers.add("background")
    if include_furniture:
        allowed_layers.add("furniture")

    harvests: list[TableHarvest] = []
    sep_len = len(harvest_separator)

    for table_idx, table_el in enumerate(_walk_tables(root)):
        pieces: list[str] = []
        spans: list[HarvestSpan] = []
        cursor = 0
        if _element_layer(table_el) in allowed_layers:
            thread = _thread_id(table_el)
            layer = _element_layer(table_el)
            for marker, kind, text, row, col in _table_cells(table_el):
                if pieces:
                    cursor += sep_len
                start = cursor
                end = start + len(text)
                spans.append(HarvestSpan(
                    xpath=local_path(marker),
                    thread_id=thread,
                    layer=layer,
                    text=text,
                    start=start,
                    end=end,
                    kind=kind,
                    row_idx=row,
                    col_idx=col,
                ))
                pieces.append(text)
                cursor = end
        harvests.append(TableHarvest(
            table_idx=table_idx,
            marker_xpath=local_path(table_el),
            full_text=harvest_separator.join(pieces),
            spans=tuple(spans),
        ))

    return tuple(harvests)


__all__ = ["harvest_doclang_tables", "harvest_doclang_text"]
