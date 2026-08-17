"""Detect structural boundaries in a parsed DocLang document.

Boundaries are emitted from the DocLang structure independently of RST
parsing. The mapper later intersects each boundary's ``xpaths`` with
each RST relation's xpaths to produce ``boundary_memberships``.

Boundary kinds (verified Phase 1 against the 40-fixture corpus):

- ``heading-N`` — each ``<heading>`` owns itself plus following
  harvest-eligible xpaths until the next heading (markdown-style
  section bucketing). Pre-heading content lands in a leading
  ``document`` boundary when non-empty.
- ``page-N``    — content between successive ``<page_break/>`` markers
- ``group-N``   — each top-level ``<group>``; nested groups get
  hierarchical ids (``group-N-M-…`` at arbitrary nesting depth).
- ``table-N``   — each ``<table>``
- ``field_region-N`` — each ``<field_region>``
- ``document``  — fallback boundary covering all harvest-eligible
  elements when none of the above apply; also used for pre-heading
  content when headings are present.

DocLang has no slide / speaker-turn concepts (Phase 0 verified) — those
kinds are absent by design.
"""

from collections.abc import Iterable

from lxml import etree

from .harvester import reject_nested_tables
from .loader import local_name, local_path
from .schema import Boundary


def _walk_descendants(element: etree._Element) -> Iterable[etree._Element]:
    """Yield ``element`` and every descendant in document order."""
    yield element
    for child in element:
        if isinstance(child.tag, str):
            yield from _walk_descendants(child)


