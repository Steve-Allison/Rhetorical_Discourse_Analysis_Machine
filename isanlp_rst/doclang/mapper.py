"""Map an RST tree's character-offset spans to DocLang xpaths.

Thin format binding over ``isanlp_rst._rst_common``: the address is each
span's ``xpath``; relations and edus are the DocLang schema types, with
``thread_ids`` aggregated per node from the constituent spans (Phase 1
confirmed at most one ``<thread>`` per host element). The traversal
itself lives in ``_rst_common._flatten``.
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
    return _generic_compute_overlap_refs(start, end, spans, ref_of=_xpath, note_threshold=note_threshold)


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
    source_text: str,
    note_threshold: float = NOTE_THRESHOLD,
) -> tuple[tuple[RstRelation, ...], tuple[RstEdu, ...]]:
    """Flatten a DiscourseUnit tree into ``(relations, edus)`` tuples.

    Ids are assigned in pre-order traversal and shared across relations
    and edus. ``boundary_memberships`` for each relation lists the boundary
    ids whose ``xpaths`` intersect the relation's node-level xpaths.
    """
    span_lookup: dict[str, HarvestSpan] = {s.xpath: s for s in harvest_spans}

    def make_relation(
        *,
        id: int,
        relation: str,
        nuclearity: str,
        nucleus_refs: tuple[str, ...],
        satellite_refs: tuple[str, ...],
        depth: int,
        left_id: int,
        right_id: int,
        boundary_memberships: tuple[str, ...],
        note: str | None,
        text: str,
        char_span: tuple[int, int],
        edu_span: tuple[int, int],
    ) -> RstRelation:
        return RstRelation(
            id=id,
            text=text,
            char_span=char_span,
            edu_span=edu_span,
            relation=relation,
            nuclearity=nuclearity,
            nucleus_xpaths=nucleus_refs,
            satellite_xpaths=satellite_refs,
            nucleus_thread_ids=_thread_ids_for_xpaths(nucleus_refs, span_lookup),
            satellite_thread_ids=_thread_ids_for_xpaths(satellite_refs, span_lookup),
            depth=depth,
            left_id=left_id,
            right_id=right_id,
            boundary_memberships=boundary_memberships,
            note=note,
        )

    def make_edu(
        *,
        id: int,
        refs: tuple[str, ...],
        depth: int,
        text: str,
        char_span: tuple[int, int],
        edu_span: tuple[int, int],
    ) -> RstEdu:
        return RstEdu(
            id=id,
            text=text,
            char_span=char_span,
            edu_span=edu_span,
            xpaths=refs,
            thread_ids=_thread_ids_for_xpaths(refs, span_lookup),
            depth=depth,
        )

    return _generic_flatten_tree(
        tree,
        source_text,
        SpanIndex(harvest_spans, ref_of=_xpath),
        [(b.id, frozenset(b.xpaths)) for b in boundaries],
        make_relation=make_relation,
        make_edu=make_edu,
        note_threshold=note_threshold,
    )
