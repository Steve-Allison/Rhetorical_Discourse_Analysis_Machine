"""Production-ingest enrichment of parser coordinates with native source anchors."""

from collections.abc import Callable, Iterable
from functools import cache

from rdam.ingest.contracts.analysis import (
    AnalysedDocument,
    AnalysedEdu,
    AnalysedToken,
    AnalysisAnchor,
    EndpointAnchor,
    ParserAnalysisResult,
)
from rdam.ingest.contracts.preparation import PreparationOutcome, PreparedDocument, PreparedSegment, SegmentKind
from rdam.ingest.contracts.source import SourceAnchor, TextSpanAnchor

type _RangeResolver = Callable[[int, int], tuple[SourceAnchor, ...]]


def enrich_parser_evidence(
    preparation: PreparationOutcome,
    parser_result: ParserAnalysisResult,
) -> tuple[AnalysedDocument, tuple[AnalysisAnchor, ...]]:
    """Map exact parser coordinates to provider-owned prepared and source evidence."""

    document = enrich_parser_document(preparation, parser_result)
    return document, enrich_parser_anchors(preparation, parser_result, document)


def enrich_parser_document(
    preparation: PreparationOutcome, parser_result: ParserAnalysisResult,
) -> AnalysedDocument:
    """Resolve token and EDU source mappings without expanding graph anchors."""

    prepared = preparation.semantic.prepared_document
    parser_document = parser_result.semantic.analysed_document

    @cache
    def resolve(start: int, end: int) -> tuple[SourceAnchor, ...]:
        return resolve_source_range(prepared, start, end)

    tokens = tuple(_enrich_token(token, prepared, resolve) for token in parser_document.tokens)
    token_by_id = {token.token_id: token for token in tokens}
    edus = tuple(_enrich_edu(edu, token_by_id, prepared, resolve) for edu in parser_document.edus)
    document = AnalysedDocument.model_validate(
        {
            **parser_document.model_dump(exclude={"semantic_digest", "tokens", "edus"}),
            "tokens": tokens,
            "edus": edus,
            "structural_boundary_ids": tuple(boundary.boundary_id for boundary in prepared.structural_boundaries),
            "prepared_segment_ids": tuple(segment.segment_id for segment in prepared.segments),
            "source_anchors": _unique_anchors(
                anchor for segment in prepared.segments for anchor in segment.source_anchors
            ),
        }
    )
    return document


def enrich_parser_anchors(
    preparation: PreparationOutcome, parser_result: ParserAnalysisResult, document: AnalysedDocument,
) -> tuple[AnalysisAnchor, ...]:
    """Expand graph evidence against its already resolved analysed document."""
    prepared = preparation.semantic.prepared_document
    parser_document = parser_result.semantic.analysed_document
    if document.text != parser_document.text or tuple(
        (token.token_id, token.character_range) for token in document.tokens
    ) != tuple((token.token_id, token.character_range) for token in parser_document.tokens):
        raise ValueError("source anchor document differs from parser coordinates")

    @cache
    def resolve(start: int, end: int) -> tuple[SourceAnchor, ...]:
        return resolve_source_range(prepared, start, end)

    token_by_id = {token.token_id: token for token in document.tokens}
    segments_by_token = {
        token.token_id: tuple(
            segment.segment_id for segment in _overlapping_segments(
                token.character_range.start, token.character_range.end, prepared.segments
            ) if segment.kind is SegmentKind.SOURCE
        ) for token in document.tokens
    }
    return tuple(
        _enrich_analysis_anchor(anchor, token_by_id, segments_by_token, resolve)
        for anchor in parser_result.semantic.anchors
    )


def _enrich_token(
    token: AnalysedToken,
    prepared: PreparedDocument,
    resolve: _RangeResolver,
) -> AnalysedToken:
    overlapping = _overlapping_segments(
        token.character_range.start,
        token.character_range.end,
        prepared.segments,
    )
    anchors = resolve(
        token.character_range.start,
        token.character_range.end,
    )
    if not anchors:
        raise ValueError(f"analysed token {token.token_id!r} has no native source mapping")
    return token.model_copy(
        update={
            "source_anchors": anchors,
            "transformation_ids": tuple(
                dict.fromkeys(
                    transformation_id for segment in overlapping for transformation_id in segment.transformation_ids
                )
            ),
        }
    )


def _enrich_edu(
    edu: AnalysedEdu,
    token_by_id: dict[str, AnalysedToken],
    prepared: PreparedDocument,
    resolve: _RangeResolver,
) -> AnalysedEdu:
    tokens = tuple(token_by_id[token_id] for token_id in edu.token_ids)
    start = min(token.character_range.start for token in tokens)
    end = max(token.character_range.end for token in tokens)
    overlapping = _overlapping_segments(start, end, prepared.segments)
    anchors = resolve(start, end)
    if not anchors:
        raise ValueError(f"analysed EDU {edu.edu_id!r} has no native source mapping")
    return edu.model_copy(
        update={
            "prepared_segment_ids": tuple(
                segment.segment_id for segment in overlapping if segment.kind is SegmentKind.SOURCE
            ),
            "source_anchors": anchors,
        }
    )