def _harvest_eligible_xpaths(
    root: etree._Element,
    *,
    include_code_blocks: bool = False,
    include_formulas: bool = False,
    include_field_regions: bool = False,
) -> tuple[str, ...]:
    """Yield xpaths of every harvest-eligible element under ``root``.

    Mirrors the harvester's coverage for the default / opt-in knobs used by
    ``detect_boundaries``. Default tags: ``text``, ``heading``, ``footnote``,
    ``ldiv``, picture ``caption``. Opt-in: ``code``, ``formula``, ``key`` /
    ``value`` under ``field_region``.
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
        elif tag == "code" and include_code_blocks:
            xpaths.append(local_path(el))
        elif tag == "formula" and include_formulas:
            xpaths.append(local_path(el))
        elif tag in {"key", "value"} and include_field_regions:
            xpaths.append(local_path(el))
    return tuple(xpaths)


def _detect_heading_boundaries(
    root: etree._Element,
    *,
    include_code_blocks: bool = False,
    include_formulas: bool = False,
    include_field_regions: bool = False,
) -> list[Boundary]:
    """Emit ``heading-N`` boundaries with markdown-style section bucketing.

    Document-order harvest-eligible xpaths are partitioned so each
    heading owns itself plus every following eligible xpath until the
    next heading. Content before the first heading lands in a leading
    ``document`` boundary when non-empty. The ``label`` carries the
    heading's text; the ``level`` carries its ``level`` attribute
    (default 1 per spec).
    """
    heading_meta: dict[str, tuple[str | None, int]] = {}
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
        heading_meta[local_path(el)] = (label, level)

    if not heading_meta:
        return []

    eligible = _harvest_eligible_xpaths(
        root,
        include_code_blocks=include_code_blocks,
        include_formulas=include_formulas,
        include_field_regions=include_field_regions,
    )

    # Buckets: [(None, pre-heading refs), (heading_xpath, section refs), ...]
    buckets: list[tuple[str | None, list[str]]] = [(None, [])]
    for xp in eligible:
        if xp in heading_meta:
            buckets.append((xp, [xp]))
        else:
            buckets[-1][1].append(xp)

    boundaries: list[Boundary] = []
    pre_refs = buckets[0][1]
    if pre_refs:
        boundaries.append(
            Boundary(
                id="document",
                kind="document",
                label=None,
                parent_xpath=local_path(root),
                xpaths=tuple(pre_refs),
            )
        )

    heading_idx = 0
    for heading_xp, refs in buckets[1:]:
        assert heading_xp is not None
        label, level = heading_meta[heading_xp]
        boundaries.append(
            Boundary(
                id=f"heading-{heading_idx}",
                kind="heading",
                label=label,
                parent_xpath=None,
                xpaths=tuple(refs),
                level=level,
            )
        )
        heading_idx += 1
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
    """Emit ``group-N`` / ``group-N-M-…`` boundaries at any nesting depth.

    Top-level here means a direct child of ``<doclang>``. Nested groups
    receive hierarchical ids appended with ``-M`` for each nesting level.
    """
    boundaries: list[Boundary] = []

    def _walk_groups(parent: etree._Element, id_parts: list[int]) -> None:
        idx = 0
        for child in parent:
            if not isinstance(child.tag, str) or local_name(child) != "group":
                continue
            parts = [*id_parts, idx]
            group_id = "group-" + "-".join(str(p) for p in parts)
            boundaries.append(
                Boundary(
                    id=group_id,
                    kind="group",
                    label=None,
                    parent_xpath=local_path(parent),
                    xpaths=_harvest_eligible_xpaths(child),
                )
            )
            _walk_groups(child, parts)
            idx += 1

    _walk_groups(root, [])
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
    """Emit one ``field_region-N`` boundary per ``<field_region>``.

    ``xpaths`` include the region itself plus every descendant ``key`` /
    ``value`` path the harvester emits when ``include_field_regions=True``,
    so mapper set-intersection can attach ``field_region-*`` memberships.
    """
    boundaries: list[Boundary] = []
    idx = 0
    for el in _walk_descendants(root):
        if not isinstance(el.tag, str) or local_name(el) != "field_region":
            continue
        parent = el.getparent()
        parent_xpath = local_path(parent) if parent is not None else None
        member_xpaths = [local_path(el)]
        for desc in _walk_descendants(el):
            if desc is el or not isinstance(desc.tag, str):
                continue
            if local_name(desc) in {"key", "value"}:
                member_xpaths.append(local_path(desc))
        boundaries.append(
            Boundary(
                id=f"field_region-{idx}",
                kind="field_region",
                label=None,
                parent_xpath=parent_xpath,
                xpaths=tuple(member_xpaths),
            )
        )
        idx += 1
    return boundaries


def _detect_document_fallback(
    root: etree._Element,
    *,
    include_code_blocks: bool = False,
    include_formulas: bool = False,
    include_field_regions: bool = False,
) -> list[Boundary]:
    """Emit a single ``document`` boundary covering every harvest-eligible xpath."""
    xpaths = _harvest_eligible_xpaths(
        root,
        include_code_blocks=include_code_blocks,
        include_formulas=include_formulas,
        include_field_regions=include_field_regions,
    )
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


def detect_boundaries(
    tree: etree._ElementTree,
    *,
    include_code_blocks: bool = False,
    include_formulas: bool = False,
    include_field_regions: bool = False,
) -> tuple[Boundary, ...]:
    """Detect every structural boundary in ``tree``.

    Always emits ``table-N`` and ``field_region-N`` boundaries when those
    elements exist. Emits all applicable of the ``heading-N``, ``page-N``,
    and ``group-N`` sets (they are not mutually exclusive). If none of
    those three apply, falls back to a single ``document`` boundary
    covering the harvest-eligible elements.

    Opt-in harvest knobs (``include_code_blocks`` / ``include_formulas`` /
    ``include_field_regions``) widen heading / document eligibility so
    boundary memberships stay aligned with the harvester.
    """
    root = tree.getroot()
    reject_nested_tables(root)

    primary: list[Boundary] = []
    primary.extend(
        _detect_heading_boundaries(
            root,
            include_code_blocks=include_code_blocks,
            include_formulas=include_formulas,
            include_field_regions=include_field_regions,
        )
    )
    primary.extend(_detect_page_boundaries(root))
    primary.extend(_detect_group_boundaries(root))
    if not primary:
        primary.extend(
            _detect_document_fallback(
                root,
                include_code_blocks=include_code_blocks,
                include_formulas=include_formulas,
                include_field_regions=include_field_regions,
            )
        )

    tables = _detect_table_boundaries(root)
    fields = _detect_field_region_boundaries(root)

    return tuple(primary) + tuple(tables) + tuple(fields)
