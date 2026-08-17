"""Harvest text from a DoclingDocument for RST parsing.

Two harvesters:

- ``harvest_docling_text`` — the main document harvest. Walks
  ``doc.iterate_items(traverse_pictures=True, included_content_layers=...)``
  and emits one ``HarvestSpan`` per text-bearing node. ``TableItem`` is
  always skipped here — tables are analysed separately (two-level
  analysis, 2026-06-12 directive Option 2).
- ``harvest_docling_tables`` — one ``TableHarvest`` per ``TableItem``,
  cells in ``data.table_cells`` order with offsets local to that
  table's text. Cell addresses are real JSON pointers
  (``#/tables/N/data/table_cells/M``) that resolve against the source.

Spans are concatenated with ``harvest_separator`` (default ``"\\n\\n"``).
"""

from docling_core.types.doc.document import (
    ContentLayer,
    DoclingDocument,
    PictureItem,
    TableItem,
    TextItem,
)

from .schema import HarvestResult, HarvestSpan, TableHarvest


def _label_value(thing: object) -> str:
    """Return the string value of a Docling enum label, or str(thing)."""
    value = getattr(thing, "value", None)
    return value if isinstance(value, str) else str(thing)


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
    """Produce the main document harvest with per-span self_ref mapping.

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
        ``HarvestResult`` whose ``full_text`` is the document-level input
        for the RST parser, and whose ``spans`` map each text range back
        to its source ``self_ref`` in iteration order. Tables are never
        included — see ``harvest_docling_tables``.
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

    def _emit(self_ref: str, kind: str, text: str) -> None:
        nonlocal cursor
        if pieces:
            cursor += sep_len
        start = cursor
        end = start + len(text)
        spans.append(HarvestSpan(self_ref=self_ref, text=text, start=start, end=end, kind=kind))
        pieces.append(text)
        cursor = end

    for item, _depth in doc.iterate_items(
        traverse_pictures=True,
        included_content_layers=layers,
    ):
        match item:
            case TableItem():
                continue
            case TextItem() if item.text:
                _emit(item.self_ref, _label_value(item.label), item.text)
            case PictureItem() if include_picture_descriptions:
                text = _picture_description(item)
                if text:
                    _emit(item.self_ref, "picture_description", text)
            case _:
                continue

    return HarvestResult(full_text=harvest_separator.join(pieces), spans=tuple(spans))


def harvest_docling_tables(
    doc: DoclingDocument,
    *,
    harvest_separator: str = "\n\n",
) -> tuple[TableHarvest, ...]:
    """Produce one ``TableHarvest`` per ``TableItem``, in ``doc.tables`` order.

    Cell self_refs are real JSON pointers
    (``f"{table.self_ref}/data/table_cells/{idx}"``) so consumers can
    resolve them against the source document. Empty cells produce no
    span but keep their index, so refs stay stable. Offsets are local
    to each table's ``full_text``.
    """
    harvests: list[TableHarvest] = []
    sep_len = len(harvest_separator)

    for table_idx, table in enumerate(doc.tables):
        if not isinstance(table, TableItem):
            continue
        pieces: list[str] = []
        spans: list[HarvestSpan] = []
        cursor = 0
        for cell_idx, cell in enumerate(table.data.table_cells):
            text = (cell.text or "").strip()
            if not text:
                continue
            if pieces:
                cursor += sep_len
            start = cursor
            end = start + len(text)
            spans.append(
                HarvestSpan(
                    self_ref=f"{table.self_ref}/data/table_cells/{cell_idx}",
                    text=text,
                    start=start,
                    end=end,
                    kind="table_header_cell" if cell.column_header else "table_cell",
                    row_idx=cell.start_row_offset_idx,
                    col_idx=cell.start_col_offset_idx,
                )
            )
            pieces.append(text)
            cursor = end
        harvests.append(
            TableHarvest(
                table_idx=table_idx,
                marker_ref=table.self_ref,
                full_text=harvest_separator.join(pieces),
                spans=tuple(spans),
            )
        )

    return tuple(harvests)


__all__ = ["harvest_docling_tables", "harvest_docling_text"]
