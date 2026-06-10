"""Harvest concatenated text from a parsed DocLang document for RST parsing.

Walks the lxml element tree and emits one ``HarvestSpan`` per text-bearing
unit, addressed by its local-name canonical XPath. Virtual-text container
shapes (``<list>``, ``<table>``, ``<index>``) are partitioned at the
self-closing marker tokens (``<ldiv/>``, ``<fcel/>``, ``<ched/>``, etc.).

Skipped (boundary-only per design):
  - ``<table>`` body (cells excluded from RST input; boundary emitted)
  - ``<index>`` body (same model as table)
  - ``<field_region>`` body (key/value text is structurally distinct)

Off by default (opt-in via knobs):
  - ``<formula>`` — LaTeX; not natural-language prose
  - ``<code>``    — source code; not natural-language prose
  - ``<page_header>`` / ``<page_footer>`` — furniture-by-position
  - ``<layer value="background">`` items
  - ``<layer value="furniture">`` items

Spans are concatenated with ``harvest_separator`` (default ``"\\n\\n"``).
"""

from __future__ import annotations

from collections.abc import Iterable

from lxml import etree

from .loader import local_name, local_path
from .schema import HarvestResult, HarvestSpan

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
    """Produce a concatenated text harvest with per-span xpath mapping.

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
        harvest_separator: inserted between consecutive harvested spans.

    Returns:
        ``HarvestResult`` whose ``full_text`` is the concatenated input
        for the RST parser, and whose ``spans`` map each text range back
        to its source ``xpath`` in document order.
    """
    root = tree.getroot()
    allowed_layers: set[str] = {"body"}
    if include_background:
        allowed_layers.add("background")
    if include_furniture:
        allowed_layers.add("furniture")

    pieces: list[str] = []
    spans: list[HarvestSpan] = []
    cursor = 0
    sep_len = len(harvest_separator)

    def _emit(xpath: str, thread_id: int | None, layer: str, text: str) -> None:
        nonlocal cursor
        if not text:
            return
        if pieces:
            cursor += sep_len
        start = cursor
        end = start + len(text)
        spans.append(HarvestSpan(
            xpath=xpath,
            thread_id=thread_id,
            layer=layer,
            text=text,
            start=start,
            end=end,
        ))
        pieces.append(text)
        cursor = end

    def _thread_id(element: etree._Element) -> int | None:
        for child in element:
            if isinstance(child.tag, str) and local_name(child) == "thread":
                value = child.get("thread_id")
                if value is not None:
                    return int(value)
        return None

    def _walk(element: etree._Element) -> None:
        if not isinstance(element.tag, str):
            return
        tag = local_name(element)

        if tag == "list":
            layer = _element_layer(element)
            if layer in allowed_layers:
                for marker, item_text in _list_items(element):
                    _emit(local_path(marker), _thread_id(element), layer, item_text)
            # nested lists / structural children are handled within _list_items;
            # we still recurse into nested lists for their own boundaries.
            for child in element:
                if isinstance(child.tag, str) and local_name(child) == "list":
                    _walk(child)
            return

        if tag in {"table", "index", "tabular"}:
            # Boundary-only; cells are not harvested as prose.
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
            _emit(local_path(element), _thread_id(element), layer, text)
            return

        if tag == "formula":
            if not include_formulas:
                return
            layer = _element_layer(element)
            if layer not in allowed_layers:
                return
            text = "".join(_prose_itertext(element)).strip()
            _emit(local_path(element), _thread_id(element), layer, text)
            return

        if tag == "code":
            if not include_code_blocks:
                return
            layer = _element_layer(element)
            if layer not in allowed_layers:
                return
            text = "".join(_prose_itertext(element)).strip()
            _emit(local_path(element), _thread_id(element), layer, text)
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
                    _emit(local_path(child), _thread_id(element), layer, caption_text)
            return

        if tag in _HARVEST_AS_BLOCK:
            layer = _element_layer(element)
            if layer not in allowed_layers:
                return
            text = "".join(_prose_itertext(element)).strip()
            _emit(local_path(element), _thread_id(element), layer, text)
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

    return HarvestResult(full_text=harvest_separator.join(pieces), spans=tuple(spans))


__all__ = ["harvest_doclang_text"]
