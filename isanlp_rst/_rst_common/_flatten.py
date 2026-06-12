"""Generic, iterative DiscourseUnit-tree flattening.

One implementation shared by all format-native mappers. Each format
supplies two adapter callables that build its own frozen relation / EDU
dataclasses from the neutral keyword set computed here; everything else
(pre-order id assignment, overlap lookup, nuclearity split, boundary
membership) is format-agnostic.

Both traversals use explicit stacks, not recursion — RST joint-chains
produce heavily skewed trees, and a few-thousand-EDU document would
exceed Python's default recursion limit with the recursive walk this
replaces.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any, TypeVar

from ._overlap import NOTE_THRESHOLD, SpanIndex
from ._split import split_refs_by_nuclearity

R = TypeVar("R")
E = TypeVar("E")

# Adapter signatures (keyword-only at the call site):
#   make_relation(id=, relation=, nuclearity=, nucleus_refs=, satellite_refs=,
#                 depth=, left_id=, right_id=, boundary_memberships=, note=) -> R
#   make_edu(id=, refs=, depth=) -> E


def flatten_tree(
    tree: Any,
    span_index: SpanIndex,
    boundaries: Sequence[tuple[str, frozenset[str]]],
    *,
    make_relation: Callable[..., R],
    make_edu: Callable[..., E],
    note_threshold: float = NOTE_THRESHOLD,
) -> tuple[tuple[R, ...], tuple[E, ...]]:
    """Flatten a binary ``DiscourseUnit`` tree into ``(relations, edus)``.

    Ids are assigned in pre-order traversal and shared across relations
    and edus. ``boundary_memberships`` for each relation lists the
    boundary ids whose ref-sets intersect the relation's node-level refs,
    in ``boundaries`` order.
    """
    # Pass 1 — pre-order id assignment (iterative).
    id_map: dict[int, int] = {}
    counter = 0
    stack: list[Any] = [tree]
    while stack:
        node = stack.pop()
        id_map[id(node)] = counter
        counter += 1
        # Push right first so left is processed first (pre-order).
        if node.right is not None:
            stack.append(node.right)
        if node.left is not None:
            stack.append(node.left)

    # Inverted index: ref -> boundary positions, for ordered memberships.
    ref_to_bpos: dict[str, list[int]] = {}
    boundary_ids: list[str] = []
    for pos, (bid, brefs) in enumerate(boundaries):
        boundary_ids.append(bid)
        for ref in brefs:
            ref_to_bpos.setdefault(ref, []).append(pos)

    relations: list[R] = []
    edus: list[E] = []

    # Pass 2 — pre-order build (iterative).
    build_stack: list[tuple[Any, int]] = [(tree, 0)]
    while build_stack:
        node, depth = build_stack.pop()
        my_id = id_map[id(node)]
        left = node.left
        right = node.right
        node_refs, node_note = span_index.overlap(
            node.start, node.end, note_threshold=note_threshold
        )

        if left is None and right is None:
            edus.append(make_edu(id=my_id, refs=node_refs, depth=depth))
            continue

        # Binary-tree invariant (see isanlp_rst/base_predictor.py):
        # internal nodes always have both children.
        assert left is not None and right is not None
        left_refs, _ = span_index.overlap(left.start, left.end)
        right_refs, _ = span_index.overlap(right.start, right.end)
        nuclearity = node.nuclearity or ""
        relation = node.relation or ""
        nucleus_refs, satellite_refs = split_refs_by_nuclearity(
            left_refs, right_refs, nuclearity
        )

        positions = {pos for ref in node_refs for pos in ref_to_bpos.get(ref, ())}
        memberships = tuple(boundary_ids[pos] for pos in sorted(positions))

        relations.append(
            make_relation(
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

        # Push right first so the left subtree is fully emitted first.
        build_stack.append((right, depth + 1))
        build_stack.append((left, depth + 1))

    return tuple(relations), tuple(edus)


__all__ = ["flatten_tree"]
