"""Preparation, planning, mapping, transformation, and coverage contracts."""

from enum import StrEnum
from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from rdam.ingest.contracts.base import (
    PRODUCTION_CONTRACT,
    WRITE_CONTRACT_VERSION,
    ExactCoverage,
    CoverageUnit,
    SemanticVersion,
    Sha256Identity,
    StrictContractModel,
)
from rdam.ingest.contracts.source import (
    ContentClass,
    ContentInventoryItem,
    Disposition,
    DispositionDecision,
    SourceAnchor,
    SourceContractIdentity,
    SourceSummary,
)
from rdam.ingest.identity import semantic_sha256


class PreparedRange(StrictContractModel):
    start: int = Field(ge=0)
    end: int = Field(gt=0)

    @model_validator(mode="after")
    def ordered(self) -> Self:
        if self.end <= self.start:
            raise ValueError("range end must be greater than start")
        return self

    @property
    def length(self) -> int:
        return self.end - self.start


class SegmentKind(StrEnum):
    SOURCE = "source"
    SEPARATOR = "separator"
    DERIVED = "derived"


class StructureKind(StrEnum):
    DOCUMENT = "document"
    SECTION = "section"
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    LIST = "list"
    LIST_ITEM = "list_item"
    TURN = "turn"
    SLIDE = "slide"
    PAGE = "page"
    TABLE = "table"
    ROW = "row"
    CELL = "cell"
    GROUP = "group"
    FIELD = "field"
    RANGE = "range"


class BoundaryPreference(StrEnum):
    STRUCTURAL_CONTAINER = "structural_container"
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    SENTENCE = "sentence"
    EDU = "edu"


class AnalysisPlanStatus(StrEnum):
    NOT_PLANNED = "not_planned"
    SINGLE_UNIT = "single_unit"
    SUBDIVIDED = "subdivided"


class PreparationWarning(StrEnum):
    RETAINED_ONLY_SOURCE = "retained_only_source"
    EMPTY_SUBMITTED_CONTENT = "empty_submitted_content"
    MUTABLE_SOURCE_CONTRACT = "mutable_source_contract"


class CapacityUnit(StrEnum):
    EDU_COUNT = "edu_count"
    TOKEN_COUNT = "token_count"
    SEGMENT_COUNT = "segment_count"


class AnalysisCapacity(StrictContractModel):
    unit: CapacityUnit
    maximum: int = Field(gt=1)
    estimation_algorithm: str = Field(min_length=1)
    estimation_version: SemanticVersion
    source: str = Field(min_length=1)


class PreparationPolicy(StrictContractModel):
    policy_version: SemanticVersion
    primary_classes: tuple[ContentClass, ...]
    retained_classes: tuple[ContentClass, ...]
    duplicate_precedence: tuple[str, ...]
    normalization: Literal["preserve", "unicode_nfc", "line_endings_lf"]
    invalid_item_handling: Literal["fail_closed"] = "fail_closed"
    semantic_digest: Sha256Identity | None = None

    @model_validator(mode="after")
    def disjoint_classification(self) -> Self:
        if set(self.primary_classes) & set(self.retained_classes):
            raise ValueError("primary and retained content classes must be disjoint")
        expected = Sha256Identity(hex_digest=semantic_sha256(self.model_dump(exclude={"semantic_digest"})))
        if self.semantic_digest is not None and self.semantic_digest != expected:
            raise ValueError("preparation policy semantic digest mismatch")
        object.__setattr__(self, "semantic_digest", expected)
        return self


class PlanningPolicy(StrictContractModel):
    algorithm: str = Field(min_length=1)
    algorithm_version: SemanticVersion
    capacity_margin: int = Field(ge=0)
    boundary_preference: tuple[BoundaryPreference, ...]
    semantic_digest: Sha256Identity | None = None

    @model_validator(mode="after")
    def unique_boundaries(self) -> Self:
        if not self.boundary_preference:
            raise ValueError("planning policy requires at least one boundary preference")
        if len(self.boundary_preference) != len(set(self.boundary_preference)):
            raise ValueError("planning boundary preferences must be unique")
        expected = Sha256Identity(hex_digest=semantic_sha256(self.model_dump(exclude={"semantic_digest"})))
        if self.semantic_digest is not None and self.semantic_digest != expected:
            raise ValueError("planning policy semantic digest mismatch")
        object.__setattr__(self, "semantic_digest", expected)
        return self


