"""Complete v2 source inventory and reversible canonical preparation."""

from importlib.metadata import version
import re
from time import perf_counter
import unicodedata
from uuid import uuid4

from isanlp_rst.ingest import _harvest
from isanlp_rst.ingest.contracts.base import CoverageUnit, ExactCoverage, SemanticVersion, Sha256Identity
from isanlp_rst.ingest.contracts.legacy import (
    AnchorKind as LegacyAnchorKind,
    ConversionActivity as LegacyConversionActivity,
    ContentClass as LegacyContentClass,
    ContentInventoryItem as LegacyInventoryItem,
    NativeAnchor as LegacyAnchor,
    SourceContractIdentity as LegacySourceContractIdentity,
    SourceArtifact as LegacySourceArtifact,
    SourceForm as LegacySourceForm,
)
from isanlp_rst.ingest.contracts.preparation import (
    AdapterExecutionIdentity,
    LineEndingParameters,
    ParserCapacity,
    PlanningPolicy,
    PreparationExecutionEvidence,
    PreparationOutcome,
    PreparationPolicy,
    PreparationWarning,
    PreparationSemanticEvidence,
    PreparedRange,
    PreparedRstDocument,
    PreparedSegment,
    SegmentKind,
    SeparatorInsertionParameters,
    StructuralBoundary,
    StructureKind,
    TransformationRecord,
    UnicodeNormalizationParameters,
)
from isanlp_rst.ingest.contracts.source import (
    AnnotationRepresentation,
    ArchiveMemberAnchor,
    AuthorshipRole,
    ContentClass,
    ContentInventoryItem,
    ContentRepresentation,
    CoordinateBoxAnchor,
    CrossReferenceRepresentation,
    Disposition,
    DispositionDecision,
    DispositionReason,
    ItemAnchor,
    ItemRelationship,
    ListItemRepresentation,
    ListRepresentation,
    MediaReferenceRepresentation,
    MetadataEntry,
    MetadataRepresentation,
    PageAnchor,
    PageBoxAnchor,
    SourceAnchor,
    SourceArtifact,
    SourceContractIdentity,
    SourceOrigin,
    SourcePathAnchor,
    StructureRepresentation,
    TableCell,
    TableCoordinateAnchor,
    TableRepresentation,
    TextRepresentation,
    TextSpanAnchor,
)
from isanlp_rst.ingest.policy import (
    DEFAULT_PLANNING_POLICY,
    DEFAULT_PREPARATION_POLICY,
    apply_policy,
)
from isanlp_rst.ingest.subdivision import build_analysis_plan
from isanlp_rst.ingest.validation import validate_inventory, validate_preparation_outcome


class PreparationValidationError(ValueError):
    """A fully assembled preparation outcome failed required validation."""

    def __init__(self, outcome: PreparationOutcome) -> None:
        self.outcome = outcome
        super().__init__("assembled preparation outcome failed required validation")


class SourceClassificationError(ValueError):
    """A materialized source failed its declared adapter/schema contract."""


def inventory_source(
    artifact: SourceArtifact,
) -> tuple[tuple[ContentInventoryItem, ...], SourceContractIdentity]:
    """Harvest every provider-observed item and translate it to the v2 contract."""

    legacy_inventory, legacy_contract = _harvest.inventory_source(_legacy_artifact(artifact))
    inventory = tuple(_translate_item(item, legacy_inventory, artifact) for item in legacy_inventory)
    return inventory, _translate_source_contract(legacy_contract)


