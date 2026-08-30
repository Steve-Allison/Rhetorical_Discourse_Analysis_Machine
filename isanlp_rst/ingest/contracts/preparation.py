"""Preparation, planning, mapping, transformation, and coverage contracts."""

from enum import StrEnum
from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from isanlp_rst.ingest.contracts.base import (
    PRODUCTION_CONTRACT,
    WRITE_CONTRACT_VERSION,
    ExactCoverage,
    SemanticVersion,
    Sha256Identity,
    StrictContractModel,
)
from isanlp_rst.ingest.contracts.source import (
    ContentClass,
    ContentInventoryItem,
    Disposition,
    SourceAnchor,
    SourceContractIdentity,
    SourceSummary,
)
from isanlp_rst.ingest.identity import semantic_sha256


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


class ParserCapacity(StrictContractModel):
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
        expected = Sha256Identity(
            hex_digest=semantic_sha256(self.model_dump(exclude={"semantic_digest"}))
        )
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
        expected = Sha256Identity(
            hex_digest=semantic_sha256(self.model_dump(exclude={"semantic_digest"}))
        )
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


type TransformationParameters = Annotated[
    PreserveParameters
    | UnicodeNormalizationParameters
    | LineEndingParameters
    | SeparatorInsertionParameters,
    Field(discriminator="kind"),
]


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


class PreparedRstDocument(StrictContractModel):
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
    parser_capacity: ParserCapacity | None
    policy: PlanningPolicy
    units: tuple[AnalysisUnit, ...]
    recombination: RecombinationPlan
    semantic_digest: Sha256Identity | None = None

    @model_validator(mode="after")
    def coherent_state_and_identity(self) -> Self:
        if self.status is AnalysisPlanStatus.NOT_PLANNED:
            if self.parser_capacity is not None or self.units:
                raise ValueError("not_planned requires absent capacity and no units")
        elif self.parser_capacity is None:
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
                    "parser_capacity": self.parser_capacity,
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
    prepared_document: PreparedRstDocument
    analysis_plan: AnalysisPlan
    inventory_coverage: ExactCoverage
    primary_coverage: ExactCoverage
    retained_coverage: ExactCoverage
    mapping_coverage: ExactCoverage
    warnings: tuple[PreparationWarning, ...] = ()


class AdapterExecutionIdentity(StrictContractModel):
    distribution: str
    version: str


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
    "AdapterExecutionIdentity", "AnalysisPlan", "AnalysisPlanStatus", "AnalysisUnit",
    "BoundaryPreference", "CapacityUnit", "LineEndingParameters", "ParserCapacity", "PlanningPolicy",
    "PreparationExecutionEvidence", "PreparationOutcome", "PreparationPolicy", "PreparationWarning",
    "PreparationSemanticEvidence", "PreparedRange", "PreparedRstDocument",
    "PreparedSegment", "PreserveParameters", "RecombinationLink", "RecombinationPlan",
    "SegmentKind", "SeparatorInsertionParameters", "StructuralBoundary", "StructureKind",
    "TransformationParameters", "TransformationRecord", "UnicodeNormalizationParameters",
]