class PreserveParameters(StrictContractModel):
    kind: Literal["preserve"] = "preserve"


class UnicodeNormalizationParameters(StrictContractModel):
    kind: Literal["unicode_normalization"] = "unicode_normalization"
    form: Literal["NFC"] = "NFC"


class LineEndingParameters(StrictContractModel):
    kind: Literal["line_ending_normalization"] = "line_ending_normalization"
    output: Literal["LF"] = "LF"


class SeparatorInsertionParameters(StrictContractModel):
    kind: Literal["separator_insertion"] = "separator_insertion"
    separator: str


class TableLinearisationParameters(StrictContractModel):
    kind: Literal["table_linearisation"] = "table_linearisation"
    layout: Literal["coordinates", "rows"] = "coordinates"
    repeat_headers: bool = True


type TransformationParameters = Annotated[
    PreserveParameters
    | UnicodeNormalizationParameters
    | LineEndingParameters
    | SeparatorInsertionParameters
    | TableLinearisationParameters,
    Field(discriminator="kind"),
]


class RepresentationProjection(StrictContractModel):
    representation_kind: str = Field(min_length=1)
    parameters: TransformationParameters


class ContentRequirement(StrictContractModel):
    """A provider-owned, content-addressed declaration of analysable source."""

    requirement_id: str = Field(min_length=1)
    admitted_classes: tuple[ContentClass, ...] = Field(min_length=1)
    representation_projections: tuple[RepresentationProjection, ...] = ()
    capacity: AnalysisCapacity
    boundary_preference: tuple[BoundaryPreference, ...] = Field(min_length=1)
    normalization: Literal["preserve", "unicode_nfc", "line_endings_lf"]
    requires_speaker_identity: bool
    semantic_digest: Sha256Identity | None = None

    @model_validator(mode="after")
    def coherent_requirement(self) -> Self:
        for values in (self.admitted_classes, self.boundary_preference):
            if len(values) != len(set(values)):
                raise ValueError("requirement classes and boundaries must be unique")
        kinds = tuple(item.representation_kind for item in self.representation_projections)
        if len(kinds) != len(set(kinds)):
            raise ValueError("representation projections must have unique kinds")
        if {ContentClass.TABLE, ContentClass.TABLE_CELL}.intersection(self.admitted_classes) and "table" not in kinds:
            raise ValueError("admitting tables requires a table representation projection")
        for projection in self.representation_projections:
            if projection.representation_kind != "table" or not isinstance(
                projection.parameters, TableLinearisationParameters
            ):
                raise ValueError("the supported representation projection is table linearisation")
        expected = Sha256Identity(hex_digest=semantic_sha256(self.model_dump(exclude={"semantic_digest"})))
        if self.semantic_digest is not None and self.semantic_digest != expected:
            raise ValueError("content requirement semantic digest mismatch")
        object.__setattr__(self, "semantic_digest", expected)
        return self


class UnmetRequirement(StrictContractModel):
    aspect: Literal["speaker_identity", "admitted_class", "capacity"]
    detail: str = Field(min_length=1)
    affected_item_ids: tuple[str, ...] = ()


