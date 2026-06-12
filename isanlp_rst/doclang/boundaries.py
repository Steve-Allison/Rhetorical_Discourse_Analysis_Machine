"""Detect structural boundaries in a parsed DocLang document.

Boundaries are emitted from the DocLang structure independently of RST
parsing. The mapper later intersects each boundary's ``xpaths`` with
each RST relation's xpaths to produce ``boundary_memberships``.

Boundary kinds (verified Phase 1 against the 40-fixture corpus):

- ``heading-N`` — each top-level ``<heading>``, indexed in document order
- ``page-N``    — content between successive ``<page_break/>`` markers
- ``group-N``   — each top-level ``<group>``; nested groups get
  hierarchical ids (``group-N-M`` for one level of nesting; deeper
  nesting was not observed in the corpus and is left as a follow-up).
- ``table-N``   — each ``<table>``
- ``field_region-N`` — each ``<field_region>``
- ``document``  — fallback boundary covering all harvest-eligible
  elements when none of the above apply.

DocLang has no slide / speaker-turn concepts (Phase 0 verified) — those
kinds are absent by design.
"""

from __future__ import annotations

from collections.abc import Iterable

from lxml import etree

from .loader import local_name, local_path
from .schema import Boundary


def _walk_descendants(element: etree._Element) -> Iterable[etree._Element]:
    """Yield ``element`` and every descendant in document order."""
    yield element
    for child in element:
        if isinstance(child.tag, str):
            yield from _walk_descendants(child)


def _harvest_eligible_xpaths(root: etree._Element) -> tuple[str, ...]:
    """Yield xpaths of every harvest-eligible element under ``root``.

    Mirrors the harvester's coverage: ``<text>``, ``<heading>``,
    ``<footnote>``, ``<list>`` items (via the ``<ldiv/>`` marker), and
    ``<picture>``'s caption. Used to populate the ``document`` fallback
    boundary when no structural boundaries match.
    """
    xpaths: list[str] = []
    for el in _walk_descendants(root):
        if not isinstance(el.tag, str):
            continue
        tag = local_name(el)
        if tag in {"text", "heading", "footnote"}:
            xpaths.append(local_path(el))
        elif tag == "ldiv":
            xpaths.append(local_path(el))
        elif tag == "caption":
            parent = el.getparent()
            if parent is not None and local_name(parent) == "picture":
                xpaths.append(local_path(el))
    return tuple(xpaths)


def _detect_heading_boundaries(root: etree._Element) -> list[Boundary]:
    """Emit one ``heading-N`` boundary per ``<heading>``, in document order.

    The boundary's ``xpaths`` is the heading itself plus every
    harvest-eligible element under it (which, since headings cannot
    contain block-level descendants in practice, is usually just the
    heading). The ``label`` carries the heading's text; the ``level``
    carries its ``level`` attribute (default 1 per spec).
    """
    boundaries: list[Boundary] = []
    idx = 0
    for el in _walk_descendants(root):
        if not isinstance(el.tag, str) or local_name(el) != "heading":
            continue
        level_str = el.get("level", "1")
        try:
            level = int(level_str)
        except ValueError as exc:
            raise ValueError(
                f"<heading> at {local_path(el)} has non-integer level={level_str!r}"
            ) from exc
        label = "".join(el.itertext()).strip() or None
        boundaries.append(
            Boundary(
                id=f"heading-{idx}",
                kind="heading",
                label=label,
                parent_xpath=None,
                xpaths=(local_path(el),),
                level=level,
            )
        )
        idx += 1
    return boundaries


def _detect_page_boundaries(root: etree._Element) -> list[Boundary]:
    """Emit one ``page-N`` boundary per ``<page_break/>``-delimited region.

    Spec restricts ``<page_break/>`` to children of ``<doclang>``. Returns
    ``[]`` when no breaks are present.
    """
    body = list(root)
    break_positions: list[int] = [
        i for i, child in enumerate(body)
        if isinstance(child.tag, str) and local_name(child) == "page_break"
    ]
    if not break_positions:
        return []

    pages: list[list[etree._Element]] = []
    start = 0
    for pos in break_positions:
        pages.append(body[start:pos])
        start = pos + 1
    pages.append(body[start:])

    boundaries: list[Boundary] = []
    for page_idx, page_children in enumerate(pages):
        xpaths: list[str] = []
        for child in page_children:
            for el in _walk_descendants(child):
                if not isinstance(el.tag, str):
                    continue
                tag = local_name(el)
                if tag in {"text", "heading", "footnote"}:
                    xpaths.append(local_path(el))
                elif tag == "ldiv":
                    xpaths.append(local_path(el))
                elif tag == "caption":
                    parent = el.getparent()
                    if parent is not None and local_name(parent) == "picture":
                        xpaths.append(local_path(el))
        boundaries.append(
            Boundary(
                id=f"page-{page_idx}",
                kind="page",
                label=None,
                parent_xpath=None,
                xpaths=tuple(xpaths),
                page_no=page_idx,
            )
        )
    return boundaries


