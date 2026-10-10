"""Source-only DocLang decoding with local cell ownership and exact text slots."""

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Literal

from .document import DoclangDocument, DoclangTextFragment
from .errors import InvalidDoclangError
from .loader import XmlElement, local_name
from .text_walker import body_text, iter_body_slots, iter_sibling_slots

CELL_TOKENS = frozenset({"ched", "rhed", "corn", "srow", "fcel", "ecel", "lcel", "ucel", "xcel"})
CONTINUATIONS = frozenset({"lcel", "ucel", "xcel"})
TEXT_ELEMENTS = frozenset(
    {"text", "heading", "footnote", "code", "formula", "caption", "description", "key", "value", "chapter"}
)
# A track timestamp is a run of these in order; only <seconds> is required (DocLang spec, Tracks).
TIME_ELEMENTS = ("hours", "minutes", "seconds", "msecs")
TRACK_MEDIA_ELEMENTS = frozenset({"cover", "frame", "audio"})


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
class DecodedTrackCue:
    """A <track> cue block: the <bdiv> that opens it and its inclusive interval in milliseconds."""

    path: str
    start_ms: int
    end_ms: int


@dataclass(frozen=True, slots=True)
class DecodedTrackTurn:
    """One speaker turn; ``speaker`` is the <voice> body text, absent when the turn is unattributed."""

    speaker: str | None


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
    cue: DecodedTrackCue | None = None
    turn: DecodedTrackTurn | None = None

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


def cue_interval(path: str, timing: Sequence[XmlElement]) -> tuple[int, int]:
    """Read a cue block's start and optional end time runs as inclusive milliseconds."""
    runs: list[dict[str, int]] = []
    previous = len(TIME_ELEMENTS)
    for element in timing:
        name = local_name(element)
        order = TIME_ELEMENTS.index(name)
        if order <= previous:
            runs.append({})
        previous = order
        try:
            runs[-1][name] = int(element.get("value", ""))
        except ValueError as exc:
            raise InvalidDoclangError(f"non-integer DocLang timestamp at {path}") from exc
    if not 1 <= len(runs) <= 2 or any("seconds" not in run for run in runs):
        raise InvalidDoclangError(f"DocLang cue block needs a start time and at most one end time at {path}")
    start, end = (
        ((run.get("hours", 0) * 60 + run.get("minutes", 0)) * 60 + run["seconds"]) * 1000 + run.get("msecs", 0)
        for run in (runs[0], runs[-1])
    )
    if end < start:
        raise InvalidDoclangError(f"DocLang cue block ends before it starts at {path}")
    return start, end


def _track(
    document: DoclangDocument, track: XmlElement
) -> tuple[dict[str, TextSurface], dict[str, DecodedTrackCue], dict[str, DecodedTrackTurn], dict[str, str]]:
    """Split each cue block's transcript into speaker turns owned by their <voice> (or the <bdiv>).

    The last mapping places a <bdiv>-owned turn in reading order: after the timestamps,
    chapter and media that precede its text.
    """
    surfaces: dict[str, TextSurface] = {}
    cues: dict[str, DecodedTrackCue] = {}
    turns: dict[str, DecodedTrackTurn] = {}
    positions: dict[str, str] = {}
    for marker, siblings, _row, _column in _intervals(track, frozenset({"bdiv"})):
        timing: list[XmlElement] = []
        for sibling in siblings:
            if not isinstance(sibling.tag, str):
                continue
            if local_name(sibling) not in TIME_ELEMENTS:
                break
            timing.append(sibling)
        cue_path = document.paths[marker]
        cue = DecodedTrackCue(cue_path, *cue_interval(cue_path, timing))
        # Text before any <voice> is an unattributed turn owned by the <bdiv>; an empty
        # <voice/> ends the current turn, and the text after it is unattributed.
        owners: list[tuple[str, str | None, list[DoclangTextFragment]]] = [
            (cue_path, None, list(_surface(document, cue_path, ((marker, "tail"),)).fragments))
        ]
        leading = True
        for sibling in siblings:
            tag = local_name(sibling) if isinstance(sibling.tag, str) else ""
            owner = owners[-1][0]
            leading = leading and (tag in TIME_ELEMENTS or tag == "chapter" or tag in TRACK_MEDIA_ELEMENTS or not tag)
            if leading and tag:
                positions[cue_path] = document.paths[sibling]
            if tag == "voice":
                path = document.paths[sibling]
                owners.append((path, body_text(sibling) or None, list(_surface(document, path, ((sibling, "tail"),)).fragments)))
            elif tag in TIME_ELEMENTS or tag == "chapter" or tag in TRACK_MEDIA_ELEMENTS:
                if tag not in TIME_ELEMENTS:
                    cues[document.paths[sibling]] = cue
                owners[-1][2].extend(_surface(document, owner, ((sibling, "tail"),)).fragments)
            else:
                owners[-1][2].extend(_surface(document, owner, iter_sibling_slots(sibling)).fragments)
        for owner, speaker, fragments in owners:
            surface = TextSurface.build(fragments)
            if surface.text:
                surfaces[owner] = surface
                cues[owner] = cue
                turns[owner] = DecodedTrackTurn(speaker)
    return surfaces, cues, turns, {owner: anchor for owner, anchor in positions.items() if owner in turns}


def _reading_order(
    items: list[DecodedDoclangItem], positions: Mapping[str, str]
) -> tuple[DecodedDoclangItem, ...]:
    """Move each positioned item to just after the subtree of the element its text follows."""
    held: dict[str, DecodedDoclangItem] = {}
    ordered: list[DecodedDoclangItem] = []
    open_anchor: tuple[str, DecodedDoclangItem] | None = None
    for item in items:
        if open_anchor is not None and not (item.path == open_anchor[0] or item.path.startswith(open_anchor[0] + "/")):
            ordered.append(open_anchor[1])
            open_anchor = None
        if item.path in positions:
            held[positions[item.path]] = item
            continue
        ordered.append(item)
        if item.path in held:
            open_anchor = item.path, held.pop(item.path)
    if open_anchor is not None:
        ordered.append(open_anchor[1])
    return tuple(ordered)


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
                or local_name(sibling) in {"list", "table", "picture", "track"}
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
    """Decode all elements in reading order; no policy or public models live here."""
    surfaces: dict[str, TextSurface] = {}
    tables: dict[str, tuple[DecodedDoclangCell, ...]] = {}
    cells: dict[str, DecodedDoclangCell] = {}
    cues: dict[str, DecodedTrackCue] = {}
    turns: dict[str, DecodedTrackTurn] = {}
    positions: dict[str, str] = {}
    elements = tuple(element for element in document.root.iter() if isinstance(element.tag, str))
    for element in reversed(elements):
        path = document.paths[element]
        tag = local_name(element)
        if tag in {"table", "index", "tabular"}:
            tables[path] = _table(document, element)
            cells.update((cell.path, cell) for cell in tables[path])
        elif tag == "list":
            surfaces.update(_list_surfaces(document, element, surfaces))
        elif tag == "track":
            track_surfaces, track_cues, track_turns, track_positions = _track(document, element)
            surfaces.update(track_surfaces)
            cues.update(track_cues)
            turns.update(track_turns)
            positions.update(track_positions)
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
                cues.get(path),
                turns.get(path),
            )
        )
    return _reading_order(result, positions)


def item_index(items: tuple[DecodedDoclangItem, ...]) -> Mapping[str, DecodedDoclangItem]:
    return MappingProxyType({item.path: item for item in items})