def prepare_source(
    artifact: SourceArtifact,
    *,
    policy: PreparationPolicy = DEFAULT_PREPARATION_POLICY,
    planning_policy: PlanningPolicy = DEFAULT_PLANNING_POLICY,
    parser_capacity: ParserCapacity | None = None,
    execution_id: str | None = None,
) -> PreparationOutcome:
    """Return complete source, inventory, transformation, mapping, and plan evidence."""

    started = perf_counter()
    policy = PreparationPolicy.model_validate(policy.model_dump())
    planning_policy = PlanningPolicy.model_validate(planning_policy.model_dump())
    try:
        harvested, source_contract = inventory_source(artifact)
    except ModuleNotFoundError:
        raise
    except (OSError, TypeError, UnicodeError, ValueError) as exc:
        raise SourceClassificationError(
            "source failed its declared classification contract"
        ) from exc
    inventory = apply_policy(harvested, policy)
    validate_inventory(inventory)
    primary = tuple(
        item for item in inventory if item.disposition.decision is DispositionDecision.PRIMARY and item.text is not None
    )

    segments: list[PreparedSegment] = []
    transformations: list[TransformationRecord] = []
    transformations_by_item: dict[str, list[str]] = {item.item_id: [] for item in inventory}
    cursor = 0
    for item_index, item in enumerate(primary):
        if item_index:
            separator = " " if artifact.source_form.value == "edus" else "\n\n"
            segment_id = f"separator:{item_index:04d}"
            transformation_id = f"transformation:{segment_id}"
            segments.append(
                PreparedSegment(
                    segment_id=segment_id,
                    order=len(segments),
                    kind=SegmentKind.SEPARATOR,
                    prepared_range=PreparedRange(start=cursor, end=cursor + len(separator)),
                    text=separator,
                    contributing_item_ids=(),
                    source_anchors=(),
                    transformation_ids=(transformation_id,),
                )
            )
            transformations.append(
                TransformationRecord(
                    transformation_id=transformation_id,
                    transformation_kind="separator_insertion",
                    algorithm_version=SemanticVersion(root="2.0.0"),
                    input_item_ids=(primary[item_index - 1].item_id, item.item_id),
                    output_segment_ids=(segment_id,),
                    parameters=SeparatorInsertionParameters(separator=separator),
                )
            )
            transformations_by_item[primary[item_index - 1].item_id].append(transformation_id)
            transformations_by_item[item.item_id].append(transformation_id)
            cursor += len(separator)
        text, transformation_kind, parameters = _normalize_text(item.text or "", policy)
        segment_id = f"segment:{item.item_id}"
        transformation_ids: tuple[str, ...] = ()
        if transformation_kind is not None and parameters is not None:
            transformation_id = f"transformation:{segment_id}:{transformation_kind}"
            transformation_ids = (transformation_id,)
            transformations_by_item[item.item_id].append(transformation_id)
            transformations.append(
                TransformationRecord(
                    transformation_id=transformation_id,
                    transformation_kind=transformation_kind,
                    algorithm_version=SemanticVersion(root="2.0.0"),
                    input_item_ids=(item.item_id,),
                    output_segment_ids=(segment_id,),
                    parameters=parameters,
                )
            )
        segments.append(
            PreparedSegment(
                segment_id=segment_id,
                order=len(segments),
                kind=SegmentKind.SOURCE,
                prepared_range=PreparedRange(start=cursor, end=cursor + len(text)),
                text=text,
                contributing_item_ids=(item.item_id,),
                source_anchors=item.anchors,
                structural_boundary_id=f"boundary:{item.item_id}",
                transformation_ids=transformation_ids,
            )
        )
        cursor += len(text)

    inventory = tuple(
        item.model_copy(
            update={
                "disposition": item.disposition.model_copy(
                    update={"transformation_ids": tuple(transformations_by_item[item.item_id])}
                )
            }
        )
        for item in inventory
    )
    validate_inventory(inventory)

    text = "".join(segment.text for segment in segments)
    segment_by_item = {
        segment.contributing_item_ids[0]: segment for segment in segments if segment.contributing_item_ids
    }
    boundaries = tuple(
        StructuralBoundary(
            boundary_id=f"boundary:{item.item_id}",
            kind=_structure_kind(item.classification),
            prepared_range=(segment_by_item[item.item_id].prepared_range if item.item_id in segment_by_item else None),
            source_item_ids=(item.item_id,),
            parent_boundary_id=f"boundary:{item.parent_id}" if item.parent_id is not None else None,
            child_boundary_ids=tuple(f"boundary:{child_id}" for child_id in item.child_ids),
        )
        for item in inventory
    )
    prepared = PreparedRstDocument(
        source=artifact.summary(),
        text=text,
        segments=tuple(segments),
        structural_boundaries=boundaries,
    )
    plan = build_analysis_plan(
        prepared,
        capacity=parser_capacity,
        policy=planning_policy,
    )
    primary_count = sum(item.disposition.decision is DispositionDecision.PRIMARY for item in inventory)
    retained_count = sum(item.disposition.retained for item in inventory)
    mapped_characters = sum(segment.prepared_range.length for segment in segments)
    warnings: tuple[PreparationWarning, ...] = ()
    if not primary:
        warnings = (
            (PreparationWarning.EMPTY_SUBMITTED_CONTENT,)
            if _submitted_content_is_empty(artifact)
            else (PreparationWarning.RETAINED_ONLY_SOURCE,)
        )
    semantic = PreparationSemanticEvidence(
        source=artifact.summary(),
        source_contract=source_contract,
        preparation_policy=policy,
        planning_policy=planning_policy,
        inventory=inventory,
        transformations=tuple(transformations),
        prepared_document=prepared,
        analysis_plan=plan,
        inventory_coverage=ExactCoverage(
            covered_units=len(inventory),
            total_units=len(inventory),
            unit=CoverageUnit.ITEMS,
        ),
        primary_coverage=ExactCoverage(
            covered_units=primary_count,
            total_units=primary_count,
            unit=CoverageUnit.ITEMS,
        ),
        retained_coverage=ExactCoverage(
            covered_units=retained_count,
            total_units=retained_count,
            unit=CoverageUnit.ITEMS,
        ),
        mapping_coverage=ExactCoverage(
            covered_units=mapped_characters,
            total_units=len(text),
            unit=CoverageUnit.CHARACTERS,
        ),
        warnings=warnings,
    )
    outcome = PreparationOutcome(
        semantic=semantic,
        execution=PreparationExecutionEvidence(
            execution_id=execution_id or str(uuid4()),
            adapters=(
                AdapterExecutionIdentity(
                    distribution=source_contract.upstream_format or "isanlp_rst",
                    version=source_contract.upstream_version or version("isanlp_rst"),
                ),
            ),
            duration_ms=(perf_counter() - started) * 1_000.0,
        ),
    )
    try:
        validate_preparation_outcome(outcome)
    except Exception as exc:
        raise PreparationValidationError(outcome) from exc
    return outcome


