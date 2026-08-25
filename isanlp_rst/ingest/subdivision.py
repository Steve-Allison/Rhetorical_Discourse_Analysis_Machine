"""Deterministic structure-first subdivision for bounded local RST analysis."""

import re

from isanlp_rst.ingest.contracts import (
    AnalysisUnit,
    PreparedRange,
    PreparedRstDocument,
    StructureKind,
    SubdivisionPlan,
)
from isanlp_rst.model_loading import ParserCapacity

ALGORITHM_VERSION = "structure_first_v1"
_CHARACTERS_PER_CAPACITY_UNIT = 512


def build_subdivision_plan(prepared: PreparedRstDocument, capacity: ParserCapacity) -> SubdivisionPlan:
    """Partition the complete output exactly once, without splitting supplied EDUs."""

    if not prepared.text:
        return SubdivisionPlan(algorithm_version=ALGORITHM_VERSION, units=())
    ranges = (
        _edu_ranges(prepared, capacity.maximum)
        if prepared.document.edus is not None
        else _text_ranges(prepared, max(1_024, capacity.maximum * _CHARACTERS_PER_CAPACITY_UNIT))
    )
    units = tuple(
        AnalysisUnit(
            unit_id=f"unit:{index:04}",
            structure_kind=_operative_kind(prepared, output_range),
            output_range=output_range,
            source_item_ids=_source_items(prepared, output_range),
            capacity_unit=capacity.unit,
            capacity_maximum=capacity.maximum,
        )
        for index, output_range in enumerate(ranges)
    )
    _verify_complete(units, len(prepared.text))
    return SubdivisionPlan(algorithm_version=ALGORITHM_VERSION, units=units)


def _edu_ranges(prepared: PreparedRstDocument, maximum: int) -> tuple[PreparedRange, ...]:
    edus = prepared.document.edus or ()
    starts = list(range(0, len(edus), maximum))
    ranges: list[PreparedRange] = []
    for group_index, edu_index in enumerate(starts):
        start = 0 if group_index == 0 else edus[edu_index].start
        next_edu_index = edu_index + maximum
        end = edus[next_edu_index].start if next_edu_index < len(edus) else len(prepared.text)
        ranges.append(PreparedRange(start=start, end=end))
    return tuple(ranges)


def _text_ranges(prepared: PreparedRstDocument, maximum: int) -> tuple[PreparedRange, ...]:
    text = prepared.text
    preferred = {
        node.prepared_range.end
        for node in prepared.structure
        if node.prepared_range is not None
        and node.kind
        in {
            StructureKind.SECTION,
            StructureKind.HEADING,
            StructureKind.PARAGRAPH,
            StructureKind.LIST_ITEM,
            StructureKind.TURN,
        }
    }
    preferred.update(match.end() for match in re.finditer(r"\n\s*\n+|(?<=[.!?])\s+", text))
    candidates = sorted(point for point in preferred if 0 < point < len(text))
    structural_starts = sorted(
        {
            _separator_start(prepared, node.prepared_range.start)
            for node in prepared.structure
            if node.prepared_range is not None
            and node.kind in {StructureKind.HEADING, StructureKind.TURN}
            and node.prepared_range.start > 0
        }
    )
    coarse_boundaries = [0, *structural_starts, len(text)]
    ranges: list[PreparedRange] = []
    for coarse_start, coarse_end in zip(coarse_boundaries, coarse_boundaries[1:], strict=False):
        start = coarse_start
        while coarse_end - start > maximum:
            ceiling = start + maximum
            usable = [point for point in candidates if start < point <= ceiling]
            end = usable[-1] if usable else ceiling
            ranges.append(PreparedRange(start=start, end=end))
            start = end
        if coarse_end > start:
            ranges.append(PreparedRange(start=start, end=coarse_end))
    return tuple(ranges)


def _separator_start(prepared: PreparedRstDocument, position: int) -> int:
    preceding = next(
        (
            segment
            for segment in reversed(prepared.segments)
            if segment.prepared_range.end == position
        ),
        None,
    )
    return preceding.prepared_range.start if preceding is not None else position


def _source_items(prepared: PreparedRstDocument, output_range: PreparedRange) -> tuple[str, ...]:
    return tuple(
        segment.source_item_id
        for segment in prepared.segments
        if segment.source_item_id is not None and _overlaps(segment.prepared_range, output_range)
    )


def _operative_kind(prepared: PreparedRstDocument, output_range: PreparedRange) -> StructureKind:
    candidates = [
        node.kind
        for node in prepared.structure
        if node.prepared_range is not None
        and node.prepared_range.start <= output_range.start
        and output_range.end <= node.prepared_range.end
    ]
    return candidates[-1] if candidates else StructureKind.RANGE


def _overlaps(left: PreparedRange, right: PreparedRange) -> bool:
    return left.start < right.end and right.start < left.end


def _verify_complete(units: tuple[AnalysisUnit, ...], text_length: int) -> None:
    cursor = 0
    for unit in units:
        if unit.output_range.start != cursor:
            raise ValueError("subdivision output ranges must be contiguous and ordered")
        cursor = unit.output_range.end
    if cursor != text_length:
        raise ValueError("subdivision output ranges must cover prepared text exactly")


__all__ = ["ALGORITHM_VERSION", "build_subdivision_plan"]
