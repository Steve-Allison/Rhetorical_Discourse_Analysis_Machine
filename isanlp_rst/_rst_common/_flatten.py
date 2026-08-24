"""Authoritative, iterative projection of binary RST trees."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

from ._overlap import NOTE_THRESHOLD, SpanIndex
from ._split import split_refs_by_nuclearity


@dataclass(frozen=True, slots=True)
class ProjectedTreeNode:
    """One immutable, self-contained node in the authoritative projection."""

    node_id: int
    depth: int
    text: str
    char_span: tuple[int, int]
    edu_span: tuple[int, int]
    refs: tuple[str, ...]
    note: str | None
    relation: str
    nuclearity: str
    nucleus_refs: tuple[str, ...]
    satellite_refs: tuple[str, ...]
    left_id: int | None
    right_id: int | None
    boundary_memberships: tuple[str, ...]

    @property
    def is_leaf(self) -> bool:
        """Whether this projection represents an EDU leaf."""

        return self.left_id is None and self.right_id is None


@dataclass(frozen=True, slots=True)
class AuthoritativeProjection:
    """Complete format-neutral tree projection in pre-order."""

    source_text: str
    nodes: tuple[ProjectedTreeNode, ...]

    @property
    def relations(self) -> tuple[ProjectedTreeNode, ...]:
        """Internal-node projections in stable pre-order."""

        return tuple(node for node in self.nodes if not node.is_leaf)

    @property
    def edus(self) -> tuple[ProjectedTreeNode, ...]:
        """EDU projections in stable reading order."""

        return tuple(node for node in self.nodes if node.is_leaf)


def _validated_char_span(node: Any, source_length: int) -> tuple[int, int]:
    start = node.start
    end = node.end
    if not isinstance(start, int) or isinstance(start, bool) or not isinstance(end, int) or isinstance(end, bool):
        raise TypeError(f"RST node offsets must be integers, got start={start!r}, end={end!r}")
    if start < 0 or end < start or end > source_length:
        raise ValueError(f"RST node span [{start}, {end}) is outside source length {source_length}")
    return start, end


def project_tree(
    tree: Any,
    source_text: str,
    span_index: SpanIndex[Any],
    boundaries: Sequence[tuple[str, frozenset[str]]],
    *,
    note_threshold: float = NOTE_THRESHOLD,
) -> AuthoritativeProjection:
    """Compute ids, exact source slices, leaf order, and ancestor coverage once."""

    id_map: dict[int, int] = {}
    depth_map: dict[int, int] = {}
    preorder: list[Any] = []
    seen: set[int] = set()
    stack: list[tuple[Any, int]] = [(tree, 0)]
    while stack:
        node, depth = stack.pop()
        identity = id(node)
        if identity in seen:
            raise ValueError("RST input must be a tree: a node was reached more than once")
        seen.add(identity)
        _validated_char_span(node, len(source_text))
        id_map[identity] = len(preorder)
        depth_map[identity] = depth
        preorder.append(node)

        left = node.left
        right = node.right
        if (left is None) != (right is None):
            raise ValueError("RST internal nodes must have both left and right children")
        if left is not None and right is not None:
            node_start, node_end = _validated_char_span(node, len(source_text))
            for child in (left, right):
                child_start, child_end = _validated_char_span(child, len(source_text))
                if child_start < node_start or child_end > node_end:
                    raise ValueError(
                        f"Child span [{child_start}, {child_end}) lies outside parent span [{node_start}, {node_end})"
                    )
            stack.append((right, depth + 1))
            stack.append((left, depth + 1))

    leaf_coverage: dict[int, tuple[int, int]] = {}
    next_ordinal = 1
    for node in preorder:
        if node.left is None:
            leaf_coverage[id(node)] = (next_ordinal, next_ordinal)
            next_ordinal += 1
    for node in reversed(preorder):
        if node.left is None:
            continue
        left_coverage = leaf_coverage[id(node.left)]
        right_coverage = leaf_coverage[id(node.right)]
        leaf_coverage[id(node)] = (left_coverage[0], right_coverage[1])

    ref_to_boundary_positions: dict[str, list[int]] = {}
    boundary_ids: list[str] = []
    for position, (boundary_id, boundary_refs) in enumerate(boundaries):
        boundary_ids.append(boundary_id)
        for ref in boundary_refs:
            ref_to_boundary_positions.setdefault(ref, []).append(position)

    projected: list[ProjectedTreeNode] = []
    for node in preorder:
        identity = id(node)
        start, end = _validated_char_span(node, len(source_text))
        refs, note = span_index.overlap(start, end, note_threshold=note_threshold)
        left = node.left
        right = node.right
        positions = {position for ref in refs for position in ref_to_boundary_positions.get(ref, ())}
        memberships = tuple(boundary_ids[position] for position in sorted(positions))

        if left is None and right is None:
            relation = ""
            nuclearity = ""
            nucleus_refs: tuple[str, ...] = ()
            satellite_refs: tuple[str, ...] = ()
            left_id = None
            right_id = None
        else:
            if left is None or right is None:
                raise ValueError("RST internal nodes must have both left and right children")
            left_start, left_end = _validated_char_span(left, len(source_text))
            right_start, right_end = _validated_char_span(right, len(source_text))
            left_refs, _ = span_index.overlap(left_start, left_end)
            right_refs, _ = span_index.overlap(right_start, right_end)
            nuclearity = node.nuclearity or ""
            relation = node.relation or ""
            nucleus_refs, satellite_refs = split_refs_by_nuclearity(left_refs, right_refs, nuclearity)
            left_id = id_map[id(left)]
            right_id = id_map[id(right)]

        projected.append(
            ProjectedTreeNode(
                node_id=id_map[identity],
                depth=depth_map[identity],
                text=source_text[start:end],
                char_span=(start, end),
                edu_span=leaf_coverage[identity],
                refs=refs,
                note=note,
                relation=relation,
                nuclearity=nuclearity,
                nucleus_refs=nucleus_refs,
                satellite_refs=satellite_refs,
                left_id=left_id,
                right_id=right_id,
                boundary_memberships=memberships,
            )
        )

    return AuthoritativeProjection(source_text=source_text, nodes=tuple(projected))


def flatten_tree[R, E](
    tree: Any,
    source_text: str,
    span_index: SpanIndex[Any],
    boundaries: Sequence[tuple[str, frozenset[str]]],
    *,
    make_relation: Callable[..., R],
    make_edu: Callable[..., E],
    note_threshold: float = NOTE_THRESHOLD,
) -> tuple[tuple[R, ...], tuple[E, ...]]:
    """Adapt the authoritative projection to format-native wire classes."""

    projection = project_tree(
        tree,
        source_text,
        span_index,
        boundaries,
        note_threshold=note_threshold,
    )
    relations: list[R] = []
    edus: list[E] = []
    for node in projection.nodes:
        common = {
            "id": node.node_id,
            "depth": node.depth,
            "text": node.text,
            "char_span": node.char_span,
            "edu_span": node.edu_span,
        }
        if node.is_leaf:
            edus.append(make_edu(refs=node.refs, **common))
            continue
        if node.left_id is None or node.right_id is None:
            raise ValueError("Projected internal node is missing child identifiers")
        relations.append(
            make_relation(
                relation=node.relation,
                nuclearity=node.nuclearity,
                nucleus_refs=node.nucleus_refs,
                satellite_refs=node.satellite_refs,
                left_id=node.left_id,
                right_id=node.right_id,
                boundary_memberships=node.boundary_memberships,
                note=node.note,
                **common,
            )
        )

    return tuple(relations), tuple(edus)


__all__ = ["AuthoritativeProjection", "ProjectedTreeNode", "flatten_tree", "project_tree"]