class TransformationRecord(StrictContractModel):
    transformation_id: str = Field(min_length=1)
    transformation_kind: str = Field(min_length=1)
    algorithm_version: SemanticVersion
    input_item_ids: tuple[str, ...]
    output_segment_ids: tuple[str, ...]
    parameters: TransformationParameters
    semantic_digest: Sha256Identity | None = None

    @model_validator(mode="after")
    def complete_identity(self) -> Self:
        expected = Sha256Identity(
            hex_digest=semantic_sha256(
                {
                    "transformation_id": self.transformation_id,
                    "transformation_kind": self.transformation_kind,
                    "algorithm_version": self.algorithm_version,
                    "input_item_ids": self.input_item_ids,
                    "output_segment_ids": self.output_segment_ids,
                    "parameters": self.parameters,
                }
            )
        )
        if self.semantic_digest is not None and self.semantic_digest != expected:
            raise ValueError("transformation semantic digest mismatch")
        object.__setattr__(self, "semantic_digest", expected)
        return self


class PreparedSegment(StrictContractModel):
    segment_id: str = Field(min_length=1)
    order: int = Field(ge=0)
    kind: SegmentKind
    prepared_range: PreparedRange
    text: str
    contributing_item_ids: tuple[str, ...]
    source_anchors: tuple[SourceAnchor, ...]
    structural_boundary_id: str | None = None
    transformation_ids: tuple[str, ...] = ()

    @model_validator(mode="after")
    def range_matches_text(self) -> Self:
        if self.prepared_range.length != len(self.text):
            raise ValueError("prepared segment text length must match its range")
        if self.kind is SegmentKind.SOURCE and not self.contributing_item_ids:
            raise ValueError("source segment requires at least one contributing item")
        return self


class StructuralBoundary(StrictContractModel):
    boundary_id: str
    kind: StructureKind
    prepared_range: PreparedRange | None
    source_item_ids: tuple[str, ...]
    parent_boundary_id: str | None = None
    child_boundary_ids: tuple[str, ...] = ()


class PreparedDocument(StrictContractModel):
    source: SourceSummary
    text: str
    segments: tuple[PreparedSegment, ...]
    structural_boundaries: tuple[StructuralBoundary, ...]
    semantic_digest: Sha256Identity | None = None

    @model_validator(mode="after")
    def exact_ordered_text_and_identity(self) -> Self:
        cursor = 0
        parts: list[str] = []
        for order, segment in enumerate(self.segments):
            if segment.order != order or segment.prepared_range.start != cursor:
                raise ValueError("prepared segments must be contiguous and have canonical order")
            cursor = segment.prepared_range.end
            parts.append(segment.text)
        if cursor != len(self.text) or "".join(parts) != self.text:
            raise ValueError("prepared segments must reconstruct prepared text exactly")
        expected = Sha256Identity(
            hex_digest=semantic_sha256(
                {
                    "source": self.source,
                    "text": self.text,
                    "segments": self.segments,
                    "structural_boundaries": self.structural_boundaries,
                }
            )
        )
        if self.semantic_digest is not None and self.semantic_digest != expected:
            raise ValueError("prepared document semantic digest mismatch")
        object.__setattr__(self, "semantic_digest", expected)
        return self


class AnalysisUnit(StrictContractModel):
    unit_id: str
    order: int = Field(ge=0)
    first_segment_order: int = Field(ge=0)
    last_segment_order: int = Field(ge=0)
    estimated_demand: int = Field(ge=0)
    capacity: int = Field(gt=0)
    boundary_reason: BoundaryPreference
    predecessor_id: str | None = None
    successor_id: str | None = None

    @model_validator(mode="after")
    def coherent_range_and_capacity(self) -> Self:
        if self.last_segment_order < self.first_segment_order:
            raise ValueError("analysis-unit segment order is reversed")
        if self.estimated_demand > self.capacity:
            raise ValueError("analysis unit exceeds declared parser capacity")
        return self


class RecombinationLink(StrictContractModel):
    predecessor_unit_id: str
    successor_unit_id: str
    boundary_segment_order: int = Field(ge=0)


class RecombinationPlan(StrictContractModel):
    links: tuple[RecombinationLink, ...]