def _normalize_text(
    text: str,
    policy: PreparationPolicy,
) -> tuple[
    str,
    str | None,
    UnicodeNormalizationParameters | LineEndingParameters | None,
]:
    if policy.normalization == "unicode_nfc":
        return (
            unicodedata.normalize("NFC", text),
            "unicode_normalization",
            UnicodeNormalizationParameters(),
        )
    if policy.normalization == "line_endings_lf":
        return (
            text.replace("\r\n", "\n").replace("\r", "\n"),
            "line_ending_normalization",
            LineEndingParameters(),
        )
    return text, None, None


def _submitted_content_is_empty(artifact: SourceArtifact) -> bool:
    if artifact.edus is not None:
        return not any(edu.strip() for edu in artifact.edus)
    if artifact.raw_bytes is None:
        return True
    try:
        return not artifact.raw_bytes.decode(artifact.encoding or "utf-8").strip()
    except UnicodeDecodeError:
        return False


def _translate_source_contract(legacy: LegacySourceContractIdentity) -> SourceContractIdentity:
    assumptions = tuple(f"{key}={value}" for key, value in legacy.validation_profile)
    return SourceContractIdentity(
        adapter=f"isanlp_rst.ingest.{legacy.family}",
        adapter_contract_version=SemanticVersion(root="2.0.0"),
        upstream_format=legacy.validator_distribution,
        upstream_version=legacy.validator_version,
        schema_identity=Sha256Identity(hex_digest=legacy.validator_digest),
        assumptions=assumptions,
    )


