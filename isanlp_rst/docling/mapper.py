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
"""

from __future__ import annotations

from typing import Any

from .schema import Boundary, HarvestSpan, RstEdu, RstRelation

NOTE_THRESHOLD: float = 0.90


def compute_overlap_refs(
    start: int,
    end: int,
    spans: tuple[HarvestSpan, ...],
    *,
    note_threshold: float = NOTE_THRESHOLD,
) -> tuple[tuple[str, ...], str | None]:
    """Return ``(refs, note)`` for the half-open range ``[start, end)``.

    ``refs`` is every HarvestSpan's ``self_ref`` whose own range has any
    non-empty intersection with ``[start, end)``, in the order the spans
    appear in ``spans``. ``note`` is ``None`` unless one span carries
    >= ``NOTE_THRESHOLD`` of the total intersected length and there is at
    least one minor contributor; in that case ``note`` summarises the
    spill in human-readable form.

    Returns ``((), None)`` for zero-width or non-overlapping ranges.
    """
    if start >= end:
        return (), None

    overlaps: list[tuple[str, int]] = []
    for span in spans:
        ov_start = max(start, span.start)
        ov_end = min(end, span.end)
        if ov_end > ov_start:
            overlaps.append((span.self_ref, ov_end - ov_start))

    if not overlaps:
        return (), None

    refs = tuple(ref for ref, _ in overlaps)

    if len(overlaps) == 1:
        return refs, None

    total = sum(o for _, o in overlaps)
    dominant_ref, dominant_overlap = max(overlaps, key=lambda x: x[1])
    if total > 0 and dominant_overlap / total >= note_threshold:
        minors = [(r, o) for r, o in overlaps if r != dominant_ref and o > 0]
        if minors:
            spill_pct = sum(o for _, o in minors) / total * 100
            minor_summary = ", ".join(f"{r} ({o} chars)" for r, o in minors)
            note = (
                f"{dominant_ref} covers {dominant_overlap}/{total} chars "
                f"({dominant_overlap / total * 100:.0f}%); "
                f"{spill_pct:.0f}% spills into: {minor_summary}"
            )
            return refs, note

    return refs, None


def _split_refs_by_nuclearity(
    left_refs: tuple[str, ...],
    right_refs: tuple[str, ...],
    nuclearity: str,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Return (nucleus_refs, satellite_refs) based on nuclearity."""
    if nuclearity == "NS":
        return left_refs, right_refs
    if nuclearity == "SN":
        return right_refs, left_refs
    # NN, "", or anything unrecognised → treat both children as nuclei
    return left_refs + right_refs, ()


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
    # Pre-compute boundary self_ref sets for O(1) intersection.
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
        nucleus_refs, satellite_refs = _split_refs_by_nuclearity(
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
