"""Source-only DocLang decoding with local cell ownership and exact text slots."""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Literal

from .document import DoclangDocument, DoclangTextFragment
from .errors import InvalidDoclangError
from .loader import XmlElement, local_name
from .text_walker import body_text, iter_body_slots, iter_sibling_slots

CELL_TOKENS = frozenset({"ched", "rhed", "corn", "srow", "fcel", "ecel", "lcel", "ucel", "xcel"})
CONTINUATIONS = frozenset({"lcel", "ucel", "xcel"})
TEXT_ELEMENTS = frozenset({"text", "heading", "footnote", "code", "formula", "caption", "description", "key", "value"})


@dataclass(frozen=True, slots=True)
class FragmentRange:
    fragment: DoclangTextFragment
    fragment_start: int
    fragment_end: int
    surface_start: int
    surface_end: int


@dataclass(frozen=True, slots=True)
class TextSurface:
    fragments: tuple[DoclangTextFragment, ...]
    text: str
    ranges: tuple[FragmentRange, ...]

    @classmethod
    def build(cls, fragments: Iterable[DoclangTextFragment]) -> TextSurface:
        values = tuple(fragments)
        raw = "".join(fragment.text for fragment in values)
        start = len(raw) - len(raw.lstrip())
        end = len(raw.rstrip())
        cursor = 0
        ranges: list[FragmentRange] = []
        for fragment in values:
            stop = cursor + len(fragment.text)
            left, right = max(start, cursor), min(end, stop)
            if left < right:
                ranges.append(FragmentRange(fragment, left - cursor, right - cursor, left - start, right - start))
            cursor = stop
        return cls(values, raw.strip(), tuple(ranges))


@dataclass(frozen=True, slots=True)
class DecodedDoclangCell:
    path: str
    token: str
    row: int
    column: int
    owner_path: str
    row_span: int
    column_span: int
    header: bool
    linked_paths: tuple[str, ...]
    surface: TextSurface


@dataclass(frozen=True, slots=True)
class DecodedDoclangItem:
    path: str
    parent_path: str | None
    child_paths: tuple[str, ...]
    tag: str
    attributes: tuple[tuple[str, str], ...]
    ancestors: frozenset[str]
    layer: str
    locations: tuple[tuple[str, str], ...]
    surface: TextSurface | None
    cell: DecodedDoclangCell | None
    cells: tuple[DecodedDoclangCell, ...]

    @property
    def text(self) -> str | None:
        return self.surface.text or None if self.surface is not None else None


def _surface(
    document: DoclangDocument, path: str, slots: Iterable[tuple[XmlElement, Literal["text", "tail"]]]
) -> TextSurface:
    fragments: list[DoclangTextFragment] = []
    for node, slot in slots:
        fragment = document.fragment(node, slot, path)
        if fragment is not None:
            fragments.append(fragment)
    return TextSurface.build(fragments)


def _intervals(
    parent: XmlElement, delimiters: frozenset[str]
) -> Iterable[tuple[XmlElement, tuple[XmlElement, ...], int, int]]:
    marker: XmlElement | None = None
    siblings: list[XmlElement] = []
    row = column = 0
    marker_position: tuple[int, int] = (0, 0)
    for child in parent:
        tag = local_name(child) if isinstance(child.tag, str) else ""
        if tag in delimiters:
            if marker is not None:
                yield marker, tuple(siblings), marker_position[0], marker_position[1]
            marker = child if tag != "nl" else None
            marker_position = (row, column)
            column += 1
            if tag == "nl":
                row += 1
                column = 0
            siblings = []
        elif marker is not None:
            siblings.append(child)
    if marker is not None:
        yield marker, tuple(siblings), marker_position[0], marker_position[1]


def _interval_slots(
    marker: XmlElement,
    siblings: tuple[XmlElement, ...],
) -> Iterable[tuple[XmlElement, Literal["text", "tail"]]]:
    yield marker, "tail"
    for sibling in siblings:
        yield from iter_sibling_slots(sibling)


def _list_surfaces(
    document: DoclangDocument,
    element: XmlElement,
    nested: Mapping[str, TextSurface],
) -> dict[str, TextSurface]:
    """Assign raw tails to the last emitted component, preserving reading order."""
    result: dict[str, TextSurface] = {}
    for marker, siblings, _row, _column in _intervals(element, frozenset({"ldiv"})):
        owner = document.paths[marker]
        fragments = list(_surface(document, owner, ((marker, "tail"),)).fragments)
        for sibling in siblings:
            tag = local_name(sibling)
            if tag in TEXT_ELEMENTS:
                result[owner] = TextSurface.build(fragments)
                owner = document.paths[sibling]
                fragments = list(
                    _surface(
                        document,
                        owner,
                        iter_body_slots(
                            sibling,
                            excluded_subtrees=frozenset({"table", "index", "tabular"}),
                        ),
                    ).fragments
                )
                fragments.extend(_surface(document, owner, ((sibling, "tail"),)).fragments)
            elif tag == "list":
                result[owner] = TextSurface.build(fragments)
                last: str | None = None
                for node in sibling.iter():
                    path = document.paths.get(node)
                    # A containing text surface already includes nested text.
                    if path is not None and path in nested and nested[path].text and (
                        last is None or not path.startswith(last + "/")
                    ):
                        last = path
                if last is not None:
                    owner = last
                    fragments = list(nested[last].fragments)
                fragments.extend(_surface(document, owner, ((sibling, "tail"),)).fragments)
            elif tag in {"table", "picture"}:
                fragments.extend(_surface(document, owner, ((sibling, "tail"),)).fragments)
            else:
                fragments.extend(_surface(document, owner, iter_sibling_slots(sibling)).fragments)
        result[owner] = TextSurface.build(fragments)
    return result