def _legacy_artifact(artifact: SourceArtifact) -> LegacySourceArtifact:
    provenance = tuple(
        LegacyConversionActivity(
            activity_id=item.activity_id,
            tool=item.tool,
            tool_version=item.tool_version,
            source_identity=item.source_identity,
            output_identity=item.output_identity,
        )
        for item in artifact.conversion_provenance
    )
    if artifact.edus is not None:
        return LegacySourceArtifact.from_edus(
            artifact.edus,
            source_name=artifact.source_name,
            original_source=artifact.original_source,
            conversion_provenance=provenance,
        )
    if artifact.raw_bytes is None:
        raise ValueError("validated source artifact has no materialized payload")
    return LegacySourceArtifact.from_bytes(
        artifact.raw_bytes,
        source_form=LegacySourceForm(artifact.source_form.value),
        source_name=artifact.source_name,
        media_type=artifact.media_type,
        original_source=artifact.original_source,
        conversion_provenance=provenance,
    )


def _translate_item(
    legacy: LegacyInventoryItem,
    inventory: tuple[LegacyInventoryItem, ...],
    artifact: SourceArtifact,
) -> ContentInventoryItem:
    classification = ContentClass(legacy.content_class.value)
    anchors = tuple(_translate_anchor(anchor, artifact) for anchor in legacy.native_anchors)
    if classification is ContentClass.ASSET:
        attributes = dict(legacy.attributes)
        member_digest = attributes.get("sha256")
        if member_digest is not None:
            anchors = (
                *anchors,
                ArchiveMemberAnchor(
                    artifact_identity=artifact.source_id,
                    member_path=legacy.item_id.removeprefix("archive:"),
                    member_identity=Sha256Identity(hex_digest=member_digest),
                ),
            )
    return ContentInventoryItem(
        item_id=legacy.item_id,
        classification=classification,
        origin=SourceOrigin(
            authorship=AuthorshipRole(legacy.authorship_role.value),
            source_layer=legacy.content_layer,
            producer=legacy.inventory_adapter,
        ),
        representation=_representation(legacy, inventory, classification),
        anchors=anchors,
        parent_id=legacy.parent_id,
        child_ids=legacy.child_ids,
        relationships=_relationships(legacy, inventory),
        provider_attributes=legacy.attributes,
        disposition=Disposition(
            decision=DispositionDecision.RETAINED,
            reason=DispositionReason.VALID_NON_PRIMARY,
        ),
    )