class AnalysisPlan(StrictContractModel):
    status: AnalysisPlanStatus
    capacity: AnalysisCapacity | None
    policy: PlanningPolicy
    units: tuple[AnalysisUnit, ...]
    recombination: RecombinationPlan
    semantic_digest: Sha256Identity | None = None

    @model_validator(mode="after")
    def coherent_state_and_identity(self) -> Self:
        if self.status is AnalysisPlanStatus.NOT_PLANNED:
            if self.capacity is not None or self.units:
                raise ValueError("not_planned requires absent capacity and no units")
        elif self.capacity is None:
            raise ValueError("planned analysis requires parser capacity")
        if self.status is AnalysisPlanStatus.SINGLE_UNIT and len(self.units) > 1:
            raise ValueError("single_unit plan cannot contain multiple units")
        if self.status is AnalysisPlanStatus.SUBDIVIDED and len(self.units) < 2:
            raise ValueError("subdivided plan requires at least two units")
        ids = [unit.unit_id for unit in self.units]
        if len(ids) != len(set(ids)):
            raise ValueError("analysis unit identities must be unique")
        expected = Sha256Identity(
            hex_digest=semantic_sha256(
                {
                    "status": self.status,
                    "capacity": self.capacity,
                    "policy": self.policy,
                    "units": self.units,
                    "recombination": self.recombination,
                }
            )
        )
        if self.semantic_digest is not None and self.semantic_digest != expected:
            raise ValueError("analysis plan semantic digest mismatch")
        object.__setattr__(self, "semantic_digest", expected)
        return self


class PreparationSemanticEvidence(StrictContractModel):
    source: SourceSummary
    source_contract: SourceContractIdentity
    preparation_policy: PreparationPolicy
    planning_policy: PlanningPolicy
    inventory: tuple[ContentInventoryItem, ...]
    transformations: tuple[TransformationRecord, ...]
    prepared_document: PreparedDocument
    analysis_plan: AnalysisPlan
    inventory_coverage: ExactCoverage
    primary_coverage: ExactCoverage
    retained_coverage: ExactCoverage
    mapping_coverage: ExactCoverage
    warnings: tuple[PreparationWarning, ...] = ()


class ContentInventory(StrictContractModel):
    """The complete shared inventory, independent of provider projection and execution."""

    source: SourceSummary
    source_contract: SourceContractIdentity
    items: tuple[ContentInventoryItem, ...]
    empty_submitted_content: bool
    semantic_digest: Sha256Identity | None = None

    @model_validator(mode="after")
    def complete_identity(self) -> Self:
        ids = tuple(item.item_id for item in self.items)
        if len(ids) != len(set(ids)):
            raise ValueError("inventory item identities must be unique")
        expected = Sha256Identity(hex_digest=semantic_sha256(self.model_dump(exclude={"semantic_digest"})))
        if self.semantic_digest is not None and self.semantic_digest != expected:
            raise ValueError("inventory semantic digest mismatch")
        object.__setattr__(self, "semantic_digest", expected)
        return self

    @classmethod
    def from_preparation(cls, preparation: PreparationOutcome) -> Self:
        semantic = preparation.semantic
        return cls(
            source=semantic.source,
            source_contract=semantic.source_contract,
            items=semantic.inventory,
            empty_submitted_content=PreparationWarning.EMPTY_SUBMITTED_CONTENT in semantic.warnings,
        )


