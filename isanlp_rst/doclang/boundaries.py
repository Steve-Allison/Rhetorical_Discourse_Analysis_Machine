"""Detect DocLang boundaries from the exact shared harvest eligibility policy."""

from collections.abc import Iterable

from lxml import etree

from .eligibility import DoclangEligibility
from .harvester import harvest_doclang_tables, harvest_doclang_text, reject_nested_tables
from .loader import local_name, local_path
from .schema import Boundary, HarvestResult, TableHarvest
from .text_walker import body_text


def _walk_descendants(element: etree._Element) -> Iterable[etree._Element]:
    """Yield ``element`` and descendants in document order."""

    yield element
    for child in element:
        if isinstance(child.tag, str):
            yield from _walk_descendants(child)


def _resolve_policy(
    eligibility: DoclangEligibility | None,
    *,
    include_picture_captions: bool = True,
    include_background: bool = False,
    include_furniture: bool = False,
    include_field_regions: bool = False,
    include_code_blocks: bool = False,
    include_formulas: bool = False,
    include_table_cells: bool = True,
) -> DoclangEligibility:
    """Resolve legacy keyword switches into the shared immutable policy."""

    if eligibility is not None:
        return eligibility
    return DoclangEligibility(
        include_picture_captions=include_picture_captions,
        include_background=include_background,
        include_furniture=include_furniture,
        include_field_regions=include_field_regions,
        include_code_blocks=include_code_blocks,
        include_formulas=include_formulas,
        include_table_cells=include_table_cells,
    )


def _harvest_eligible_xpaths(
    root: etree._Element,
    *,
    include_picture_captions: bool = True,
    include_background: bool = False,
    include_furniture: bool = False,
    include_code_blocks: bool = False,
    include_formulas: bool = False,
    include_field_regions: bool = False,
    eligibility: DoclangEligibility | None = None,
) -> tuple[str, ...]:
    """Return the exact main-harvest paths admitted by the shared policy."""

    policy = _resolve_policy(
        eligibility,
        include_picture_captions=include_picture_captions,
        include_background=include_background,
        include_furniture=include_furniture,
        include_code_blocks=include_code_blocks,
        include_formulas=include_formulas,
        include_field_regions=include_field_regions,
    )
    harvest = harvest_doclang_text(root.getroottree(), eligibility=policy)
    return tuple(span.xpath for span in harvest.spans)


def _is_within(xpath: str, ancestor_xpath: str) -> bool:
    """Return whether ``xpath`` addresses ``ancestor_xpath`` or its descendant."""

    return xpath == ancestor_xpath or xpath.startswith(f"{ancestor_xpath}/")


def _detect_heading_boundaries(
    root: etree._Element,
    eligible: tuple[str, ...],
    policy: DoclangEligibility,
) -> list[Boundary]:
    """Partition exact harvested paths into metadata-aware heading sections."""

    if not policy.include_heading_boundaries:
        return []
    heading_meta: dict[str, tuple[str | None, int]] = {}
    eligible_set = set(eligible)
    for element in _walk_descendants(root):
        if not isinstance(element.tag, str) or local_name(element) != "heading":
            continue
        xpath = local_path(element)
        if xpath not in eligible_set:
            continue
        level_text = element.get("level", "1")
        try:
            level = int(level_text)
        except ValueError as exc:
            raise ValueError(f"<heading> at {xpath} has non-integer level={level_text!r}") from exc
        heading_meta[xpath] = (body_text(element) or None, level)
    if not heading_meta:
        return []

    buckets: list[tuple[str | None, list[str]]] = [(None, [])]
    for xpath in eligible:
        if xpath in heading_meta:
            buckets.append((xpath, [xpath]))
        else:
            buckets[-1][1].append(xpath)

    boundaries: list[Boundary] = []
    if buckets[0][1]:
        boundaries.append(
            Boundary(
                id="document",
                kind="document",
                label=None,
                parent_xpath=local_path(root),
                xpaths=tuple(buckets[0][1]),
            )
        )
    for heading_idx, (heading_xpath, paths) in enumerate(buckets[1:]):
        if heading_xpath is None:
            raise RuntimeError("heading bucket is missing its heading path")
        label, level = heading_meta[heading_xpath]
        boundaries.append(
            Boundary(
                id=f"heading-{heading_idx}",
                kind="heading",
                label=label,
                parent_xpath=None,
                xpaths=tuple(paths),
                level=level,
            )
        )
    return boundaries


def _detect_page_boundaries(
    root: etree._Element,
    eligible: tuple[str, ...],
    policy: DoclangEligibility,
) -> list[Boundary]:
    """Emit exact-harvest page partitions around top-level page breaks."""

    if not policy.include_page_boundaries:
        return []
    body = list(root)
    break_positions = [
        index
        for index, child in enumerate(body)
        if isinstance(child.tag, str) and local_name(child) == "page_break"
    ]
    if not break_positions:
        return []
    pages: list[list[etree._Element]] = []
    start = 0
    for position in break_positions:
        pages.append(body[start:position])
        start = position + 1
    pages.append(body[start:])

    boundaries: list[Boundary] = []
    for page_idx, children in enumerate(pages):
        roots = tuple(local_path(child) for child in children if isinstance(child.tag, str))
        paths = tuple(xpath for xpath in eligible if any(_is_within(xpath, root_path) for root_path in roots))
        boundaries.append(
            Boundary(
                id=f"page-{page_idx}",
                kind="page",
                label=None,
                parent_xpath=None,
                xpaths=paths,
                page_no=page_idx,
            )
        )
    return boundaries


