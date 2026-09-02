"""Analysis requests, parser results, outcomes, validation, and anchors."""

from enum import StrEnum
from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from rdam.rst.contracts import RstAnalysis
from rdam.rst.ingest.contracts.base import (
    PRODUCTION_CONTRACT,
    WRITE_CONTRACT_VERSION,
    ExactCoverage,
    SemanticVersion,
    Sha256Identity,
    StrictContractModel,
)
from rdam.rst.ingest.contracts.inference import (
    CompositeAnalysisIdentity,
    ErstCompletionEvidence,
    EvidenceDetailPolicy,
    LoadedComponentReceipt,
    OutputFormalism,
    PrimaryInferenceEvidence,
)
from rdam.rst.ingest.contracts.preparation import PreparationOutcome, PreparedRange
from rdam.rst.ingest.contracts.source import SourceAnchor
from rdam.rst.ingest.identity import (
    analysis_outcome_semantic_identity,
    parser_result_semantic_identity,
    semantic_sha256,
)


class AnalysisStatus(StrEnum):
    ANALYSED = "analysed"
    EMPTY_PRIMARY_DISCOURSE = "empty_primary_discourse"


class LossyInputPolicy(StrEnum):
    FORBID = "forbid"


class MarkerRefinementMode(StrEnum):
    DISABLED = "disabled"
    EVIDENCE_PRESERVING = "evidence_preserving"


class ValidationPolicy(StrictContractModel):
    policy_version: SemanticVersion
    required_checks: tuple[str, ...]
    advisory_checks: tuple[str, ...]

    @model_validator(mode="after")
    def unique_checks(self) -> Self:
        checks = (*self.required_checks, *self.advisory_checks)
        if len(checks) != len(set(checks)) or any(not check for check in checks):
            raise ValueError("validation check identifiers must be non-empty and unique")
        return self


class RelationInterpretationPolicy(StrictContractModel):
    relation_scheme: str
    ontology_mapping: Literal["disabled", "identity_only", "provider_mapping"]
    policy_version: SemanticVersion


class AnalysisPolicy(StrictContractModel):
    output_formalism: OutputFormalism
    evidence_detail: EvidenceDetailPolicy
    marker_refinement: MarkerRefinementMode
    validation: ValidationPolicy
    relation_interpretation: RelationInterpretationPolicy
    lossy_input: LossyInputPolicy = LossyInputPolicy.FORBID
    policy_version: SemanticVersion
    semantic_digest: Sha256Identity | None = None

    @model_validator(mode="after")
    def complete_identity(self) -> Self:
        expected = Sha256Identity(hex_digest=semantic_sha256(self.model_dump(exclude={"semantic_digest"})))
        if self.semantic_digest is not None and self.semantic_digest != expected:
            raise ValueError("analysis policy semantic digest mismatch")
        object.__setattr__(self, "semantic_digest", expected)
        return self


class AnalysisRequest(StrictContractModel):
    source_identity: Sha256Identity
    preparation_identity: Sha256Identity
    analysis_policy: AnalysisPolicy
    analysis_plan_identity: Sha256Identity
    parser_capacity_identity: Sha256Identity | None
    composite_analysis_identity: CompositeAnalysisIdentity
    pipeline_version: SemanticVersion
    production_contract_version: SemanticVersion
    semantic_digest: Sha256Identity | None = None

    @model_validator(mode="after")
    def complete_identity(self) -> Self:
        expected = Sha256Identity(hex_digest=semantic_sha256(self.model_dump(exclude={"semantic_digest"})))
        if self.semantic_digest is not None and self.semantic_digest != expected:
            raise ValueError("analysis request semantic digest mismatch")
        object.__setattr__(self, "semantic_digest", expected)
        return self


class AnalysedToken(StrictContractModel):
    token_id: str
    order: int = Field(ge=0)
    text: str
    character_range: PreparedRange
    source_anchors: tuple[SourceAnchor, ...]
    sentence_id: str
    paragraph_id: str
    transformation_ids: tuple[str, ...] = ()