class SourceProjection(StrictContractModel):
    inventory_identity: Sha256Identity
    requirement_identity: Sha256Identity
    projection_identity: Sha256Identity | None = None
    requirement_id: str = Field(min_length=1)
    prepared_document: PreparedDocument
    analysis_plan: AnalysisPlan
    transformations: tuple[TransformationRecord, ...]
    unmet_requirements: tuple[UnmetRequirement, ...] = ()

    @model_validator(mode="after")
    def complete_derivation(self) -> Self:
        records = {item.transformation_id: item for item in self.transformations}
        if len(records) != len(self.transformations):
            raise ValueError("projection transformation identities must be unique")
        segments = {item.segment_id: item for item in self.prepared_document.segments}
        if len(segments) != len(self.prepared_document.segments):
            raise ValueError("projection segment identities must be unique")
        for segment in segments.values():
            if segment.kind is SegmentKind.DERIVED and not segment.transformation_ids:
                raise ValueError("derived segment requires a transformation")
            for identity in segment.transformation_ids:
                if identity not in records or segment.segment_id not in records[identity].output_segment_ids:
                    raise ValueError("segment transformation must record its output")
        for record in records.values():
            if any(identity not in segments for identity in record.output_segment_ids):
                raise ValueError("transformation names an absent output segment")
        expected = Sha256Identity(
            hex_digest=semantic_sha256(
                {
                    "inventory": self.inventory_identity,
                    "requirement": self.requirement_identity,
                }
            )
        )
        if self.projection_identity is not None and self.projection_identity != expected:
            raise ValueError("projection identity mismatch")
        object.__setattr__(self, "projection_identity", expected)
        return self


class AdapterExecutionIdentity(StrictContractModel):
    distribution: str
    version: str


class SpeakerCoverage(StrictContractModel):
    turn_count: int = Field(ge=0)
    resolved_count: int = Field(ge=0)
    unresolved_count: int = Field(ge=0)
    distinct_participants: int = Field(ge=0)

    @model_validator(mode="after")
    def reconciled(self) -> Self:
        if self.resolved_count + self.unresolved_count != self.turn_count:
            raise ValueError("speaker counts must reconcile exactly")
        if self.distinct_participants > self.resolved_count or bool(self.distinct_participants) != bool(
            self.resolved_count
        ):
            raise ValueError("distinct participants must reconcile with resolved turns")
        return self

    @classmethod
    def from_items(cls, items: tuple[ContentInventoryItem, ...]) -> Self | None:
        turns = tuple(item for item in items if item.classification is ContentClass.TURN)
        if not turns:
            return None
        if any(item.speaker is None for item in turns):
            raise ValueError("every turn must explicitly resolve or not resolve its speaker")
        resolved = tuple(
            item.speaker for item in turns if item.speaker is not None and item.speaker.resolution == "resolved"
        )
        return cls(
            turn_count=len(turns),
            resolved_count=len(resolved),
            unresolved_count=len(turns) - len(resolved),
            distinct_participants=len({speaker.participant_id for speaker in resolved}),
        )


class PreparationReceipt(StrictContractModel):
    """One source inventory and its distinct provider projections, without run timing."""

    inventory: ContentInventory
    inventory_coverage: ExactCoverage
    primary_coverage: ExactCoverage
    retained_coverage: ExactCoverage
    mapping_coverage: ExactCoverage
    projections: tuple[SourceProjection, ...]
    transformations: tuple[TransformationRecord, ...]
    speaker_coverage: SpeakerCoverage | None = None

    @model_validator(mode="after")
    def complete_shared_inventory(self) -> Self:
        if self.speaker_coverage != SpeakerCoverage.from_items(self.inventory.items):
            raise ValueError("speaker coverage must account for every inventory turn")
        if self.inventory_coverage != ExactCoverage(
            covered_units=len(self.inventory.items),
            total_units=len(self.inventory.items),
            unit=CoverageUnit.ITEMS,
        ):
            raise ValueError("receipt must cover every inventory item")
        primary = sum(item.disposition.decision is DispositionDecision.PRIMARY for item in self.inventory.items)
        retained = sum(item.disposition.retained for item in self.inventory.items)
        for actual, count in ((self.primary_coverage, primary), (self.retained_coverage, retained)):
            if actual != ExactCoverage(covered_units=count, total_units=count, unit=CoverageUnit.ITEMS):
                raise ValueError("receipt disposition coverage differs from its shared inventory")
        identities = tuple(projection.projection_identity for projection in self.projections)
        if len(identities) != len(set(identities)):
            raise ValueError("receipt projections must be distinct")
        for projection in self.projections:
            if projection.inventory_identity != self.inventory.semantic_digest:
                raise ValueError("receipt projections must use its one inventory")
            if projection.prepared_document.source != self.inventory.source:
                raise ValueError("receipt projection source differs from its inventory")
            originals = {item.item_id: item for item in self.inventory.items}
            for segment in projection.prepared_document.segments:
                if any(identity not in originals for identity in segment.contributing_item_ids):
                    raise ValueError("projection contributor is absent from the shared inventory")
                if segment.kind is not SegmentKind.SEPARATOR and (
                    not segment.contributing_item_ids or not segment.source_anchors
                ):
                    raise ValueError("every projected content segment requires contributors and anchors")
                if any(
                    not any(anchor in originals[identity].anchors for identity in segment.contributing_item_ids)
                    for anchor in segment.source_anchors
                ):
                    raise ValueError("projection anchor is not supplied by its contributing items")
            for record in projection.transformations:
                if any(identity not in originals for identity in record.input_item_ids):
                    raise ValueError("transformation input is absent from the shared inventory")
            for unmet in projection.unmet_requirements:
                if any(identity not in originals for identity in unmet.affected_item_ids):
                    raise ValueError("unmet requirement names an absent inventory item")
        expected_transformations = {
            record.semantic_digest: record for projection in self.projections for record in projection.transformations
        }
        if self.transformations != tuple(expected_transformations.values()):
            raise ValueError("receipt transformations must be the ordered union of its projections")
        return self


