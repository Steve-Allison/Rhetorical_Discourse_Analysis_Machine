"""Map an RST tree's character-offset spans to Docling self_refs.

Thin format binding over ``isanlp_rst._rst_common``: the address is each
span's ``self_ref``; relations and edus are the Docling schema types.
The traversal itself (iterative pre-order, shared id namespace, boundary
memberships) lives in ``_rst_common._flatten``.
"""

from operator import attrgetter
from typing import Any

from .._rst_common import (
    NOTE_THRESHOLD,
    SpanIndex,
)
from .._rst_common import (
    compute_overlap_refs as _generic_compute_overlap_refs,
)
from .._rst_common import (
    flatten_tree as _generic_flatten_tree,
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
    return _generic_compute_overlap_refs(start, end, spans, ref_of=_self_ref, note_threshold=note_threshold)


def _make_edu(*, id: int, refs: tuple[str, ...], depth: int) -> RstEdu:
    return RstEdu(id=id, self_refs=refs, depth=depth)


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
    return _generic_flatten_tree(
        tree,
        SpanIndex(harvest_spans, ref_of=_self_ref),
        [(b.id, frozenset(b.self_refs)) for b in boundaries],
        make_relation=RstRelation,
        make_edu=_make_edu,
        note_threshold=note_threshold,
    )
