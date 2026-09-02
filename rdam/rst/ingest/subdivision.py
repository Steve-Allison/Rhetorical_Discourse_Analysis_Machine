"""Deterministic capacity-estimated analysis planning over prepared segments.

Planning never splits a prepared segment; units are greedy contiguous groups
whose *estimated* demand fits the usable capacity. Estimation is exact when
segments align with the capacity unit (EDU-form sources under edu_count),
whitespace-token approximate under token_count, and a one-per-segment
heuristic otherwise — underestimation surfaces downstream as a typed parser
capacity failure at inference, never as silent truncation.
"""

from rdam.rst.ingest.contracts.preparation import (
    AnalysisPlan,
    AnalysisPlanStatus,
    AnalysisUnit,
    BoundaryPreference,
    ParserCapacity,
    PlanningPolicy,
    PreparedRstDocument,
    RecombinationLink,
    RecombinationPlan,
    SegmentKind,
    StructureKind,
)


class AnalysisPlanningError(ValueError):
    """The declared capacity cannot yield a lossless analysis plan."""


def build_analysis_plan(
    prepared: PreparedRstDocument,
    *,
    capacity: ParserCapacity | None,
    policy: PlanningPolicy,
) -> AnalysisPlan:
    """Build a complete capacity-estimated plan without splitting prepared segments."""

    if capacity is None:
        return AnalysisPlan(
            status=AnalysisPlanStatus.NOT_PLANNED,
            parser_capacity=None,
            policy=policy,
            units=(),
            recombination=RecombinationPlan(links=()),
        )

    available = capacity.maximum - policy.capacity_margin
    if available <= 0:
        raise AnalysisPlanningError(
            "planning capacity margin leaves no usable parser capacity"
        )
    if not prepared.segments:
        return AnalysisPlan(
            status=AnalysisPlanStatus.SINGLE_UNIT,
            parser_capacity=capacity,
            policy=policy,
            units=(),
            recombination=RecombinationPlan(links=()),
        )

    groups: list[tuple[int, int, int]] = []
    start = 0
    demand = 0
    for index, segment in enumerate(prepared.segments):
        segment_demand = _estimated_demand(segment.text, segment.kind, capacity)
        if segment_demand > available:
            raise AnalysisPlanningError(
                f"prepared segment {segment.segment_id!r} exceeds usable parser capacity"
            )
        if demand and demand + segment_demand > available:
            groups.append((start, index - 1, demand))
            start = index
            demand = 0
        demand += segment_demand
    groups.append((start, len(prepared.segments) - 1, demand))

    units = tuple(
        AnalysisUnit(
            unit_id=f"unit:{index:04d}",
            order=index,
            first_segment_order=first,
            last_segment_order=last,
            estimated_demand=unit_demand,
            capacity=available,
            boundary_reason=_boundary_reason(prepared, first, policy),
            predecessor_id=f"unit:{index - 1:04d}" if index else None,
            successor_id=f"unit:{index + 1:04d}" if index + 1 < len(groups) else None,
        )
        for index, (first, last, unit_demand) in enumerate(groups)
    )
    links = tuple(
        RecombinationLink(
            predecessor_unit_id=left.unit_id,
            successor_unit_id=right.unit_id,
            boundary_segment_order=right.first_segment_order,
        )
        for left, right in zip(units, units[1:], strict=False)
    )
    return AnalysisPlan(
        status=(AnalysisPlanStatus.SINGLE_UNIT if len(units) == 1 else AnalysisPlanStatus.SUBDIVIDED),
        parser_capacity=capacity,
        policy=policy,
        units=units,
        recombination=RecombinationPlan(links=links),
    )


def _estimated_demand(
    text: str,
    kind: SegmentKind,
    capacity: ParserCapacity,
) -> int:
    if kind is SegmentKind.SEPARATOR:
        return 0
    if capacity.unit.value == "token_count":
        return max(1, len(text.split()))
    return 1


_KIND_TO_PREFERENCE = {
    StructureKind.HEADING: BoundaryPreference.HEADING,
    StructureKind.PARAGRAPH: BoundaryPreference.PARAGRAPH,
}


def _boundary_reason(
    prepared: PreparedRstDocument,
    first_segment_order: int,
    policy: PlanningPolicy,
) -> BoundaryPreference:
    # The recorded reason states the kind of boundary the unit actually starts
    # on — never a preference the greedy packer did not consult.
    segment = prepared.segments[first_segment_order]
    if segment.structural_boundary_id is None:
        return policy.boundary_preference[-1]
    kind = next(
        boundary.kind
        for boundary in prepared.structural_boundaries
        if boundary.boundary_id == segment.structural_boundary_id
    )
    return _KIND_TO_PREFERENCE.get(kind, BoundaryPreference.STRUCTURAL_CONTAINER)


__all__ = ["AnalysisPlanningError", "build_analysis_plan"]
