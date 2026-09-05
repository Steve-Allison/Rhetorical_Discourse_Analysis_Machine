"""Materialize only provider-selected source evidence; never mine metadata strings."""

from typing import Literal

from pydantic import Field, model_validator
from typing import Self

from rdam._json_pointer import resolve_pointer
from rdam._strict import Sha256Identity, StrictModel
from rdam.contracts import ResultSourceAlignment
from rdam.ingest.contracts.evidence import SourceEvidenceSpan
from rdam.ingest.contracts.preparation import PreparedRange, SourceProjection


class SourceSelection(StrictModel):
    """A provider-owned payload field and its declared evidence relationship."""

    payload_path: str = Field(min_length=1)
    relationship: Literal["exact_quote", "supporting_passage", "literal_occurrence"]
    span: SourceEvidenceSpan | None = None

    @model_validator(mode="after")
    def supporting_passage_requires_span(self) -> Self:
        if self.relationship == "supporting_passage" and self.span is None:
            raise ValueError("supporting passage requires an explicit span")
        return self


def align_payload(
    payload: object,
    projection: SourceProjection | None,
    *,
    selections: tuple[SourceSelection, ...],
) -> tuple[ResultSourceAlignment, ...]:
    """Validate selected fields and preserve every eligible literal occurrence."""
    result: list[ResultSourceAlignment] = []
    for selection in selections:
        text = resolve_pointer(payload, selection.payload_path)
        if not isinstance(text, str) or not text.strip():
            raise ValueError("selected evidence field must be a nonblank string")
        span = selection.span
        if span is not None and selection.relationship != "supporting_passage" and span.text != text:
            raise ValueError("exact/literal selection must equal the source quote")
        if projection is None:
            continue
        if projection.projection_identity is None:
            raise ValueError("projection has no validated identity")
        document = projection.prepared_document
        spans: list[SourceEvidenceSpan] = []
        if span is not None:
            span.validate_source(document.text)
            spans.append(span)
        else:
            cursor = 0
            while (start := document.text.find(text, cursor)) >= 0:
                spans.append(SourceEvidenceSpan(start=start, end=start + len(text), text=text))
                cursor = start + 1
            if not spans and selection.relationship == "exact_quote":
                raise ValueError("selected exact quote does not occur in the source")
        for quote in spans:
            segments = tuple(segment for segment in document.segments
                             if segment.prepared_range.start < quote.end and quote.start < segment.prepared_range.end)
            items = tuple(dict.fromkeys(item for segment in segments for item in segment.contributing_item_ids))
            anchors = tuple(dict.fromkeys(anchor for segment in segments for anchor in segment.source_anchors))
            if not items or not anchors:
                raise ValueError("selected source passage has no contributing source anchors")
            result.append(ResultSourceAlignment(
                payload_path=selection.payload_path,
                prepared_range=PreparedRange(start=quote.start, end=quote.end),
                contributing_item_ids=items, source_anchors=anchors,
                relationship=selection.relationship,
                projection_identity=Sha256Identity(hex_digest=projection.projection_identity.hex_digest),
                quote=quote.text,
            ))
    return tuple(result)
