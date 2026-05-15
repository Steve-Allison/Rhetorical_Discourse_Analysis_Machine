"""Harvest concatenated text from a DoclingDocument for RST parsing.

Walks ``doc.iterate_items(traverse_pictures=True, included_content_layers=...)``
and emits one ``HarvestSpan`` per text-bearing node:

- ``TextItem`` → ``.text`` (normalised form; bullet markers etc. stripped
  by Docling — see plan §Decisions: TextItem.text vs TextItem.orig).
- ``PictureItem`` → ``picture.meta.description.text`` when present and
  ``include_picture_descriptions=True``.
- ``TableItem`` → skipped. Tables are structurally grids; their cells do
  not enter the RST input. They are surfaced by ``detect_boundaries``.

Spans are concatenated with ``harvest_separator`` (default ``"\\n\\n"``).
"""

from __future__ import annotations

from docling_core.types.doc.document import (
    ContentLayer,
    DoclingDocument,
    PictureItem,
    TableItem,
    TextItem,
)

from .schema import HarvestResult, HarvestSpan


def _picture_description(picture: PictureItem) -> str | None:
    """Return ``picture.meta.description.text`` when present and non-empty."""
    meta = getattr(picture, "meta", None)
    if meta is None:
        return None
    description = getattr(meta, "description", None)
    if description is None:
        return None
    text = getattr(description, "text", None)
    if isinstance(text, str) and text.strip():
        return text
    return None


def harvest_docling_text(
    doc: DoclingDocument,
    *,
    include_picture_descriptions: bool = True,
    include_slide_notes: bool = True,
    include_furniture: bool = False,
    harvest_separator: str = "\n\n",
) -> HarvestResult:
    """Produce a concatenated text harvest with per-span self_ref mapping.

    Args:
        doc: a loaded ``DoclingDocument``.
        include_picture_descriptions: include each picture's
            ``meta.description.text`` when present.
        include_slide_notes: include items in ``ContentLayer.NOTES``
            (PPTX speaker notes).
        include_furniture: include items in ``ContentLayer.FURNITURE``
            (page headers / footers; typically boilerplate).
        harvest_separator: inserted between consecutive harvested spans.

    Returns:
        ``HarvestResult`` whose ``full_text`` is the concatenated input
        for the RST parser, and whose ``spans`` map each text range back
        to its source ``self_ref`` in iteration order.
    """
    layers: set[ContentLayer] = {ContentLayer.BODY}
    if include_slide_notes:
        layers.add(ContentLayer.NOTES)
    if include_furniture:
        layers.add(ContentLayer.FURNITURE)

    pieces: list[str] = []
    spans: list[HarvestSpan] = []
    cursor = 0
    sep_len = len(harvest_separator)

    for item, _depth in doc.iterate_items(
        traverse_pictures=True,
        included_content_layers=layers,
    ):
        text: str | None
        if isinstance(item, TextItem):
            text = item.text or None
        elif isinstance(item, PictureItem):
            text = _picture_description(item) if include_picture_descriptions else None
        elif isinstance(item, TableItem):
            continue
        else:
            continue

        if not text:
            continue

        if pieces:
            cursor += sep_len
        start = cursor
        end = start + len(text)
        spans.append(HarvestSpan(self_ref=item.self_ref, text=text, start=start, end=end))
        pieces.append(text)
        cursor = end

    return HarvestResult(full_text=harvest_separator.join(pieces), spans=tuple(spans))
