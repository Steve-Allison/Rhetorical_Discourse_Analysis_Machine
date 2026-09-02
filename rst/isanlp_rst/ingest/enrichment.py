"""Production-ingest enrichment of parser coordinates with native source anchors."""

from collections.abc import Iterable

from isanlp_rst.ingest.contracts.analysis import (
    AnalysedDocument,
    AnalysedEdu,
    AnalysedToken,
    AnalysisAnchor,
    EndpointAnchor,
    ParserAnalysisResult,
)
from isanlp_rst.ingest.contracts.preparation import PreparationOutcome, PreparedSegment, SegmentKind
from isanlp_rst.ingest.contracts.source import SourceAnchor, TextSpanAnchor


def enrich_parser_evidence(
    preparation: PreparationOutcome,
    parser_result: ParserAnalysisResult,
) -> tuple[AnalysedDocument, tuple[AnalysisAnchor, ...]]:
    """Map exact parser coordinates to provider-owned prepared and source evidence."""

    prepared = preparation.semantic.prepared_document
    parser_document = parser_result.semantic.analysed_document
    tokens = tuple(
        _enrich_token(token, prepared.segments)
        for token in parser_document.tokens
    )
    token_by_id = {token.token_id: token for token in tokens}
    edus = tuple(
        _enrich_edu(edu, token_by_id, prepared.segments)
        for edu in parser_document.edus
    )
    document = AnalysedDocument.model_validate(
        {
            **parser_document.model_dump(exclude={"semantic_digest"}),
            "tokens": tokens,
            "edus": edus,
            "structural_boundary_ids": tuple(
                boundary.boundary_id for boundary in prepared.structural_boundaries
            ),
            "prepared_segment_ids": tuple(segment.segment_id for segment in prepared.segments),
            "source_anchors": _unique_anchors(
                anchor
                for segment in prepared.segments
                for anchor in segment.source_anchors
            ),
        }
    )
    anchors = tuple(
        _enrich_analysis_anchor(anchor, document, prepared.segments)
        for anchor in parser_result.semantic.anchors
    )
    return document, anchors


def _enrich_token(
    token: AnalysedToken,
    segments: tuple[PreparedSegment, ...],
) -> AnalysedToken:
    overlapping = _overlapping_segments(
        token.character_range.start,
        token.character_range.end,
        segments,
    )
    anchors = _anchors_for_range(
        token.character_range.start,
        token.character_range.end,
        overlapping,
    )
    if not anchors:
        raise ValueError(f"analysed token {token.token_id!r} has no native source mapping")
    return token.model_copy(
        update={
            "source_anchors": anchors,
            "transformation_ids": tuple(
                dict.fromkeys(
                    transformation_id
                    for segment in overlapping
                    for transformation_id in segment.transformation_ids
                )
            ),
        }
    )


def _enrich_edu(
    edu: AnalysedEdu,
    token_by_id: dict[str, AnalysedToken],
    segments: tuple[PreparedSegment, ...],
) -> AnalysedEdu:
    tokens = tuple(token_by_id[token_id] for token_id in edu.token_ids)
    start = min(token.character_range.start for token in tokens)
    end = max(token.character_range.end for token in tokens)
    overlapping = _overlapping_segments(start, end, segments)
    anchors = _unique_anchors(anchor for token in tokens for anchor in token.source_anchors)
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
    document: AnalysedDocument,
    segments: tuple[PreparedSegment, ...],
) -> AnalysisAnchor:
    token_by_id = {token.token_id: token for token in document.tokens}
    tokens = tuple(token_by_id[token_id] for token_id in anchor.token_ids)
    source_anchors = _unique_anchors(
        native for token in tokens for native in token.source_anchors
    )
    if not source_anchors:
        raise ValueError(
            f"analysis anchor {anchor.target_id!r} has no native source mapping"
        )
    prepared_segment_ids = tuple(
        dict.fromkeys(
            segment.segment_id
            for token in tokens
            for segment in _overlapping_segments(
                token.character_range.start,
                token.character_range.end,
                segments,
            )
            if segment.kind is SegmentKind.SOURCE
        )
    )
    return anchor.model_copy(
        update={
            "source_anchors": source_anchors,
            "prepared_segment_ids": prepared_segment_ids,
            "source_endpoint": _enrich_endpoint(anchor.source_endpoint, token_by_id, segments),
            "target_endpoint": _enrich_endpoint(anchor.target_endpoint, token_by_id, segments),
        }
    )


def _enrich_endpoint(
    endpoint: EndpointAnchor | None,
    token_by_id: dict[str, AnalysedToken],
    segments: tuple[PreparedSegment, ...],
) -> EndpointAnchor | None:
    if endpoint is None:
        return None
    tokens = tuple(token_by_id[token_id] for token_id in endpoint.token_ids)
    return endpoint.model_copy(
        update={
            "source_anchors": _unique_anchors(
                anchor for token in tokens for anchor in token.source_anchors
            ),
            "prepared_segment_ids": tuple(
                dict.fromkeys(
                    segment.segment_id
                    for token in tokens
                    for segment in _overlapping_segments(
                        token.character_range.start,
                        token.character_range.end,
                        segments,
                    )
                    if segment.kind is SegmentKind.SOURCE
                )
            ),
        }
    )


def _overlapping_segments(
    start: int,
    end: int,
    segments: tuple[PreparedSegment, ...],
) -> tuple[PreparedSegment, ...]:
    return tuple(
        segment
        for segment in segments
        if segment.prepared_range.start < end and start < segment.prepared_range.end
    )


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
                and segment.prepared_range.start <= start
                and end <= segment.prepared_range.end
            ):
                local_start = start - segment.prepared_range.start
                local_end = end - segment.prepared_range.start
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


__all__ = ["enrich_parser_evidence"]
