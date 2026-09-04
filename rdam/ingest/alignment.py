"""Literal native-result quotes aligned to prepared source, without merging formalisms."""

from collections.abc import Mapping, Sequence
from typing import cast

from rdam.contracts import ResultSourceAlignment
from rdam.ingest.contracts.preparation import PreparedRange, SourceProjection


def align_payload(payload: object, projection: SourceProjection | None) -> tuple[ResultSourceAlignment, ...]:
    """Record every exact occurrence; ambiguous repeated quotations remain multiple matches."""
    if projection is None:
        return ()
    result: list[ResultSourceAlignment] = []
    document = projection.prepared_document
    for path, text in _strings(payload):
        cursor = 0
        while (start := document.text.find(text, cursor)) >= 0:
            end = start + len(text)
            segments = tuple(segment for segment in document.segments
                             if segment.prepared_range.start < end and start < segment.prepared_range.end)
            items = tuple(dict.fromkeys(item for segment in segments for item in segment.contributing_item_ids))
            anchors = tuple(dict.fromkeys(anchor for segment in segments for anchor in segment.source_anchors))
            if items and anchors:
                result.append(ResultSourceAlignment(
                    payload_path=path, prepared_range=PreparedRange(start=start, end=end),
                    contributing_item_ids=items, source_anchors=anchors,
                ))
            cursor = start + 1
    return tuple(result)


def _strings(value: object, path: str = "") -> tuple[tuple[str, str], ...]:
    if isinstance(value, str):
        return ((path, value),) if value.strip() and path else ()
    if isinstance(value, Mapping):
        return tuple(pair for key, child in cast(Mapping[object, object], value).items() if isinstance(key, str)
                     for pair in _strings(child, path + "/" + key.replace("~", "~0").replace("/", "~1")))
    if isinstance(value, Sequence) and not isinstance(value, bytes):
        return tuple(pair for index, child in enumerate(cast(Sequence[object], value)) for pair in _strings(child, path + "/" + str(index)))
    return ()
