"""Model-independent validation of shared inventory and preparation evidence."""

from itertools import pairwise

from rdam.ingest.contracts.source import ContentInventoryItem, DispositionDecision, RedactedContentRepresentation
from rdam.ingest.contracts.preparation import AnalysisPlanStatus, PlanningPolicy, PreparationOutcome, PreparationPolicy, PreparedDocument, TransformationRecord
from rdam.ingest.identity import preparation_semantic_identity


def validate_inventory(inventory: tuple[ContentInventoryItem, ...]) -> None:
    """Reject incomplete links, duplicate cycles, or inaccessible retained content."""

    by_id = {item.item_id: item for item in inventory}
    if len(by_id) != len(inventory):
        raise ValueError("inventory item identities must be unique")
    for item in inventory:
        if item.parent_id is not None:
            parent = by_id.get(item.parent_id)
            if parent is None or item.item_id not in parent.child_ids:
                raise ValueError(f"inventory parent link is not reciprocal: {item.item_id}")
        for child_id in item.child_ids:
            child = by_id.get(child_id)
            if child is None or child.parent_id != item.item_id:
                raise ValueError(f"inventory child link is not reciprocal: {child_id}")
        for relationship in item.relationships:
            if relationship.target_kind == "inventory_item" and relationship.target_identity not in by_id:
                raise ValueError(f"inventory relationship target does not exist: {relationship.target_identity}")
        if item.disposition.retained and isinstance(
            item.representation,
            RedactedContentRepresentation,
        ):
            raise ValueError("normal retained inventory cannot replace accessible content with a digest")
    _validate_duplicate_chains(by_id)


def validate_preparation_outcome(outcome: PreparationOutcome) -> None:
    """Fail closed unless every exposed preparation reference and identity agrees."""

    semantic = outcome.semantic
    prepared = semantic.prepared_document
    inventory = semantic.inventory
    validate_inventory(inventory)
    if semantic.source != prepared.source:
        raise ValueError("preparation source summary and prepared source differ")

    _revalidate(semantic.preparation_policy, PreparationPolicy)
    _revalidate(semantic.planning_policy, PlanningPolicy)
    _revalidate(prepared, PreparedDocument)
    for transformation in semantic.transformations:
        _revalidate(transformation, TransformationRecord)

    primary_count = sum(item.disposition.decision is DispositionDecision.PRIMARY for item in inventory)
    retained_count = sum(item.disposition.retained for item in inventory)
    _require_exact_coverage(
        semantic.inventory_coverage.covered_units,
        semantic.inventory_coverage.total_units,
        len(inventory),
        "inventory",
    )
    _require_exact_coverage(
        semantic.primary_coverage.covered_units,
        semantic.primary_coverage.total_units,
        primary_count,
        "primary",
    )
    _require_exact_coverage(
        semantic.retained_coverage.covered_units,
        semantic.retained_coverage.total_units,
        retained_count,
        "retained",
    )
    mapped = sum(segment.prepared_range.length for segment in prepared.segments)
    _require_exact_coverage(
        semantic.mapping_coverage.covered_units,
        semantic.mapping_coverage.total_units,
        len(prepared.text),
        "mapping",
    )
    if mapped != len(prepared.text):
        raise ValueError("prepared mapping does not cover every output character")

    item_by_id = {item.item_id: item for item in inventory}
    segment_by_id = {segment.segment_id: segment for segment in prepared.segments}
    transformation_by_id = {
        transformation.transformation_id: transformation for transformation in semantic.transformations
    }
    boundary_by_id = {boundary.boundary_id: boundary for boundary in prepared.structural_boundaries}
    if len(segment_by_id) != len(prepared.segments):
        raise ValueError("prepared segment identities must be unique")
    if len(transformation_by_id) != len(semantic.transformations):
        raise ValueError("transformation identities must be unique")
    if len(boundary_by_id) != len(prepared.structural_boundaries):
        raise ValueError("structural boundary identities must be unique")

    for item in inventory:
        if any(anchor.artifact_identity != semantic.source.source_id for anchor in item.anchors):
            raise ValueError(f"inventory item {item.item_id!r} has a foreign source anchor")

    for segment in prepared.segments:
        if any(item_id not in item_by_id for item_id in segment.contributing_item_ids):
            raise ValueError(f"segment {segment.segment_id!r} references an absent inventory item")
        if any(anchor.artifact_identity != semantic.source.source_id for anchor in segment.source_anchors):
            raise ValueError(f"segment {segment.segment_id!r} has a foreign source anchor")
        if segment.structural_boundary_id not in boundary_by_id and segment.structural_boundary_id is not None:
            raise ValueError(f"segment {segment.segment_id!r} has an absent structural boundary")
        if any(value not in transformation_by_id for value in segment.transformation_ids):
            raise ValueError(f"segment {segment.segment_id!r} has an absent transformation")

    for transformation in semantic.transformations:
        if any(item_id not in item_by_id for item_id in transformation.input_item_ids):
            raise ValueError(f"transformation {transformation.transformation_id!r} has an absent input")
        if any(segment_id not in segment_by_id for segment_id in transformation.output_segment_ids):
            raise ValueError(f"transformation {transformation.transformation_id!r} has an absent output")
        for segment_id in transformation.output_segment_ids:
            if transformation.transformation_id not in segment_by_id[segment_id].transformation_ids:
                raise ValueError("transformation-to-segment link is not reciprocal")
        for item_id in transformation.input_item_ids:
            if transformation.transformation_id not in item_by_id[item_id].disposition.transformation_ids:
                raise ValueError("transformation-to-inventory link is not reciprocal")

    for boundary in prepared.structural_boundaries:
        if any(item_id not in item_by_id for item_id in boundary.source_item_ids):
            raise ValueError(f"boundary {boundary.boundary_id!r} has an absent inventory source")
        if boundary.parent_boundary_id is not None:
            parent = boundary_by_id.get(boundary.parent_boundary_id)
            if parent is None or boundary.boundary_id not in parent.child_boundary_ids:
                raise ValueError("structural boundary parent link is not reciprocal")
        for child_id in boundary.child_boundary_ids:
            child = boundary_by_id.get(child_id)
            if child is None or child.parent_boundary_id != boundary.boundary_id:
                raise ValueError("structural boundary child link is not reciprocal")

    _validate_analysis_plan(outcome)
    expected_identity = preparation_semantic_identity(outcome)
    if outcome.semantic_digest is None or outcome.semantic_digest.hex_digest != expected_identity:
        raise ValueError("preparation outcome semantic digest mismatch")


