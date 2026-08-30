"""Deterministic structure-first analysis planning over prepared segments."""

from isanlp_rst.ingest.contracts.preparation import (
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
)


class AnalysisPlanningError(ValueError):
    """The declared capacity cannot yield a lossless analysis plan."""


def build_analysis_plan(
    prepared: PreparedRstDocument,
    *,
    capacity: ParserCapacity | None,
    policy: PlanningPolicy,
) -> AnalysisPlan:
    """Build a complete capacity-safe plan without splitting prepared segments."""

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


def _boundary_reason(
    prepared: PreparedRstDocument,
    first_segment_order: int,
    policy: PlanningPolicy,
) -> BoundaryPreference:
    segment = prepared.segments[first_segment_order]
    if segment.structural_boundary_id is not None:
        return policy.boundary_preference[0]
    return policy.boundary_preference[-1]


__all__ = ["AnalysisPlanningError", "build_analysis_plan"]