def _enrich_analysis_anchor(
    anchor: AnalysisAnchor,
    token_by_id: dict[str, AnalysedToken],
    segments_by_token: dict[str, tuple[str, ...]],
    resolve: _RangeResolver,
) -> AnalysisAnchor:
    tokens = tuple(token_by_id[token_id] for token_id in anchor.token_ids)
    if not tokens:
        raise ValueError(f"analysis anchor {anchor.target_id!r} has no native source mapping")
    source_anchors = _resolve_parser_ranges(anchor.source_anchors, resolve)
    prepared_segment_ids = tuple(
        dict.fromkeys(
            segment_id
            for token in tokens
            for segment_id in segments_by_token[token.token_id]
        )
    )
    return anchor.model_copy(
        update={
            "source_anchors": source_anchors,
            "prepared_segment_ids": prepared_segment_ids,
            "source_endpoint": _enrich_endpoint(anchor.source_endpoint, token_by_id, segments_by_token, resolve),
            "target_endpoint": _enrich_endpoint(anchor.target_endpoint, token_by_id, segments_by_token, resolve),
        }
    )


def _enrich_endpoint(
    endpoint: EndpointAnchor | None,
    token_by_id: dict[str, AnalysedToken],
    segments_by_token: dict[str, tuple[str, ...]],
    resolve: _RangeResolver,
) -> EndpointAnchor | None:
    if endpoint is None:
        return None
    tokens = tuple(token_by_id[token_id] for token_id in endpoint.token_ids)
    return endpoint.model_copy(
        update={
            "source_anchors": _resolve_parser_ranges(endpoint.source_anchors, resolve),
            "prepared_segment_ids": tuple(
                dict.fromkeys(
                    segment_id
                    for token in tokens
                    for segment_id in segments_by_token[token.token_id]
                )
            ),
        }
    )


def _resolve_parser_ranges(
    anchors: tuple[SourceAnchor, ...], resolve: _RangeResolver,
) -> tuple[SourceAnchor, ...]:
    resolved: list[SourceAnchor] = []
    for anchor in anchors:
        if not isinstance(anchor, TextSpanAnchor):
            raise ValueError("parser source mapping requires explicit text ranges")
        resolved.extend(resolve(anchor.start, anchor.end))
    if not resolved:
        raise ValueError("parser range has no native source mapping")
    return _unique_anchors(resolved)


def _overlapping_segments(
    start: int,
    end: int,
    segments: tuple[PreparedSegment, ...],
) -> tuple[PreparedSegment, ...]:
    return tuple(
        segment for segment in segments if segment.prepared_range.start < end and start < segment.prepared_range.end
    )


def resolve_source_range(prepared: PreparedDocument, start: int, end: int) -> tuple[SourceAnchor, ...]:
    """Resolve a nonempty prepared-text range to its original source coordinates.

    Exact untransformed text mappings are clipped independently at segment
    boundaries. Transformed and structured-source mappings retain their original
    anchors; their coordinates must never be inferred from prepared offsets.
    """
    if start < 0 or end <= start or end > len(prepared.text):
        raise ValueError("source resolution requires a nonempty range within prepared text")
    anchors = _anchors_for_range(start, end, _overlapping_segments(start, end, prepared.segments))
    if not anchors:
        raise ValueError("prepared range has no native source mapping")
    return anchors


def _anchors_for_range(
    start: int,
    end: int,
    segments: tuple[PreparedSegment, ...],
) -> tuple[SourceAnchor, ...]:
    anchors: list[SourceAnchor] = []
    for segment in segments:
        for anchor in segment.source_anchors:
            # Offset narrowing is valid only when the prepared text is the
            # source text verbatim: any recorded transformation may have moved
            # characters, so the whole-segment anchor is the truthful mapping.
            if (
                isinstance(anchor, TextSpanAnchor)
                and segment.kind is SegmentKind.SOURCE
                and not segment.transformation_ids
            ):
                local_start = max(start, segment.prepared_range.start) - segment.prepared_range.start
                local_end = min(end, segment.prepared_range.end) - segment.prepared_range.start
                if anchor.end - anchor.start == len(segment.text):
                    anchors.append(
                        TextSpanAnchor(
                            artifact_identity=anchor.artifact_identity,
                            start=anchor.start + local_start,
                            end=anchor.start + local_end,
                            quote=segment.text[local_start:local_end],
                        )
                    )
                    continue
            anchors.append(anchor)
    return _unique_anchors(anchors)


def _unique_anchors(values: Iterable[SourceAnchor]) -> tuple[SourceAnchor, ...]:
    result: list[SourceAnchor] = []
    seen: set[str] = set()
    for anchor in values:
        key = anchor.model_dump_json()
        if key not in seen:
            seen.add(key)
            result.append(anchor)
    return tuple(result)


__all__ = ["enrich_parser_anchors", "enrich_parser_document", "enrich_parser_evidence", "resolve_source_range"]
