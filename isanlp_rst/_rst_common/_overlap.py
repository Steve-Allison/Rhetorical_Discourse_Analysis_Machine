"""Generic overlap computation for harvest spans of any format.

``SpanIndex`` is the workhorse: built once per flatten over the sorted,
mutually non-overlapping harvest spans, it answers each node's overlap
query in O(log n + k) via ``bisect`` instead of a full linear scan.
``compute_overlap_refs`` remains as the one-shot functional API (same
results, builds a throwaway index).
"""

from bisect import bisect_right
from collections.abc import Callable, Sequence
from operator import itemgetter
from typing import Protocol

NOTE_THRESHOLD: float = 0.90


class SpanLike(Protocol):
    """Any harvest span with half-open ``[start, end)`` character offsets."""

    @property
    def start(self) -> int: ...
    @property
    def end(self) -> int: ...


class SpanIndex[S: SpanLike]:
    """Bisect-backed overlap lookup over an ordered span sequence.

    Precondition: ``spans`` are sorted ascending by ``start`` and
    mutually non-overlapping — which is how every harvester constructs
    them (sequential emission with a cursor).
    """

    def __init__(self, spans: Sequence[S], *, ref_of: Callable[[S], str]) -> None:
        self._spans = list(spans)
        self._starts = [s.start for s in self._spans]
        self._ref_of = ref_of

    def overlap(
        self,
        start: int,
        end: int,
        *,
        note_threshold: float = NOTE_THRESHOLD,
    ) -> tuple[tuple[str, ...], str | None]:
        """Return ``(refs, note)`` for the half-open range ``[start, end)``.

        ``refs`` lists every span's address (via ``ref_of``) whose own
        range has any non-empty intersection with ``[start, end)``, in
        span order. ``note`` summarises lopsided overlaps where one span
        carries >= ``note_threshold`` of the total intersected length AND
        there is at least one minor contributor; ``None`` otherwise.

        Returns ``((), None)`` for zero-width or non-overlapping ranges.
        """
        if start >= end:
            return (), None

        # First candidate: the last span starting at or before `start`.
        i = bisect_right(self._starts, start) - 1
        if i < 0:
            i = 0

        overlaps: list[tuple[str, int]] = []
        n = len(self._spans)
        while i < n:
            span = self._spans[i]
            if span.start >= end:
                break
            ov_start = max(start, span.start)
            ov_end = min(end, span.end)
            if ov_end > ov_start:
                overlaps.append((self._ref_of(span), ov_end - ov_start))
            i += 1

        if not overlaps:
            return (), None

        refs = tuple(ref for ref, _ in overlaps)

        if len(overlaps) == 1:
            return refs, None

        total = sum(o for _, o in overlaps)
        dominant_ref, dominant_overlap = max(overlaps, key=itemgetter(1))
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


def compute_overlap_refs[S: SpanLike](
    start: int,
    end: int,
    spans: Sequence[S],
    *,
    ref_of: Callable[[S], str],
    note_threshold: float = NOTE_THRESHOLD,
) -> tuple[tuple[str, ...], str | None]:
    """One-shot functional form of ``SpanIndex.overlap``."""
    return SpanIndex(spans, ref_of=ref_of).overlap(
        start, end, note_threshold=note_threshold
    )


__all__ = ["NOTE_THRESHOLD", "SpanIndex", "SpanLike", "compute_overlap_refs"]
