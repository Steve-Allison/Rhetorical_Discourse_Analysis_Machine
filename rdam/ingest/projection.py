"""Pure provider-specific views over one complete source inventory."""

from rdam.ingest.contracts.preparation import (
    ContentInventory,
    ContentRequirement,
    PlanningPolicy,
    PreparationPolicy,
    PreparationSemanticEvidence,
    PreparationWarning,
    PreparedDocument,
    SegmentKind,
    TableLinearisationParameters,
    TransformationRecord,
    UnmetRequirement,
    SourceProjection,
)
from rdam.ingest.contracts.base import CoverageUnit, ExactCoverage, SemanticVersion
from rdam.ingest.contracts.source import (
    ContentClass,
    ContentInventoryItem,
    Disposition,
    DispositionDecision,
    DispositionReason,
    TableRepresentation,
    TextRepresentation,
)
from rdam.ingest.policy import DEFAULT_PLANNING_POLICY, DEFAULT_PREPARATION_POLICY, admit_content
from rdam.ingest.prepare import assemble_preparation


def project(inventory: ContentInventory, requirement: ContentRequirement) -> SourceProjection:
    """Project without harvesting, mutating the inventory, or observing execution state."""

    semantic = project_preparation(inventory, requirement)
    if inventory.semantic_digest is None or requirement.semantic_digest is None:
        raise ValueError("validated inventory and requirement must carry identities")
    return SourceProjection(
        inventory_identity=inventory.semantic_digest,
        requirement_identity=requirement.semantic_digest,
        requirement_id=requirement.requirement_id,
        prepared_document=semantic.prepared_document,
        analysis_plan=semantic.analysis_plan,
        transformations=semantic.transformations,
        unmet_requirements=_unmet_speakers(inventory, requirement),
    )


def _unmet_speakers(inventory: ContentInventory, requirement: ContentRequirement) -> tuple[UnmetRequirement, ...]:
    if not requirement.requires_speaker_identity:
        return ()
    turns = tuple(item for item in inventory.items if item.classification is ContentClass.TURN)
    unresolved = tuple(
        item.item_id for item in turns if item.speaker is None or item.speaker.resolution == "unresolved"
    )
    if turns and not unresolved:
        return ()
    return (
        UnmetRequirement(
            aspect="speaker_identity",
            affected_item_ids=unresolved,
            detail="Source has unresolved speaker turns."
            if turns
            else "Source supplies no turn-level speaker identities.",
        ),
    )


def project_preparation(inventory: ContentInventory, requirement: ContentRequirement) -> PreparationSemanticEvidence:
    """Assemble the canonical preparation evidence for a declared view."""

    policy, planning = _policies(requirement)
    selected = admit_content(inventory.items, requirement.admitted_classes)
    rendered, table_inputs, contributors = _render_tables(inventory, requirement, selected)
    semantic = assemble_preparation(
        inventory.source,
        rendered,
        inventory.source_contract,
        policy=policy,
        planning_policy=planning,
        capacity=requirement.capacity,
        empty_submitted_content=inventory.empty_submitted_content,
    )
    if not table_inputs:
        return semantic
    transformations = list(semantic.transformations)
    segment_transformations: dict[str, str] = {}
    for table_id, (cell_ids, parameters) in table_inputs.items():
        outputs = tuple(
            segment.segment_id
            for segment in semantic.prepared_document.segments
            if set(segment.contributing_item_ids).intersection(cell_ids)
        )
        identity = f"transformation:table:{table_id}"
        transformations.append(
            TransformationRecord(
                transformation_id=identity,
                transformation_kind="table_linearisation",
                algorithm_version=SemanticVersion(root="1.0.0"),
                input_item_ids=(table_id, *cell_ids),
                output_segment_ids=outputs,
                parameters=parameters,
            )
        )
        segment_transformations.update(dict.fromkeys(outputs, identity))
    document = semantic.prepared_document
    originals = {item.item_id: item for item in inventory.items}
    segments = tuple(
        segment.model_copy(
            update={
                "kind": SegmentKind.DERIVED,
                "contributing_item_ids": tuple(
                    dict.fromkeys(
                        identity
                        for original in segment.contributing_item_ids
                        for identity in contributors.get(original, (original,))
                    )
                ),
                "source_anchors": tuple(
                    dict.fromkeys(
                        anchor
                        for original in segment.contributing_item_ids
                        for identity in contributors.get(original, (original,))
                        for anchor in originals[identity].anchors
                    )
                ),
                "transformation_ids": (*segment.transformation_ids, segment_transformations[segment.segment_id]),
            }
        )
        if segment.segment_id in segment_transformations
        else segment
        for segment in document.segments
    )
    prepared = PreparedDocument(
        source=document.source,
        text=document.text,
        segments=segments,
        structural_boundaries=document.structural_boundaries,
    )
    return semantic.model_copy(
        update={
            "prepared_document": prepared,
            "transformations": tuple(transformations),
        }
    )


