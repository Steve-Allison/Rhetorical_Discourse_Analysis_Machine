"""Map an RST tree's character-offset spans to Docling self_refs.

Two pure functions:

- ``compute_overlap_refs(start, end, spans)`` — given a half-open character
  range and the harvest's spans, return every span whose self_ref overlaps
  the range (overlap rule), plus an optional ``note`` describing lopsided
  overlaps where one span carries >= ``NOTE_THRESHOLD`` of the total.

- ``flatten_tree(tree, harvest_spans, boundaries)`` — walk a binary
  ``DiscourseUnit`` tree in pre-order, assign sequential ids (shared
  namespace across relations and edus), compute per-relation refs and
  boundary_memberships, and emit ``(relations, edus)`` tuples.

Per plan §Decisions:
- relations[] is in pre-order DFS (root first).
- edus[] is in left-to-right reading order. For binary RST trees whose
  left subtree precedes the right subtree in text, pre-order over leaves
  is the same as reading order.
- ids are a shared namespace; left_id / right_id resolve uniformly.

Pure overlap maths and the nuclearity split live in ``isanlp_rst._rst_common``
so the ``doclang`` module shares them verbatim.
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

_self_ref = attrgetter("self_ref")


def compute_overlap_refs(
    start: int,
    end: int,
    spans: tuple[HarvestSpan, ...],
    *,
    note_threshold: float = NOTE_THRESHOLD,
) -> tuple[tuple[str, ...], str | None]:
    """Return ``(refs, note)`` for the half-open range ``[start, end)``.

    Docling-specific wrapper over the generic overlap function — the
    address is each span's ``self_ref``.
    """
    return _generic_compute_overlap_refs(
        start, end, spans, ref_of=_self_ref, note_threshold=note_threshold
    )


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
    ids whose ``self_refs`` intersect the relation's node-level refs.
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

    relations: list[RstRelation] = []
    edus: list[RstEdu] = []
    boundary_sets: list[tuple[str, frozenset[str]]] = [
        (b.id, frozenset(b.self_refs)) for b in boundaries
    ]

    def _build(node: Any, depth: int) -> None:
        my_id = id_map[id(node)]
        left = getattr(node, "left", None)
        right = getattr(node, "right", None)
        is_leaf = left is None and right is None
        node_refs, node_note = compute_overlap_refs(
            node.start, node.end, harvest_spans, note_threshold=note_threshold
        )

        if is_leaf:
            edus.append(RstEdu(id=my_id, self_refs=node_refs, depth=depth))
            return

        # Binary-tree invariant (see base_predictor.py:161): internal nodes
        # always have both children. `remap_tree_offsets` raises on unary nodes.
        assert left is not None and right is not None
        left_refs, _ = compute_overlap_refs(left.start, left.end, harvest_spans)
        right_refs, _ = compute_overlap_refs(right.start, right.end, harvest_spans)
        nuclearity = getattr(node, "nuclearity", "") or ""
        relation = getattr(node, "relation", "") or ""
        nucleus_refs, satellite_refs = split_refs_by_nuclearity(
            left_refs, right_refs, nuclearity
        )

        node_ref_set = set(node_refs)
        memberships = tuple(
            bid for bid, brefs in boundary_sets if node_ref_set & brefs
        )

        relations.append(
            RstRelation(
                id=my_id,
                relation=relation,
                nuclearity=nuclearity,
                nucleus_refs=nucleus_refs,
                satellite_refs=satellite_refs,
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