class AnalysedEdu(StrictContractModel):
    edu_id: str
    order: int = Field(ge=0)
    text: str
    token_ids: tuple[str, ...] = Field(min_length=1)
    sentence_id: str
    paragraph_id: str
    prepared_segment_ids: tuple[str, ...] = Field(min_length=1)
    source_anchors: tuple[SourceAnchor, ...] = Field(min_length=1)


class FidelityClass(StrEnum):
    LOSSLESS = "lossless"
    LOSSY = "lossy"


class AnalysisSubstrateTransformation(StrictContractModel):
    transformation_id: str
    algorithm: str
    algorithm_version: SemanticVersion
    input_segment_ids: tuple[str, ...]
    output_token_ids: tuple[str, ...]
    parameters: tuple[tuple[str, str], ...]
    affected_ranges: tuple[PreparedRange, ...]
    source_anchors: tuple[SourceAnchor, ...]
    fidelity: FidelityClass
    semantic_digest: Sha256Identity | None = None

    @model_validator(mode="after")
    def complete_identity(self) -> Self:
        expected = Sha256Identity(hex_digest=semantic_sha256(self.model_dump(exclude={"semantic_digest"})))
        if self.semantic_digest is not None and self.semantic_digest != expected:
            raise ValueError("analysis substrate transformation identity mismatch")
        object.__setattr__(self, "semantic_digest", expected)
        return self


class TokenMapping(StrictContractModel):
    token_id: str
    edu_id: str
    sentence_id: str
    paragraph_id: str


class AnalysedDocument(StrictContractModel):
    text: str
    tokens: tuple[AnalysedToken, ...]
    edus: tuple[AnalysedEdu, ...]
    mappings: tuple[TokenMapping, ...]
    sentence_boundaries: tuple[PreparedRange, ...]
    paragraph_boundaries: tuple[PreparedRange, ...]
    structural_boundary_ids: tuple[str, ...]
    prepared_segment_ids: tuple[str, ...]
    source_anchors: tuple[SourceAnchor, ...]
    transformations: tuple[AnalysisSubstrateTransformation, ...]
    fidelity: FidelityClass
    character_coverage: ExactCoverage
    token_coverage: ExactCoverage
    edu_coverage: ExactCoverage
    semantic_digest: Sha256Identity | None = None

    @model_validator(mode="after")
    def exact_order_and_identity(self) -> Self:
        if any(token.order != index for index, token in enumerate(self.tokens)):
            raise ValueError("analysed tokens must have canonical order")
        if any(edu.order != index for index, edu in enumerate(self.edus)):
            raise ValueError("analysed EDUs must have canonical order")
        expected = Sha256Identity(hex_digest=semantic_sha256(self.model_dump(exclude={"semantic_digest"})))
        if self.semantic_digest is not None and self.semantic_digest != expected:
            raise ValueError("analysed document semantic digest mismatch")
        object.__setattr__(self, "semantic_digest", expected)
        return self


class LocalToGlobalMapping(StrictContractModel):
    unit_id: str
    local_id: str
    global_id: str


class StitchingDecision(StrictContractModel):
    decision_id: str
    predecessor_unit_id: str
    successor_unit_id: str
    relation: str
    nuclearity: str


class RecombinationReceipt(StrictContractModel):
    unit_identities: tuple[Sha256Identity, ...]
    local_result_identities: tuple[Sha256Identity, ...]
    segment_mappings: tuple[LocalToGlobalMapping, ...]
    node_mappings: tuple[LocalToGlobalMapping, ...]
    edge_mappings: tuple[LocalToGlobalMapping, ...]
    boundary_inputs: tuple[str, ...]
    nuclear_spine_inputs: tuple[str, ...]
    stitching_decisions: tuple[StitchingDecision, ...]
    warnings: tuple[str, ...]
    policy: str
    policy_version: SemanticVersion
    unit_durations_ms: tuple[float, ...]
    semantic_digest: Sha256Identity | None = None

    @model_validator(mode="after")
    def complete_identity(self) -> Self:
        if any(value < 0.0 for value in self.unit_durations_ms):
            raise ValueError("recombination unit durations cannot be negative")
        if len(self.unit_durations_ms) != len(self.unit_identities):
            raise ValueError("recombination timings must cover every analysis unit")
        expected = Sha256Identity(
            hex_digest=semantic_sha256(
                self.model_dump(exclude={"semantic_digest", "unit_durations_ms"})
            )
        )
        if self.semantic_digest is not None and self.semantic_digest != expected:
            raise ValueError("recombination receipt semantic digest mismatch")
        object.__setattr__(self, "semantic_digest", expected)
        return self