def _validate_analysis_plan(outcome: PreparationOutcome) -> None:
    plan = outcome.semantic.analysis_plan
    _revalidate(plan, type(plan))
    segments = outcome.semantic.prepared_document.segments
    if plan.status is AnalysisPlanStatus.NOT_PLANNED:
        if plan.units or plan.recombination.links:
            raise ValueError("not-planned analysis cannot contain units or recombination links")
        return
    covered_orders: list[int] = []
    for expected_order, unit in enumerate(plan.units):
        if unit.order != expected_order:
            raise ValueError("analysis units are not in canonical order")
        covered_orders.extend(range(unit.first_segment_order, unit.last_segment_order + 1))
        expected_predecessor = plan.units[expected_order - 1].unit_id if expected_order else None
        expected_successor = plan.units[expected_order + 1].unit_id if expected_order + 1 < len(plan.units) else None
        if unit.predecessor_id != expected_predecessor or unit.successor_id != expected_successor:
            raise ValueError("analysis-unit chain is incomplete")
    if covered_orders != list(range(len(segments))):
        raise ValueError("analysis units must cover every prepared segment exactly once")
    expected_links = tuple(
        (left.unit_id, right.unit_id, right.first_segment_order) for left, right in pairwise(plan.units)
    )
    actual_links = tuple(
        (link.predecessor_unit_id, link.successor_unit_id, link.boundary_segment_order)
        for link in plan.recombination.links
    )
    if actual_links != expected_links:
        raise ValueError("analysis recombination links do not match the unit chain")


def _require_exact_coverage(covered: int, total: int, expected: int, label: str) -> None:
    if covered != expected or total != expected:
        raise ValueError(f"{label} coverage is not exact")


def _revalidate(value: object, model_type: type[object]) -> None:
    validator = getattr(model_type, "model_validate", None)
    dumper = getattr(value, "model_dump", None)
    if not callable(validator) or not callable(dumper):
        raise TypeError("preparation validation received a non-contract value")
    validator(dumper())


def _validate_duplicate_chains(
    by_id: dict[str, ContentInventoryItem],
) -> None:
    resolved: set[str] = set()
    for item in by_id.values():
        if item.disposition.decision is not DispositionDecision.DUPLICATE or item.item_id in resolved:
            continue
        path: list[str] = []
        positions: dict[str, int] = {}
        current = item
        while current.item_id not in resolved:
            if current.item_id in positions:
                raise ValueError(f"duplicate disposition cycle includes {current.item_id}")
            positions[current.item_id] = len(path)
            path.append(current.item_id)
            duplicate_of = current.disposition.duplicate_of
            if duplicate_of is None:
                if current.disposition.decision is DispositionDecision.DUPLICATE:
                    raise ValueError("duplicate chain does not resolve to a canonical item")
                break
            target = by_id.get(duplicate_of)
            if target is None:
                raise ValueError(f"duplicate canonical target does not exist: {duplicate_of}")
            current = target
        resolved.update(path)


__all__ = ["validate_inventory", "validate_preparation_outcome"]