def _representation(
    item: LegacyInventoryItem,
    inventory: tuple[LegacyInventoryItem, ...],
    classification: ContentClass,
) -> ContentRepresentation:
    if classification is ContentClass.TABLE:
        return _table_representation(item, inventory)
    attributes = dict(item.attributes)
    target = attributes.get("uri") or attributes.get("href") or attributes.get("target")
    if target is not None and item.text is None:
        return CrossReferenceRepresentation(
            target_identity=target,
            relation="source_reference",
        )
    if classification is ContentClass.GROUP and any(
        child.parent_id == item.item_id and child.content_class is LegacyContentClass.LIST_ITEM for child in inventory
    ):
        return ListRepresentation(
            ordered=False,
            items=tuple(
                ListItemRepresentation(
                    item_id=child.item_id,
                    text=child.text,
                    child_item_ids=child.child_ids,
                )
                for child in inventory
                if child.parent_id == item.item_id
            ),
        )
    if classification in {ContentClass.METADATA, ContentClass.FIELD}:
        entries = tuple(MetadataEntry(key=key, value=value, value_type="string") for key, value in item.attributes)
        if item.text is not None:
            entries = (*entries, MetadataEntry(key="text", value=item.text, value_type="string"))
        return MetadataRepresentation(entries=entries)
    if classification in {
        ContentClass.CAPTION,
        ContentClass.NOTE,
        ContentClass.PICTURE_DESCRIPTION,
    }:
        return AnnotationRepresentation(label=classification.value, text=item.text)
    if classification in {ContentClass.PICTURE, ContentClass.ASSET}:
        child_reference = next(
            (
                dict(child.attributes).get("uri")
                for child in inventory
                if child.parent_id == item.item_id and dict(child.attributes).get("uri") is not None
            ),
            None,
        )
        markdown_reference = (
            match.group(1)
            if item.text is not None
            and (match := re.fullmatch(r"!\[[^\]]*\]\(([^)]+)\)", item.text.strip())) is not None
            else None
        )
        return MediaReferenceRepresentation(
            media_identity=item.item_id,
            source_reference=child_reference or markdown_reference,
            description=item.text,
        )
    if item.text is not None:
        return TextRepresentation(
            text=item.text,
            semantic_role=classification.value,
            attributes=tuple(
                (key, value)
                for key, value in item.attributes
                if not key.startswith("relationship:") and key not in {"href", "uri", "target"}
            ),
        )
    return StructureRepresentation(
        structure_type=classification.value,
        child_ids=item.child_ids,
    )


def _relationships(
    item: LegacyInventoryItem,
    inventory: tuple[LegacyInventoryItem, ...],
) -> tuple[ItemRelationship, ...]:
    known = {candidate.item_id for candidate in inventory}
    relationships: list[ItemRelationship] = []
    for key, target in item.attributes:
        if key in {"href", "uri", "target"}:
            relationships.append(
                ItemRelationship(
                    relation=key,
                    target_identity=target,
                    target_kind="inventory_item" if target in known else "external",
                )
            )
        elif key.startswith("relationship:"):
            relationships.append(
                ItemRelationship(
                    relation=key.removeprefix("relationship:").split(":", 1)[0],
                    target_identity=target,
                    target_kind="inventory_item" if target in known else "external",
                )
            )
    return tuple(relationships)


def _table_representation(
    table: LegacyInventoryItem,
    inventory: tuple[LegacyInventoryItem, ...],
) -> TableRepresentation:
    children = tuple(
        item
        for item in inventory
        if item.parent_id == table.item_id and item.content_class is LegacyContentClass.TABLE_CELL
    )
    coordinates: dict[tuple[int, int], tuple[LegacyInventoryItem, str]] = {}
    for index, child in enumerate(children):
        anchor = next(
            (candidate for candidate in child.native_anchors if candidate.kind is LegacyAnchorKind.TABLE_COORDINATE),
            None,
        )
        values = _selector_values(anchor.selector) if anchor is not None else {}
        row = _leading_integer(values.get("row", str(index)))
        column = _leading_integer(values.get("column", "0"))
        coordinates[(row, column)] = (child, values.get("token", "fcel"))

    continuations = {"lcel", "ucel", "xcel"}
    cells: list[TableCell] = []
    for (row, column), (child, token) in sorted(coordinates.items()):
        if token in continuations:
            continue
        attributes = dict(child.attributes)
        row_span = int(attributes.get("row_span", "1"))
        column_span = int(attributes.get("column_span", attributes.get("col_span", "1")))
        while coordinates.get((row, column + column_span), (child, ""))[1] in {"lcel", "xcel"}:
            column_span += 1
        while coordinates.get((row + row_span, column), (child, ""))[1] in {"ucel", "xcel"}:
            row_span += 1
        cells.append(
            TableCell(
                cell_id=child.item_id,
                row=row,
                column=column,
                row_span=row_span,
                column_span=column_span,
                text=child.text,
                header=(
                    token in {"ched", "rhed", "corn"}
                    or attributes.get("column_header") == "true"
                    or attributes.get("row_header") == "true"
                ),
                linked_item_ids=child.child_ids,
            )
        )
    return TableRepresentation(cells=tuple(cells))