def _detect_group_boundaries(
    root: etree._Element,
    eligible: tuple[str, ...],
    policy: DoclangEligibility,
) -> list[Boundary]:
    """Emit arbitrary-depth group boundaries over exact harvested paths."""

    if not policy.include_group_boundaries:
        return []
    boundaries: list[Boundary] = []

    def walk_groups(parent: etree._Element, id_parts: tuple[int, ...]) -> None:
        group_index = 0
        for child in parent:
            if not isinstance(child.tag, str) or local_name(child) != "group":
                continue
            parts = (*id_parts, group_index)
            group_xpath = local_path(child)
            boundaries.append(
                Boundary(
                    id="group-" + "-".join(str(part) for part in parts),
                    kind="group",
                    label=None,
                    parent_xpath=local_path(parent),
                    xpaths=tuple(xpath for xpath in eligible if _is_within(xpath, group_xpath)),
                )
            )
            walk_groups(child, parts)
            group_index += 1

    walk_groups(root, ())
    return boundaries


def _detect_table_boundaries(
    root: etree._Element,
    table_harvests: tuple[TableHarvest, ...],
) -> list[Boundary]:
    """Emit table markers plus exactly the harvested cell paths."""

    tables = [
        element
        for element in _walk_descendants(root)
        if isinstance(element.tag, str) and local_name(element) == "table"
    ]
    if len(tables) != len(table_harvests):
        raise RuntimeError("table boundary and harvest counts disagree")
    boundaries: list[Boundary] = []
    for table_idx, (element, table_harvest) in enumerate(zip(tables, table_harvests, strict=True)):
        parent = element.getparent()
        boundaries.append(
            Boundary(
                id=f"table-{table_idx}",
                kind="table",
                label=None,
                parent_xpath=local_path(parent) if parent is not None else None,
                xpaths=(local_path(element), *(span.xpath for span in table_harvest.spans)),
            )
        )
    return boundaries


def _detect_field_region_boundaries(
    root: etree._Element,
    eligible: tuple[str, ...],
) -> list[Boundary]:
    """Emit field-region markers plus exactly harvested descendant paths."""

    boundaries: list[Boundary] = []
    regions = [
        element
        for element in _walk_descendants(root)
        if isinstance(element.tag, str) and local_name(element) == "field_region"
    ]
    for region_idx, element in enumerate(regions):
        xpath = local_path(element)
        parent = element.getparent()
        boundaries.append(
            Boundary(
                id=f"field_region-{region_idx}",
                kind="field_region",
                label=None,
                parent_xpath=local_path(parent) if parent is not None else None,
                xpaths=(xpath, *(path for path in eligible if _is_within(path, xpath))),
            )
        )
    return boundaries


def _detect_document_fallback(root: etree._Element, eligible: tuple[str, ...]) -> list[Boundary]:
    """Emit a single exact-harvest document boundary when non-empty."""

    if not eligible:
        return []
    return [
        Boundary(
            id="document",
            kind="document",
            label=None,
            parent_xpath=local_path(root),
            xpaths=eligible,
        )
    ]


def detect_boundaries(
    tree: etree._ElementTree,
    *,
    include_picture_captions: bool = True,
    include_background: bool = False,
    include_furniture: bool = False,
    include_code_blocks: bool = False,
    include_formulas: bool = False,
    include_field_regions: bool = False,
    include_table_cells: bool = True,
    eligibility: DoclangEligibility | None = None,
    harvest: HarvestResult | None = None,
    table_harvests: tuple[TableHarvest, ...] | None = None,
) -> tuple[Boundary, ...]:
    """Detect all structures using the exact policy and harvested membership."""

    root = tree.getroot()
    reject_nested_tables(root)
    policy = _resolve_policy(
        eligibility,
        include_picture_captions=include_picture_captions,
        include_background=include_background,
        include_furniture=include_furniture,
        include_code_blocks=include_code_blocks,
        include_formulas=include_formulas,
        include_field_regions=include_field_regions,
        include_table_cells=include_table_cells,
    )
    actual_harvest = harvest or harvest_doclang_text(tree, eligibility=policy)
    actual_tables = table_harvests or harvest_doclang_tables(tree, eligibility=policy)
    eligible = tuple(span.xpath for span in actual_harvest.spans)

    primary: list[Boundary] = []
    primary.extend(_detect_heading_boundaries(root, eligible, policy))
    primary.extend(_detect_page_boundaries(root, eligible, policy))
    primary.extend(_detect_group_boundaries(root, eligible, policy))
    if not primary:
        primary.extend(_detect_document_fallback(root, eligible))

    return (
        *primary,
        *_detect_table_boundaries(root, actual_tables),
        *_detect_field_region_boundaries(root, eligible),
    )


__all__ = ["detect_boundaries"]
