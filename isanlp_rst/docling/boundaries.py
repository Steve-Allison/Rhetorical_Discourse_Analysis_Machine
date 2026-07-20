"""Detect structural boundaries in a DoclingDocument.

Boundaries are emitted from the Docling structure independently of RST
parsing. The mapper later intersects each boundary's ``self_refs`` with
each RST relation's refs to produce ``boundary_memberships``.

Dispatch on ``doc.origin.mimetype``:

- PPTX (either MS or OpenXML mimetype) → slide-group detection. Walks
  ``doc.groups`` for entries with ``label == "chapter"`` and ``name``
  starting with ``"slide-"``. Each emits one ``slide-N`` boundary; if
  any of its children land in ``ContentLayer.NOTES`` an additional
  ``slide-N-notes`` boundary is emitted over just those refs (when
  ``include_slide_notes`` is True).
- ``text/vtt`` → speaker-turn detection. Walks TextItems in iteration
  order; contiguous same-voice runs coalesce into one ``turn-K``
  boundary when ``coalesce_speaker_turns`` (default).
- ``application/pdf``, ``text/markdown``, ``text/html`` → section
  detection. Opens a new ``section-N`` boundary at each
  ``SectionHeaderItem``; any pre-header content lives in a leading
  ``document`` boundary.
- anything else → a single ``document`` boundary covering all
  text/picture self_refs.

Every source format also emits one ``table-N`` boundary per ``TableItem``.

``include_slide_notes`` / ``include_furniture`` must match the harvester
knobs so boundary memberships only cover content that was actually parsed.
"""

from __future__ import annotations

from collections.abc import Iterable

from docling_core.types.doc.document import (
    ContentLayer,
    DoclingDocument,
    PictureItem,
    SectionHeaderItem,
    TableItem,
    TextItem,
    TitleItem,
)

from .schema import Boundary

PPTX_MIMETYPES = frozenset({
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
})
SECTION_MIMETYPES = frozenset({
    "application/pdf",
    "text/markdown",
    "text/html",
})
VTT_MIMETYPE = "text/vtt"


def _content_layers(
    *,
    include_slide_notes: bool,
    include_furniture: bool,
) -> set[ContentLayer]:
    layers: set[ContentLayer] = {ContentLayer.BODY}
    if include_slide_notes:
        layers.add(ContentLayer.NOTES)
    if include_furniture:
        layers.add(ContentLayer.FURNITURE)
    return layers


def _layer_allowed(item: object, layers: set[ContentLayer]) -> bool:
    layer = getattr(item, "content_layer", None)
    if layer is None:
        return True
    return layer in layers


def detect_boundaries(
    doc: DoclingDocument,
    *,
    coalesce_speaker_turns: bool = True,
    include_slide_notes: bool = True,
    include_furniture: bool = False,
) -> tuple[Boundary, ...]:
    """Detect boundaries in ``doc`` based on its origin mimetype.

    ``include_slide_notes`` / ``include_furniture`` mirror
    ``harvest_docling_text`` so memberships stay aligned with the parse.
    """
    layers = _content_layers(
        include_slide_notes=include_slide_notes,
        include_furniture=include_furniture,
    )
    mimetype = (doc.origin.mimetype if doc.origin else "") or ""

    if mimetype in PPTX_MIMETYPES:
        primary: list[Boundary] = _detect_pptx_slide_boundaries(
            doc,
            include_slide_notes=include_slide_notes,
            include_furniture=include_furniture,
        )
    elif mimetype == VTT_MIMETYPE:
        primary = _detect_vtt_turn_boundaries(
            doc, coalesce=coalesce_speaker_turns, layers=layers
        )
    elif mimetype in SECTION_MIMETYPES:
        primary = _detect_section_boundaries(doc, layers=layers)
    else:
        primary = _single_document_boundary(doc, layers=layers)

    tables = _detect_table_boundaries(doc)
    return tuple(primary) + tables


# --- helpers ---------------------------------------------------------------


def _label_value(thing: object) -> str:
    """Return the string value of a Docling enum label, or str(thing)."""
    value = getattr(thing, "value", None)
    return value if isinstance(value, str) else str(thing)


def _iter_body_self_refs(
    doc: DoclingDocument, *, layers: set[ContentLayer]
) -> Iterable[str]:
    """Yield self_refs of TextItem and PictureItem in iteration order."""
    for item, _depth in doc.iterate_items(
        traverse_pictures=True,
        included_content_layers=layers,
    ):
        if isinstance(item, (TextItem, PictureItem)):
            yield item.self_ref


# --- PPTX ------------------------------------------------------------------