class CheckClassification(StrEnum):
    REQUIRED = "required"
    ADVISORY = "advisory"


class CheckOutcome(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    NOT_APPLICABLE = "not_applicable"


class ValidationCheckReceipt(StrictContractModel):
    check_id: str
    classification: CheckClassification
    outcome: CheckOutcome
    checked_count: int = Field(ge=0)
    affected_ids: tuple[str, ...]
    code: str | None = None


class ValidationReceipt(StrictContractModel):
    policy_version: SemanticVersion
    checks: tuple[ValidationCheckReceipt, ...]
    passed: bool
    graph_coverage: ExactCoverage
    anchor_coverage: ExactCoverage
    evidence_coverage: ExactCoverage
    warnings: tuple[str, ...]
    semantic_digest: Sha256Identity | None = None

    @model_validator(mode="after")
    def required_checks_and_identity(self) -> Self:
        required_pass = all(
            check.outcome is CheckOutcome.PASSED
            for check in self.checks
            if check.classification is CheckClassification.REQUIRED
        )
        if self.passed != required_pass:
            raise ValueError("validation disposition contradicts required checks")
        expected = Sha256Identity(hex_digest=semantic_sha256(self.model_dump(exclude={"semantic_digest"})))
        if self.semantic_digest is not None and self.semantic_digest != expected:
            raise ValueError("validation receipt semantic digest mismatch")
        object.__setattr__(self, "semantic_digest", expected)
        return self


class AnchorTargetKind(StrEnum):
    EDU = "edu"
    NODE = "node"
    PRIMARY_EDGE = "primary_edge"
    SECONDARY_EDGE = "secondary_edge"
    DECISION = "decision"
    SUPPORTING_SIGNAL = "supporting_signal"


class EndpointAnchor(StrictContractModel):
    node_id: int
    token_ids: tuple[str, ...]
    edu_ids: tuple[str, ...]
    prepared_segment_ids: tuple[str, ...]
    source_anchors: tuple[SourceAnchor, ...]


class AnalysisAnchor(StrictContractModel):
    target_id: str
    target_kind: AnchorTargetKind
    token_ids: tuple[str, ...]
    edu_ids: tuple[str, ...]
    prepared_segment_ids: tuple[str, ...]
    source_anchors: tuple[SourceAnchor, ...]
    source_endpoint: EndpointAnchor | None = None
    target_endpoint: EndpointAnchor | None = None
    supporting_signal_ids: tuple[str, ...] = ()

    @model_validator(mode="after")
    def relation_endpoints_are_complete(self) -> Self:
        relation = self.target_kind in {AnchorTargetKind.PRIMARY_EDGE, AnchorTargetKind.SECONDARY_EDGE}
        if relation != (self.source_endpoint is not None and self.target_endpoint is not None):
            raise ValueError("relation anchors require distinct source and target endpoint anchors")
        if (
            relation
            and self.source_endpoint is not None
            and self.target_endpoint is not None
            and self.source_endpoint.node_id == self.target_endpoint.node_id
        ):
            raise ValueError("relation anchor endpoints must identify distinct nodes")
        return self


class ParserAnalysisSemanticEvidence(StrictContractModel):
    policy: AnalysisPolicy
    analysed_document: AnalysedDocument
    analysis: RstAnalysis
    anchors: tuple[AnalysisAnchor, ...]
    primary_inference: PrimaryInferenceEvidence
    erst_completion: ErstCompletionEvidence | None
    composite_identity: CompositeAnalysisIdentity
    loaded_components: tuple[LoadedComponentReceipt, ...]
    recombination: RecombinationReceipt | None
    validation: ValidationReceipt

    @model_validator(mode="after")
    def formalism_evidence_agrees(self) -> Self:
        expects_erst = self.policy.output_formalism is OutputFormalism.ERST_GRAPH
        if expects_erst != (self.erst_completion is not None):
            raise ValueError("eRST evidence presence must match output formalism")
        return self


class UnitExecutionReceipt(StrictContractModel):
    unit_id: str
    duration_ms: float = Field(ge=0.0)
    device: str


class ParserAnalysisExecutionEvidence(StrictContractModel):
    execution_id: str
    duration_ms: float = Field(ge=0.0)
    device: str
    unit_executions: tuple[UnitExecutionReceipt, ...]


class ParserAnalysisResult(StrictContractModel):
    contract: Literal["isanlp_rst.production"] = PRODUCTION_CONTRACT
    contract_version: Literal["2.0.0"] = WRITE_CONTRACT_VERSION
    kind: Literal["parser_analysis_result"] = "parser_analysis_result"
    semantic: ParserAnalysisSemanticEvidence
    execution: ParserAnalysisExecutionEvidence
    semantic_digest: Sha256Identity | None = None

    @model_validator(mode="after")
    def complete_identity(self) -> Self:
        expected = Sha256Identity(hex_digest=parser_result_semantic_identity(self))
        if self.semantic_digest is not None and self.semantic_digest != expected:
            raise ValueError("parser analysis result semantic digest mismatch")
        object.__setattr__(self, "semantic_digest", expected)
        return self

    @property
    def analysis(self) -> RstAnalysis:
        return self.semantic.analysis

    @property
    def analysed_document(self) -> AnalysedDocument:
        return self.semantic.analysed_document

    @property
    def validation_receipt(self) -> ValidationReceipt:
        return self.semantic.validation

    @property
    def composite_analysis_identity(self) -> CompositeAnalysisIdentity:
        return self.semantic.composite_identity

    @property
    def loaded_component_receipts(self) -> tuple[LoadedComponentReceipt, ...]:
        return self.semantic.loaded_components


class CacheStatus(StrEnum):
    BYPASS = "bypass"
    MISS = "miss"
    HIT = "hit"
    WRITTEN = "written"


class AnalysisExecutionEvidence(StrictContractModel):
    execution_id: str
    duration_ms: float = Field(ge=0.0)
    device: str
    cache_status: CacheStatus
    cache_entry_identity: Sha256Identity | None = None
    unit_executions: tuple[UnitExecutionReceipt, ...]
    software_version: str
    source_revision: str


class AnalysisSemanticEvidence(StrictContractModel):
    preparation: PreparationOutcome
    request: AnalysisRequest
    policy: AnalysisPolicy
    analysed_document: AnalysedDocument | None
    composite_identity: CompositeAnalysisIdentity
    parser_result: ParserAnalysisResult | None
    status: AnalysisStatus
    analysis: RstAnalysis | None
    primary_inference: PrimaryInferenceEvidence | None
    erst_completion: ErstCompletionEvidence | None
    anchors: tuple[AnalysisAnchor, ...]
    recombination: RecombinationReceipt | None
    validation: ValidationReceipt | None
    cache_request_identity: Sha256Identity | None

    @model_validator(mode="after")
    def status_payload_is_discriminated(self) -> Self:
        if self.status is AnalysisStatus.ANALYSED:
            if (
                self.analysis is None
                or self.analysed_document is None
                or self.parser_result is None
                or self.primary_inference is None
                or self.validation is None
            ):
                raise ValueError("analysed semantic evidence requires parser result, graph, and validation")
            parser = self.parser_result.semantic
            if (
                parser.policy != self.policy
                or parser.composite_identity != self.composite_identity
                or parser.analysis != self.analysis
                or parser.primary_inference != self.primary_inference
                or parser.erst_completion != self.erst_completion
                or parser.recombination != self.recombination
            ):
                raise ValueError("embedded parser result and analysis semantic evidence differ")
            if (
                self.analysed_document.text != parser.analysed_document.text
                or tuple(token.token_id for token in self.analysed_document.tokens)
                != tuple(token.token_id for token in parser.analysed_document.tokens)
                or tuple(edu.edu_id for edu in self.analysed_document.edus)
                != tuple(edu.edu_id for edu in parser.analysed_document.edus)
            ):
                raise ValueError("source enrichment changed the parser inference substrate")
        elif any(
            value is not None
            for value in (
                self.analysed_document,
                self.parser_result,
                self.analysis,
                self.primary_inference,
                self.erst_completion,
                self.recombination,
                self.validation,
            )
        ) or self.anchors:
            raise ValueError("empty primary outcome cannot fabricate analysis evidence")
        return self


class AnalysedOutcome(StrictContractModel):
    contract: Literal["isanlp_rst.production"] = PRODUCTION_CONTRACT
    contract_version: Literal["2.0.0"] = WRITE_CONTRACT_VERSION
    kind: Literal["analysed_outcome"] = "analysed_outcome"
    semantic: AnalysisSemanticEvidence
    execution: AnalysisExecutionEvidence
    semantic_digest: Sha256Identity | None = None

    @model_validator(mode="after")
    def analysed_and_identified(self) -> Self:
        if self.semantic.status is not AnalysisStatus.ANALYSED:
            raise ValueError("analysed outcome requires analysed status")
        return _set_outcome_identity(self)

    @property
    def status(self) -> AnalysisStatus:
        return self.semantic.status


class EmptyPrimaryAnalysisOutcome(StrictContractModel):
    contract: Literal["isanlp_rst.production"] = PRODUCTION_CONTRACT
    contract_version: Literal["2.0.0"] = WRITE_CONTRACT_VERSION
    kind: Literal["empty_primary_analysis_outcome"] = "empty_primary_analysis_outcome"
    semantic: AnalysisSemanticEvidence
    execution: AnalysisExecutionEvidence
    semantic_digest: Sha256Identity | None = None

    @model_validator(mode="after")
    def empty_and_identified(self) -> Self:
        if self.semantic.status is not AnalysisStatus.EMPTY_PRIMARY_DISCOURSE:
            raise ValueError("empty-primary outcome requires empty_primary_discourse status")
        return _set_outcome_identity(self)

    @property
    def status(self) -> AnalysisStatus:
        return self.semantic.status


type ProductionAnalysisOutcome = Annotated[
    AnalysedOutcome | EmptyPrimaryAnalysisOutcome,
    Field(discriminator="kind"),
]


def _set_outcome_identity[T: AnalysedOutcome | EmptyPrimaryAnalysisOutcome](value: T) -> T:
    expected = Sha256Identity(hex_digest=analysis_outcome_semantic_identity(value))
    if value.semantic_digest is not None and value.semantic_digest != expected:
        raise ValueError("analysis outcome semantic digest mismatch")
    object.__setattr__(value, "semantic_digest", expected)
    return value


__all__ = [
    "AnalysedDocument", "AnalysedEdu", "AnalysedOutcome", "AnalysedToken",
    "AnalysisAnchor", "AnalysisExecutionEvidence", "AnalysisPolicy", "AnalysisRequest",
    "AnalysisSemanticEvidence", "AnalysisStatus", "AnalysisSubstrateTransformation",
    "AnchorTargetKind", "CacheStatus", "CheckClassification", "CheckOutcome",
    "EmptyPrimaryAnalysisOutcome", "EndpointAnchor", "FidelityClass", "LocalToGlobalMapping",
    "LossyInputPolicy", "MarkerRefinementMode", "ParserAnalysisExecutionEvidence",
    "ParserAnalysisResult", "ParserAnalysisSemanticEvidence", "ProductionAnalysisOutcome",
    "RecombinationReceipt", "RelationInterpretationPolicy", "StitchingDecision",
    "TokenMapping", "UnitExecutionReceipt", "ValidationCheckReceipt", "ValidationPolicy",
    "ValidationReceipt",
]
