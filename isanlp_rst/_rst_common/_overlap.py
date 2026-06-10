"""Generic overlap computation for harvest spans of any format."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Protocol

NOTE_THRESHOLD: float = 0.90


class SpanLike(Protocol):
    """Any harvest span with half-open ``[start, end)`` character offsets."""

    @property
    def start(self) -> int: ...
    @property
    def end(self) -> int: ...


def compute_overlap_refs(
    start: int,
    end: int,
    spans: Sequence[SpanLike],
    *,
    ref_of: Callable[[SpanLike], str],
    note_threshold: float = NOTE_THRESHOLD,
) -> tuple[tuple[str, ...], str | None]:
    """Return ``(refs, note)`` for the half-open range ``[start, end)``.

    ``refs`` lists every span's address (via ``ref_of``) whose own range
    has any non-empty intersection with ``[start, end)``, in the order
    the spans appear in ``spans``. ``note`` summarises lopsided overlaps
    where one span carries >= ``note_threshold`` of the total intersected
    length AND there is at least one minor contributor; ``None`` otherwise.

    Returns ``((), None)`` for zero-width or non-overlapping ranges.
    """
    if start >= end:
        return (), None

    overlaps: list[tuple[str, int]] = []
    for span in spans:
        ov_start = max(start, span.start)
        ov_end = min(end, span.end)
        if ov_end > ov_start:
            overlaps.append((ref_of(span), ov_end - ov_start))

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