def _detect_group_boundaries(root: etree._Element) -> list[Boundary]:
    """Emit one ``group-N`` boundary per top-level ``<group>``.

    Top-level here means a direct child of ``<doclang>``. Nested groups
    are surfaced as ``group-N-M`` (one level deep — the only depth
    observed in the Phase 1 corpus).
    """
    boundaries: list[Boundary] = []
    idx = 0
    for child in root:
        if not isinstance(child.tag, str) or local_name(child) != "group":
            continue
        outer_id = f"group-{idx}"
        boundaries.append(
            Boundary(
                id=outer_id,
                kind="group",
                label=None,
                parent_xpath=local_path(root),
                xpaths=_harvest_eligible_xpaths(child),
            )
        )
        inner_idx = 0
        for inner in child:
            if not isinstance(inner.tag, str) or local_name(inner) != "group":
                continue
            boundaries.append(
                Boundary(
                    id=f"{outer_id}-{inner_idx}",
                    kind="group",
                    label=None,
                    parent_xpath=local_path(child),
                    xpaths=_harvest_eligible_xpaths(inner),
                )
            )
            inner_idx += 1
        idx += 1
    return boundaries


def _detect_table_boundaries(root: etree._Element) -> list[Boundary]:
    """Emit one ``table-N`` boundary per ``<table>``, in document order.

    ``xpaths`` is ``(table_xpath, cell_marker_xpath_0, …)`` — the table
    element's own xpath is the synthetic boundary marker (no harvest span
    carries it, so it cannot land in relation refs), followed by each
    cell marker's xpath. Empty-by-grammar ``<ecel/>`` cells are skipped
    here too — the harvester would emit no span for them, so their
    xpaths in the boundary would never match.
    """
    boundaries: list[Boundary] = []
    idx = 0
    cell_markers = {"ched", "fcel", "rhed", "corn"}
    for el in _walk_descendants(root):
        if not isinstance(el.tag, str) or local_name(el) != "table":
            continue
        parent = el.getparent()
        parent_xpath = local_path(parent) if parent is not None else None
        cell_xpaths: list[str] = []
        for child in el:
            if not isinstance(child.tag, str):
                continue
            if local_name(child) in cell_markers:
                cell_xpaths.append(local_path(child))
        boundaries.append(
            Boundary(
                id=f"table-{idx}",
                kind="table",
                label=None,
                parent_xpath=parent_xpath,
                xpaths=(local_path(el), *cell_xpaths),
            )
        )
        idx += 1
    return boundaries


def _detect_field_region_boundaries(root: etree._Element) -> list[Boundary]:
    """Emit one ``field_region-N`` boundary per ``<field_region>``."""
    boundaries: list[Boundary] = []
    idx = 0
    for el in _walk_descendants(root):
        if not isinstance(el.tag, str) or local_name(el) != "field_region":
            continue
        parent = el.getparent()
        parent_xpath = local_path(parent) if parent is not None else None
        boundaries.append(
            Boundary(
                id=f"field_region-{idx}",
                kind="field_region",
                label=None,
                parent_xpath=parent_xpath,
                xpaths=(local_path(el),),
            )
        )
        idx += 1
    return boundaries


def _detect_document_fallback(root: etree._Element) -> list[Boundary]:
    """Emit a single ``document`` boundary covering every harvest-eligible xpath."""
    xpaths = _harvest_eligible_xpaths(root)
    if not xpaths:
        return []
    return [
        Boundary(
            id="document",
            kind="document",
            label=None,
            parent_xpath=local_path(root),
            xpaths=xpaths,
        )
    ]


def detect_boundaries(tree: etree._ElementTree) -> tuple[Boundary, ...]:
    """Detect every structural boundary in ``tree``.

    Always emits ``table-N`` and ``field_region-N`` boundaries when those
    elements exist. Emits one of (``heading-N`` set, ``page-N`` set,
    ``group-N`` set) per the structural shape; if none apply, falls back
    to a single ``document`` boundary covering the harvest-eligible
    elements.
    """
    root = tree.getroot()

    primary: list[Boundary] = []
    primary.extend(_detect_heading_boundaries(root))
    primary.extend(_detect_page_boundaries(root))
    primary.extend(_detect_group_boundaries(root))
    if not primary:
        primary.extend(_detect_document_fallback(root))

    tables = _detect_table_boundaries(root)
    fields = _detect_field_region_boundaries(root)

    return tuple(primary) + tuple(tables) + tuple(fields)
