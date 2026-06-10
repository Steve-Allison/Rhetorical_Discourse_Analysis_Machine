"""Map an RST tree's character-offset spans to DocLang xpaths.

Two pure functions:

- ``compute_overlap_refs(start, end, spans)`` — given a half-open character
  range and the harvest's spans, return every span whose xpath overlaps
  the range, plus an optional ``note`` describing lopsided overlaps where
  one span carries >= ``NOTE_THRESHOLD`` of the total. Delegates to the
  generic ``isanlp_rst._rst_common`` function.

- ``flatten_tree(tree, harvest_spans, boundaries)`` — walk a binary
  ``DiscourseUnit`` tree in pre-order, assign sequential ids (shared
  namespace across relations and edus), compute per-relation xpaths +
  thread_ids + boundary_memberships, and emit ``(relations, edus)`` tuples.

Per the verified plan:
- ``thread_ids`` on a relation / edu is the deduplicated tuple of
  ``thread_id`` values carried by its constituent spans (Phase 1
  confirmed at most one ``<thread>`` per host element).
- The ``DiscourseUnit`` walk is identical in shape to the Docling
  variant; the schema construction differs.
"""

from __future__ import annotations

from operator import attrgetter
from typing import Any

from .._rst_common import (
    NOTE_THRESHOLD,
    split_refs_by_nuclearity,
)
from .._rst_common import (
    compute_overlap_refs as _generic_compute_overlap_refs,
)
from .schema import Boundary, HarvestSpan, RstEdu, RstRelation

__all__ = ["NOTE_THRESHOLD", "compute_overlap_refs", "flatten_tree"]

_xpath = attrgetter("xpath")


def compute_overlap_refs(
    start: int,
    end: int,
    spans: tuple[HarvestSpan, ...],
    *,
    note_threshold: float = NOTE_THRESHOLD,
) -> tuple[tuple[str, ...], str | None]:
    """Return ``(xpaths, note)`` for the half-open range ``[start, end)``.

    DocLang-specific wrapper over the generic overlap function — the
    address is each span's ``xpath``.
    """
    return _generic_compute_overlap_refs(
        start, end, spans, ref_of=_xpath, note_threshold=note_threshold
    )


def _thread_ids_for_xpaths(
    xpaths: tuple[str, ...],
    span_lookup: dict[str, HarvestSpan],
) -> tuple[int, ...]:
    """Return the deduplicated thread ids carried by the named spans.

    Order is the first-seen order across ``xpaths``. Spans without a
    thread are skipped silently.
    """
    seen: dict[int, None] = {}
    for xp in xpaths:
        span = span_lookup.get(xp)
        if span is None:
            continue
        if span.thread_id is None:
            continue
        seen.setdefault(span.thread_id, None)
    return tuple(seen.keys())


def flatten_tree(
    tree: Any,
    harvest_spans: tuple[HarvestSpan, ...],
    boundaries: tuple[Boundary, ...],
    *,
    note_threshold: float = NOTE_THRESHOLD,
) -> tuple[tuple[RstRelation, ...], tuple[RstEdu, ...]]:
    """Flatten a DiscourseUnit tree into ``(relations, edus)`` tuples.

    Ids are assigned in pre-order traversal and shared across relations
    and edus. ``boundary_memberships`` for each relation lists the boundary
    ids whose ``xpaths`` intersect the relation's node-level xpaths.
    """
    id_map: dict[int, int] = {}
    counter = 0

    def _assign(node: Any) -> None:
        nonlocal counter
        id_map[id(node)] = counter
        counter += 1
        left = getattr(node, "left", None)
        right = getattr(node, "right", None)
        if left is not None:
            _assign(left)
        if right is not None:
            _assign(right)

    _assign(tree)

    span_lookup: dict[str, HarvestSpan] = {s.xpath: s for s in harvest_spans}
    boundary_sets: list[tuple[str, frozenset[str]]] = [
        (b.id, frozenset(b.xpaths)) for b in boundaries
    ]

    relations: list[RstRelation] = []
    edus: list[RstEdu] = []

    def _build(node: Any, depth: int) -> None:
        my_id = id_map[id(node)]
        left = getattr(node, "left", None)
        right = getattr(node, "right", None)
        is_leaf = left is None and right is None
        node_xpaths, node_note = compute_overlap_refs(
            node.start, node.end, harvest_spans, note_threshold=note_threshold
        )

        if is_leaf:
            edus.append(
                RstEdu(
                    id=my_id,
                    xpaths=node_xpaths,
                    thread_ids=_thread_ids_for_xpaths(node_xpaths, span_lookup),
                    depth=depth,
                )
            )
            return

        # Binary-tree invariant: internal nodes always have both children
        # (see isanlp_rst/base_predictor.py).
        assert left is not None and right is not None
        left_xpaths, _ = compute_overlap_refs(left.start, left.end, harvest_spans)
        right_xpaths, _ = compute_overlap_refs(right.start, right.end, harvest_spans)
        nuclearity = getattr(node, "nuclearity", "") or ""
        relation = getattr(node, "relation", "") or ""
        nucleus_xpaths, satellite_xpaths = split_refs_by_nuclearity(
            left_xpaths, right_xpaths, nuclearity
        )

        node_xpath_set = set(node_xpaths)
        memberships = tuple(
            bid for bid, bxpaths in boundary_sets if node_xpath_set & bxpaths
        )

        relations.append(
            RstRelation(
                id=my_id,
                relation=relation,
                nuclearity=nuclearity,
                nucleus_xpaths=nucleus_xpaths,
                satellite_xpaths=satellite_xpaths,
                nucleus_thread_ids=_thread_ids_for_xpaths(nucleus_xpaths, span_lookup),
                satellite_thread_ids=_thread_ids_for_xpaths(satellite_xpaths, span_lookup),
                depth=depth,
                left_id=id_map[id(left)],
                right_id=id_map[id(right)],
                boundary_memberships=memberships,
                note=node_note,
            )
        )

        _build(left, depth + 1)
        _build(right, depth + 1)

    _build(tree, 0)
    return tuple(relations), tuple(edus)