def _table(document: DoclangDocument, table: XmlElement) -> tuple[DecodedDoclangCell, ...]:
    positions: dict[str, tuple[int, int]] = {}
    owners: dict[tuple[int, int], str] = {}
    occupied: dict[str, list[tuple[int, int]]] = {}
    decoded: list[DecodedDoclangCell] = []
    for marker, siblings, row, column in _intervals(table, CELL_TOKENS | {"nl"}):
        path = document.paths[marker]
        positions[path] = row, column
        token = local_name(marker)
        left, above = owners.get((row, column - 1)), owners.get((row - 1, column))
        if token == "lcel":
            owner = left
        elif token == "ucel":
            owner = above
        elif token == "xcel":
            owner = left if left == above else None
        else:
            owner = path
        if owner is None:
            raise InvalidDoclangError(f"invalid DocLang merge ownership at {path} ({row}, {column})")
        owners[row, column] = owner
        occupied.setdefault(owner, []).append((row, column))
        surface = _surface(document, path, _interval_slots(marker, siblings))
        if token in CONTINUATIONS | {"ecel"} and surface.text:
            raise InvalidDoclangError(f"non-content DocLang cell contains text at {path}")
        linked = tuple(document.paths[child] for child in marker if isinstance(child.tag, str))
        linked += tuple(
            document.paths[sibling]
            for sibling in siblings
            if isinstance(sibling.tag, str)
            and (
                (local_name(sibling) in TEXT_ELEMENTS and body_text(sibling))
                or local_name(sibling) in {"list", "table", "picture"}
            )
        )
        decoded.append(
            DecodedDoclangCell(
                path, token, row, column, owner, 1, 1, token in {"ched", "rhed", "corn", "srow"}, linked, surface
            )
        )
    spans: dict[str, tuple[int, int]] = {}
    for owner, points in occupied.items():
        row, column = positions[owner]
        rows = max(point[0] for point in points) - row + 1
        columns = max(point[1] for point in points) - column + 1
        if len(points) != rows * columns or any(r < row or c < column for r, c in points):
            raise InvalidDoclangError(f"non-rectangular DocLang merge at {owner}")
        spans[owner] = rows, columns
    return tuple(
        DecodedDoclangCell(
            cell.path,
            cell.token,
            cell.row,
            cell.column,
            cell.owner_path,
            *spans[cell.owner_path],
            cell.header,
            cell.linked_paths,
            cell.surface,
        )
        for cell in decoded
    )


def decode_document(document: DoclangDocument) -> tuple[DecodedDoclangItem, ...]:
    """Decode all elements in source order; no policy or public models live here."""
    surfaces: dict[str, TextSurface] = {}
    tables: dict[str, tuple[DecodedDoclangCell, ...]] = {}
    cells: dict[str, DecodedDoclangCell] = {}
    elements = tuple(element for element in document.root.iter() if isinstance(element.tag, str))
    for element in reversed(elements):
        path = document.paths[element]
        tag = local_name(element)
        if tag in {"table", "index", "tabular"}:
            tables[path] = _table(document, element)
            cells.update((cell.path, cell) for cell in tables[path])
        elif tag == "list":
            surfaces.update(_list_surfaces(document, element, surfaces))
    result: list[DecodedDoclangItem] = []
    ancestry: dict[str, frozenset[str]] = {}
    for element in document.root.iter():
        if not isinstance(element.tag, str):
            continue
        path = document.paths[element]
        parent = element.getparent()
        parent_path = document.paths[parent] if parent is not None else None
        ancestors: frozenset[str] = ancestry[parent_path] if parent_path is not None else frozenset()
        tag = local_name(element)
        ancestry[path] = ancestors | {tag}
        children = tuple(child for child in element if isinstance(child.tag, str))
        layer = next(
            (child.get("value") for child in children if local_name(child) == "layer" and child.get("value")), "body"
        )
        locations = tuple(
            (child.get("value", ""), child.get("resolution") or "default")
            for child in children
            if local_name(child) == "location"
        )
        surface = surfaces.get(path)
        if tag in TEXT_ELEMENTS and surface is None:
            surface = _surface(
                document, path, iter_body_slots(element, excluded_subtrees=frozenset({"table", "index", "tabular"}))
            )
        # A text component may itself contain semantic components. Its surface
        # owns that text in source order; retain nested primary wrappers without
        # emitting a second copy during shared preparation.
        if tag in {"text", "heading", "footnote", "ldiv"} and ancestors & TEXT_ELEMENTS:
            surface = None
        cell = cells.get(path)
        if cell is not None and tag not in CONTINUATIONS | {"ecel"}:
            surface = cell.surface
        result.append(
            DecodedDoclangItem(
                path,
                parent_path,
                tuple(document.paths[child] for child in children),
                tag,
                tuple(sorted(element.attrib.items())),
                ancestors,
                layer or "body",
                locations,
                surface,
                cell,
                tables.get(path, ()),
            )
        )
    return tuple(result)


def item_index(items: tuple[DecodedDoclangItem, ...]) -> Mapping[str, DecodedDoclangItem]:
    return MappingProxyType({item.path: item for item in items})