class PreparationExecutionEvidence(StrictContractModel):
    execution_id: str
    adapters: tuple[AdapterExecutionIdentity, ...]
    duration_ms: float = Field(ge=0.0)
    diagnostic_mode: bool = False


class PreparationOutcome(StrictContractModel):
    contract: Literal["isanlp_rst.production"] = PRODUCTION_CONTRACT
    contract_version: Literal["2.0.0"] = WRITE_CONTRACT_VERSION
    kind: Literal["preparation_outcome"] = "preparation_outcome"
    semantic: PreparationSemanticEvidence
    execution: PreparationExecutionEvidence
    semantic_digest: Sha256Identity | None = None

    @model_validator(mode="after")
    def complete_identity(self) -> Self:
        expected = Sha256Identity(
            hex_digest=semantic_sha256(
                {
                    "contract": self.contract,
                    "contract_version": self.contract_version,
                    "kind": self.kind,
                    "semantic": self.semantic,
                }
            )
        )
        if self.semantic_digest is not None and self.semantic_digest != expected:
            raise ValueError("preparation outcome semantic digest mismatch")
        object.__setattr__(self, "semantic_digest", expected)
        return self

    @property
    def retained_items(self) -> tuple[ContentInventoryItem, ...]:
        return tuple(item for item in self.semantic.inventory if item.disposition.retained)

    @property
    def dispositions(self) -> tuple[Disposition, ...]:
        return tuple(item.disposition for item in self.semantic.inventory)


__all__ = [
    "AdapterExecutionIdentity",
    "AnalysisCapacity",
    "AnalysisPlan",
    "AnalysisPlanStatus",
    "AnalysisUnit",
    "BoundaryPreference",
    "CapacityUnit",
    "ContentInventory",
    "ContentRequirement",
    "LineEndingParameters",
    "PlanningPolicy",
    "PreparationExecutionEvidence",
    "PreparationOutcome",
    "PreparationReceipt",
    "PreparationPolicy",
    "PreparationSemanticEvidence",
    "PreparationWarning",
    "PreparedRange",
    "PreparedDocument",
    "PreparedSegment",
    "PreserveParameters",
    "RecombinationLink",
    "RecombinationPlan",
    "RepresentationProjection",
    "SegmentKind",
    "SeparatorInsertionParameters",
    "SourceProjection",
    "SpeakerCoverage",
    "StructuralBoundary",
    "StructureKind",
    "TransformationParameters",
    "TableLinearisationParameters",
    "TransformationRecord",
    "UnicodeNormalizationParameters",
    "UnmetRequirement",
]