def _render_tables(
    inventory: ContentInventory,
    requirement: ContentRequirement,
    selected: tuple[ContentInventoryItem, ...],
) -> tuple[
    tuple[ContentInventoryItem, ...],
    dict[str, tuple[tuple[str, ...], TableLinearisationParameters]],
    dict[str, tuple[str, ...]],
]:
    declaration = next(
        (entry for entry in requirement.representation_projections if entry.representation_kind == "table"), None
    )
    if declaration is None:
        return selected, {}, {}
    parameters = declaration.parameters
    if not isinstance(parameters, TableLinearisationParameters):
        raise ValueError("table projection requires table linearisation parameters")
    renderings: dict[str, str] = {}
    tables: dict[str, tuple[tuple[str, ...], TableLinearisationParameters]] = {}
    contributors: dict[str, tuple[str, ...]] = {}
    represented_items: set[str] = set()
    for table in inventory.items:
        if not isinstance(table.representation, TableRepresentation):
            continue
        if not {ContentClass.TABLE, ContentClass.TABLE_CELL}.intersection(requirement.admitted_classes):
            continue
        cells = table.representation.cells
        tables[table.item_id] = (
            tuple(dict.fromkeys(identity for cell in cells for identity in (cell.cell_id, *cell.linked_item_ids))),
            parameters,
        )
        for cell in cells:
            headers = tuple(
                header
                for header in cells
                if header.header
                and header.row < cell.row
                and header.column <= cell.column < header.column + header.column_span
                and header.text
            )
            label = f"row={cell.row}, column={cell.column}, row_span={cell.row_span}, column_span={cell.column_span}"
            if parameters.layout == "rows":
                label = f"Row {cell.row}, column {cell.column} ({cell.row_span}x{cell.column_span})"
            repeated = headers if parameters.repeat_headers else ()
            prefix = " / ".join(header.text for header in repeated if header.text) + ": " if repeated else ""
            contributors[cell.cell_id] = tuple(dict.fromkeys((
                cell.cell_id, *cell.linked_item_ids,
                *(identity for header in repeated for identity in (header.cell_id, *header.linked_item_ids)),
            )))
            represented_items.update(cell.linked_item_ids)
            renderings[cell.cell_id] = f"[{label}] {prefix}{cell.text or ''}"
    return (
        tuple(
            item.model_copy(
                update={
                    "representation": TextRepresentation(text=renderings[item.item_id], semantic_role="table_cell"),
                    "disposition": Disposition(
                        decision=DispositionDecision.PRIMARY,
                        reason=DispositionReason.AUTHORED_PRIMARY,
                        primary_segment_ids=(f"segment:{item.item_id}",),
                    ),
                }
            )
            if item.item_id in renderings
            else item.model_copy(update={"disposition": Disposition(
                decision=DispositionDecision.RETAINED, reason=DispositionReason.VALID_NON_PRIMARY,
            )})
            if item.item_id in represented_items
            else item
            for item in selected
        ),
        tables,
        contributors,
    )


def _policies(requirement: ContentRequirement) -> tuple[PreparationPolicy, PlanningPolicy]:
    policy = PreparationPolicy(
        policy_version=DEFAULT_PREPARATION_POLICY.policy_version,
        primary_classes=requirement.admitted_classes,
        retained_classes=tuple(value for value in ContentClass if value not in requirement.admitted_classes),
        duplicate_precedence=DEFAULT_PREPARATION_POLICY.duplicate_precedence,
        normalization=requirement.normalization,
    )
    planning = PlanningPolicy(
        algorithm=DEFAULT_PLANNING_POLICY.algorithm,
        algorithm_version=DEFAULT_PLANNING_POLICY.algorithm_version,
        capacity_margin=DEFAULT_PLANNING_POLICY.capacity_margin,
        boundary_preference=requirement.boundary_preference,
    )
    return policy, planning


def bind_preparation(
    inventory: ContentInventory,
    requirement: ContentRequirement,
    projection: SourceProjection,
) -> PreparationSemanticEvidence:
    """Bind an existing projection to native preparation evidence without projecting again."""
    if (
        projection.inventory_identity != inventory.semantic_digest
        or projection.requirement_identity != requirement.semantic_digest
    ):
        raise ValueError("projection does not belong to this inventory and requirement")
    policy, planning = _policies(requirement)
    selected = tuple(
        item.model_copy(
            update={
                "disposition": item.disposition.model_copy(
                    update={
                        "transformation_ids": tuple(
                            record.transformation_id
                            for record in projection.transformations
                            if item.item_id in record.input_item_ids
                        ),
                    }
                )
            }
        )
        for item in admit_content(inventory.items, requirement.admitted_classes)
    )
    primary = sum(item.disposition.decision is DispositionDecision.PRIMARY for item in selected)
    retained = sum(item.disposition.retained for item in selected)
    text = projection.prepared_document.text
    return PreparationSemanticEvidence(
        source=inventory.source,
        source_contract=inventory.source_contract,
        preparation_policy=policy,
        planning_policy=planning,
        inventory=selected,
        transformations=projection.transformations,
        prepared_document=projection.prepared_document,
        analysis_plan=projection.analysis_plan,
        inventory_coverage=ExactCoverage(
            covered_units=len(selected), total_units=len(selected), unit=CoverageUnit.ITEMS
        ),
        primary_coverage=ExactCoverage(covered_units=primary, total_units=primary, unit=CoverageUnit.ITEMS),
        retained_coverage=ExactCoverage(covered_units=retained, total_units=retained, unit=CoverageUnit.ITEMS),
        mapping_coverage=ExactCoverage(covered_units=len(text), total_units=len(text), unit=CoverageUnit.CHARACTERS),
        warnings=()
        if primary
        else (
            PreparationWarning.EMPTY_SUBMITTED_CONTENT
            if inventory.empty_submitted_content
            else PreparationWarning.RETAINED_ONLY_SOURCE,
        ),
    )


__all__ = ["project"]