def _detect_pptx_slide_boundaries(
    doc: DoclingDocument,
    *,
    include_slide_notes: bool,
    include_furniture: bool,
) -> list[Boundary]:
    layers = _content_layers(
        include_slide_notes=include_slide_notes,
        include_furniture=include_furniture,
    )
    boundaries: list[Boundary] = []
    for group in doc.groups:
        if _label_value(group.label) != "chapter":
            continue
        if not group.name.startswith("slide-"):
            continue

        slide_refs: list[str] = []
        notes_refs: list[str] = []
        slide_label: str | None = None

        for child_ref in group.children:
            try:
                child = child_ref.resolve(doc)
            except (AttributeError, LookupError, TypeError, ValueError, RuntimeError):
                continue
            if not _layer_allowed(child, layers):
                continue
            self_ref = getattr(child, "self_ref", None)
            if self_ref is None:
                continue
            slide_refs.append(self_ref)
            if slide_label is None and isinstance(child, TitleItem):
                slide_label = child.text or None
            if getattr(child, "content_layer", None) == ContentLayer.NOTES:
                notes_refs.append(self_ref)

        boundaries.append(
            Boundary(
                id=group.name,
                kind="slide",
                label=slide_label,
                parent_self_ref=group.self_ref,
                self_refs=tuple(slide_refs),
            )
        )
        if include_slide_notes and notes_refs:
            boundaries.append(
                Boundary(
                    id=f"{group.name}-notes",
                    kind="slide-notes",
                    label=None,
                    parent_self_ref=group.self_ref,
                    self_refs=tuple(notes_refs),
                )
            )

    return boundaries


# --- VTT -------------------------------------------------------------------


def _detect_vtt_turn_boundaries(
    doc: DoclingDocument, *, coalesce: bool, layers: set[ContentLayer]
) -> list[Boundary]:
    boundaries: list[Boundary] = []
    current_voice: str | None = None
    current_refs: list[str] = []
    turn_idx = 0

    def _emit() -> None:
        nonlocal turn_idx, current_refs
        if not current_refs:
            return
        boundaries.append(
            Boundary(
                id=f"turn-{turn_idx}",
                kind="turn",
                label=current_voice,
                parent_self_ref=None,
                self_refs=tuple(current_refs),
            )
        )
        turn_idx += 1
        current_refs = []

    for item, _depth in doc.iterate_items(
        traverse_pictures=True,
        included_content_layers=layers,
    ):
        if not isinstance(item, TextItem):
            continue
        source = getattr(item, "source", None) or []
        voice = getattr(source[0], "voice", None) if source else None

        if current_refs and (not coalesce or voice != current_voice):
            _emit()
        current_voice = voice
        current_refs.append(item.self_ref)

    _emit()
    return boundaries


# --- Section-based formats (PDF / Markdown / HTML) -------------------------


def _detect_section_boundaries(
    doc: DoclingDocument, *, layers: set[ContentLayer]
) -> list[Boundary]:
    # Buckets: first entry is the implicit pre-header "document" bucket;
    # each subsequent entry is one section opened by a SectionHeaderItem.
    buckets: list[tuple[str | None, int | None, list[str]]] = [(None, None, [])]

    for item, _depth in doc.iterate_items(
        traverse_pictures=True,
        included_content_layers=layers,
    ):
        if isinstance(item, SectionHeaderItem):
            buckets.append((item.text or None, getattr(item, "level", None), [item.self_ref]))
        elif isinstance(item, (TextItem, PictureItem)):
            buckets[-1][2].append(item.self_ref)

    boundaries: list[Boundary] = []
    document_label, _document_level, document_refs = buckets[0]
    if document_refs:
        boundaries.append(
            Boundary(
                id="document",
                kind="document",
                label=document_label,
                parent_self_ref=None,
                self_refs=tuple(document_refs),
            )
        )
    for i, (label, level, refs) in enumerate(buckets[1:]):
        boundaries.append(
            Boundary(
                id=f"section-{i}",
                kind="section",
                label=label,
                parent_self_ref=None,
                self_refs=tuple(refs),
                level=level,
            )
        )
    return boundaries


# --- Default fallback ------------------------------------------------------


def _single_document_boundary(
    doc: DoclingDocument, *, layers: set[ContentLayer]
) -> list[Boundary]:
    refs = tuple(_iter_body_self_refs(doc, layers=layers))
    if not refs:
        return []
    return [
        Boundary(
            id="document",
            kind="document",
            label=None,
            parent_self_ref=None,
            self_refs=refs,
        )
    ]


# --- Tables (every format) -------------------------------------------------


def _detect_table_boundaries(doc: DoclingDocument) -> tuple[Boundary, ...]:
    """Emit one ``table-N`` boundary per ``TableItem``.

    Indexing matches ``harvest_docling_tables`` (``enumerate(doc.tables)``).
    Layer knobs do not drop tables here — table mini-parses are gated by
    ``include_table_cells`` on the entry point, not content-layer filters.
    """
    out: list[Boundary] = []
    for i, table in enumerate(doc.tables):
        if not isinstance(table, TableItem):
            continue
        parent_ref = None
        parent = getattr(table, "parent", None)
        if parent is not None:
            parent_ref = getattr(parent, "cref", None)
        cell_refs = tuple(
            f"{table.self_ref}/data/table_cells/{idx}"
            for idx in range(len(table.data.table_cells))
        )
        out.append(
            Boundary(
                id=f"table-{i}",
                kind="table",
                label=None,
                parent_self_ref=parent_ref,
                self_refs=(table.self_ref, *cell_refs),
            )
        )
    return tuple(out)