def _translate_anchor(anchor: LegacyAnchor, artifact: SourceArtifact) -> SourceAnchor:
    if anchor.kind in {LegacyAnchorKind.CHARACTER, LegacyAnchorKind.BYTE} and anchor.range is not None:
        return TextSpanAnchor(
            artifact_identity=artifact.source_id,
            start=anchor.range.start,
            end=anchor.range.end,
            quote=anchor.quote,
        )
    if anchor.kind is LegacyAnchorKind.BOUNDING_BOX:
        values = _selector_values(anchor.selector)
        if {"l", "t", "r", "b"} <= values.keys():
            return PageBoxAnchor(
                artifact_identity=artifact.source_id,
                page=max(1, int(values.get("page", "1"))),
                left=float(values["l"]),
                top=float(values["t"]),
                right=float(values["r"]),
                bottom=float(values["b"]),
                coordinate_origin=values.get("origin", "unknown"),
            )
        if {"x0", "y0", "x1", "y1"} <= values.keys():
            return CoordinateBoxAnchor(
                artifact_identity=artifact.source_id,
                x0=float(values["x0"]),
                y0=float(values["y0"]),
                x1=float(values["x1"]),
                y1=float(values["y1"]),
                x0_resolution=values.get("x0_resolution", "default"),
                y0_resolution=values.get("y0_resolution", "default"),
                x1_resolution=values.get("x1_resolution", "default"),
                y1_resolution=values.get("y1_resolution", "default"),
                coordinate_system="doclang_location_axes",
            )
    if anchor.kind is LegacyAnchorKind.PAGE:
        values = _selector_values(anchor.selector)
        return PageAnchor(
            artifact_identity=artifact.source_id,
            page=max(1, int(values.get("page", "1"))),
            provenance_index=int(values["provenance"]) if "provenance" in values else None,
        )
    if anchor.kind is LegacyAnchorKind.TABLE_COORDINATE:
        values = _selector_values(anchor.selector)
        row = _leading_integer(values.get("row", "0"))
        column = _leading_integer(values.get("column", "0"))
        return TableCoordinateAnchor(
            artifact_identity=artifact.source_id,
            row=row,
            column=column,
        )
    if anchor.kind is LegacyAnchorKind.ITEM:
        return ItemAnchor(
            artifact_identity=artifact.source_id,
            item_identity=anchor.selector,
        )
    if anchor.kind is LegacyAnchorKind.JSON_POINTER:
        path_kind = "json_pointer"
    elif anchor.kind is LegacyAnchorKind.XML_PATH:
        path_kind = "xml_path"
    else:
        path_kind = "line"
    return SourcePathAnchor(
        artifact_identity=artifact.source_id,
        path_kind=path_kind,
        path=anchor.selector,
    )


def _selector_values(selector: str) -> dict[str, str]:
    return {key: value for part in selector.split(";") if "=" in part for key, value in (part.split("=", 1),)}


def _leading_integer(value: str) -> int:
    match = re.match(r"\d+", value)
    return int(match.group()) if match is not None else 0


def _structure_kind(content_class: ContentClass) -> StructureKind:
    return {
        ContentClass.TITLE: StructureKind.HEADING,
        ContentClass.HEADING: StructureKind.HEADING,
        ContentClass.PARAGRAPH: StructureKind.PARAGRAPH,
        ContentClass.LIST_ITEM: StructureKind.LIST_ITEM,
        ContentClass.TURN: StructureKind.TURN,
        ContentClass.TABLE: StructureKind.TABLE,
        ContentClass.TABLE_CELL: StructureKind.CELL,
        ContentClass.FIELD: StructureKind.FIELD,
        ContentClass.GROUP: StructureKind.GROUP,
    }.get(content_class, StructureKind.RANGE)


__all__ = [
    "PreparationValidationError",
    "SourceClassificationError",
    "inventory_source",
    "prepare_source",
]
