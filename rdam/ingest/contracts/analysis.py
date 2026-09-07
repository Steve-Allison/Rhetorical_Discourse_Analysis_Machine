"""Analysis requests, parser results, outcomes, validation, and anchors."""

from collections.abc import Mapping
from bisect import bisect_left, bisect_right
from enum import StrEnum
from functools import cached_property
import json
from typing import Annotated, Any, Literal, Self, cast

from pydantic import Field, TypeAdapter, ValidationInfo, field_serializer, field_validator, model_validator

from rdam.rst.contracts import RstAnalysis
from rdam.ingest.contracts.base import (
    PRODUCTION_CONTRACT,
    WRITE_CONTRACT_VERSION,
    CurrentContractVersion,
    ExactCoverage,
    SemanticVersion,
    Sha256Identity,
    StrictContractModel,
)
from rdam.ingest.contracts.inference import (
    CompositeAnalysisIdentity,
    ErstCompletionEvidence,
    EvidenceDetailPolicy,
    LoadedComponentReceipt,
    OutputFormalism,
    PrimaryInferenceEvidence,
)
from rdam.ingest.contracts.preparation import PreparationOutcome, PreparedRange
from rdam.ingest.contracts.inference_storage import StoredPrimaryInferenceEvidence
from rdam.ingest.contracts.source import SourceAnchor, TextSpanAnchor
from rdam.ingest.contracts.graph import StoredRstGraph
from rdam.ingest.identity import (
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
    character_range: PreparedRange
    token_ids: tuple[str, ...] = Field(min_length=1)
    sentence_id: str = Field(description="Sentence of the first overlapping token; an EDU can extend across groups.")
    paragraph_id: str = Field(description="Paragraph of the first overlapping token; resolve all groups through token_ids.")
    prepared_segment_ids: tuple[str, ...] = Field(min_length=1)
    source_anchors: tuple[SourceAnchor, ...] = Field(min_length=1)


def _document_text_anchor(
    text: str, span: PreparedRange, document_anchors: tuple[SourceAnchor, ...],
) -> TextSpanAnchor | None:
    if not 0 <= span.start < span.end <= len(text):
        raise ValueError("stored substrate range lies outside its analysed document")
    if len(document_anchors) != 1 or not isinstance(document_anchors[0], TextSpanAnchor):
        return None
    return TextSpanAnchor(
        artifact_identity=document_anchors[0].artifact_identity,
        start=span.start, end=span.end, quote=text[span.start:span.end],
    )


class StoredAnalysedToken(StrictContractModel):
    """Array order and document ranges replace repeated token text and source anchors."""

    token_id: str
    character_range: PreparedRange
    sentence_id: str
    paragraph_id: str
    transformation_ids: tuple[str, ...] = ()
    text_override: str | None = None
    source_anchors_override: tuple[SourceAnchor, ...] | None = None

    @classmethod
    def capture(cls, token: AnalysedToken, text: str, anchors: tuple[SourceAnchor, ...]) -> Self:
        anchor = _document_text_anchor(text, token.character_range, anchors)
        return cls(
            token_id=token.token_id, character_range=token.character_range,
            sentence_id=token.sentence_id, paragraph_id=token.paragraph_id,
            transformation_ids=token.transformation_ids,
            text_override=None if token.text == text[token.character_range.start:token.character_range.end] else token.text,
            source_anchors_override=None if anchor is not None and token.source_anchors == (anchor,) else token.source_anchors,
        )

    def resolve(self, order: int, text: str, anchors: tuple[SourceAnchor, ...]) -> AnalysedToken:
        anchor = _document_text_anchor(text, self.character_range, anchors)
        source_text = text[self.character_range.start:self.character_range.end]
        if self.text_override == source_text:
            raise ValueError("stored token text redundantly repeats its source range")
        if self.source_anchors_override is None:
            if anchor is None:
                raise ValueError("stored token requires explicit source anchors for this document")
            resolved_anchors: tuple[SourceAnchor, ...] = (anchor,)
        else:
            if anchor is not None and self.source_anchors_override == (anchor,):
                raise ValueError("stored token anchors redundantly repeat its document range")
            resolved_anchors = self.source_anchors_override
        return AnalysedToken(
            token_id=self.token_id, order=order, character_range=self.character_range,
            text=source_text if self.text_override is None else self.text_override,
            sentence_id=self.sentence_id, paragraph_id=self.paragraph_id,
            transformation_ids=self.transformation_ids, source_anchors=resolved_anchors,
        )


class StoredAnalysedEdu(StrictContractModel):
    """Preserve native EDU membership and refer to source text when it is exact."""

    edu_id: str
    token_ids: tuple[str, ...] = Field(min_length=1)
    sentence_id: str = Field(description="Sentence of the first overlapping token; an EDU can extend across groups.")
    paragraph_id: str = Field(description="Paragraph of the first overlapping token; resolve all groups through token_ids.")
    prepared_segment_ids: tuple[str, ...] = Field(min_length=1)
    character_range: PreparedRange
    text_override: str | None
    source_anchors_override: tuple[SourceAnchor, ...] | None

    @classmethod
    def capture(cls, edu: AnalysedEdu, text: str, anchors: tuple[SourceAnchor, ...]) -> Self:
        anchor = _document_text_anchor(text, edu.character_range, anchors)
        return cls(
            edu_id=edu.edu_id, token_ids=edu.token_ids,
            sentence_id=edu.sentence_id, paragraph_id=edu.paragraph_id,
            prepared_segment_ids=edu.prepared_segment_ids, character_range=edu.character_range,
            text_override=None if edu.text == text[edu.character_range.start:edu.character_range.end] else edu.text,
            source_anchors_override=None if anchor is not None and edu.source_anchors == (anchor,) else edu.source_anchors,
        )

    def resolve(self, order: int, text: str, anchors: tuple[SourceAnchor, ...]) -> AnalysedEdu:
        anchor = _document_text_anchor(text, self.character_range, anchors)
        source_text = text[self.character_range.start:self.character_range.end]
        if self.text_override == source_text:
            raise ValueError("stored EDU text redundantly repeats its source range")
        if self.source_anchors_override is None:
            if anchor is None:
                raise ValueError("stored EDU requires explicit source anchors for this document")
            resolved_anchors: tuple[SourceAnchor, ...] = (anchor,)
        else:
            if not self.source_anchors_override:
                raise ValueError("stored EDU requires at least one source anchor")
            if anchor is not None and self.source_anchors_override == (anchor,):
                raise ValueError("stored EDU anchors redundantly repeat its document range")
            resolved_anchors = self.source_anchors_override
        return AnalysedEdu(
            edu_id=self.edu_id, order=order, character_range=self.character_range,
            text=source_text if self.text_override is None else self.text_override, token_ids=self.token_ids,
            sentence_id=self.sentence_id, paragraph_id=self.paragraph_id,
            prepared_segment_ids=self.prepared_segment_ids, source_anchors=resolved_anchors,
        )


_STORED_TOKENS = TypeAdapter(tuple[StoredAnalysedToken, ...])
_STORED_EDUS = TypeAdapter(tuple[StoredAnalysedEdu, ...])


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
    source_anchors: tuple[SourceAnchor, ...]
    tokens: tuple[AnalysedToken, ...]
    edus: tuple[AnalysedEdu, ...]
    sentence_boundaries: tuple[PreparedRange, ...]
    paragraph_boundaries: tuple[PreparedRange, ...]
    structural_boundary_ids: tuple[str, ...]
    prepared_segment_ids: tuple[str, ...]
    transformations: tuple[AnalysisSubstrateTransformation, ...]
    fidelity: FidelityClass
    character_coverage: ExactCoverage
    token_coverage: ExactCoverage
    edu_coverage: ExactCoverage
    semantic_digest: Sha256Identity | None = None

    @field_validator("tokens", mode="before", json_schema_input_type=tuple[StoredAnalysedToken, ...])
    @classmethod
    def resolve_stored_tokens(cls, value: Any, info: ValidationInfo) -> tuple[AnalysedToken, ...]:
        if isinstance(value, tuple) and all(isinstance(token, AnalysedToken) for token in cast(tuple[object, ...], value)):
            return cast(tuple[AnalysedToken, ...], value)
        if "text" not in info.data or "source_anchors" not in info.data:
            raise ValueError("stored tokens require validated document text and source anchors")
        stored = (
            _STORED_TOKENS.validate_json(json.dumps(value, allow_nan=False))
            if info.mode == "json" else _STORED_TOKENS.validate_python(value)
        )
        return tuple(token.resolve(order, info.data["text"], info.data["source_anchors"]) for order, token in enumerate(stored))

    @field_serializer("tokens")
    def store_tokens(self, value: tuple[AnalysedToken, ...]) -> tuple[StoredAnalysedToken, ...]:
        return tuple(StoredAnalysedToken.capture(token, self.text, self.source_anchors) for token in value)

    @field_validator("edus", mode="before", json_schema_input_type=tuple[StoredAnalysedEdu, ...])
    @classmethod
    def resolve_stored_edus(cls, value: Any, info: ValidationInfo) -> tuple[AnalysedEdu, ...]:
        if isinstance(value, tuple) and all(isinstance(edu, AnalysedEdu) for edu in cast(tuple[object, ...], value)):
            return cast(tuple[AnalysedEdu, ...], value)
        if "text" not in info.data or "source_anchors" not in info.data:
            raise ValueError("stored EDUs require validated document text and source anchors")
        stored = (
            _STORED_EDUS.validate_json(json.dumps(value, allow_nan=False))
            if info.mode == "json" else _STORED_EDUS.validate_python(value)
        )
        return tuple(edu.resolve(order, info.data["text"], info.data["source_anchors"]) for order, edu in enumerate(stored))

    @field_serializer("edus")
    def store_edus(self, value: tuple[AnalysedEdu, ...]) -> tuple[StoredAnalysedEdu, ...]:
        return tuple(StoredAnalysedEdu.capture(edu, self.text, self.source_anchors) for edu in value)

    @model_validator(mode="after")
    def exact_order_and_identity(self) -> Self:
        if any(token.order != index for index, token in enumerate(self.tokens)):
            raise ValueError("analysed tokens must have canonical order")
        if any(edu.order != index for index, edu in enumerate(self.edus)):
            raise ValueError("analysed EDUs must have canonical order")
        tokens = {token.token_id: token for token in self.tokens}
        edus = {edu.edu_id: edu for edu in self.edus}
        if len(tokens) != len(self.tokens) or len(edus) != len(self.edus):
            raise ValueError("analysed token and EDU identities must be unique")
        for ranges in (tuple(token.character_range for token in self.tokens), tuple(edu.character_range for edu in self.edus)):
            previous_end = 0
            for span in ranges:
                if not previous_end <= span.start < span.end <= len(self.text):
                    raise ValueError("analysed token and EDU ranges must be ordered within the document")
                previous_end = span.end
        starts = tuple(token.character_range.start for token in self.tokens)
        ends = tuple(token.character_range.end for token in self.tokens)
        memberships: set[str] = set()
        previous_edu_end = 0
        for edu in self.edus:
            if self.text[previous_edu_end:edu.character_range.start].strip():
                raise ValueError("EDU ranges leave source characters uncovered")
            previous_edu_end = edu.character_range.end
            first = bisect_right(ends, edu.character_range.start)
            stop = bisect_left(starts, edu.character_range.end)
            expected_tokens = tuple(token.token_id for token in self.tokens[first:stop])
            if edu.token_ids != expected_tokens:
                raise ValueError("EDU membership must match exact ordered token overlaps")
            memberships.update(edu.token_ids)
        if self.text[previous_edu_end:].strip():
            raise ValueError("EDU ranges leave source characters uncovered")
        if memberships != tokens.keys():
            raise ValueError("EDU memberships must cover every analysed token")
        expected = Sha256Identity(hex_digest=semantic_sha256(self.model_dump(exclude={"semantic_digest"})))
        if self.semantic_digest is not None and self.semantic_digest != expected:
            raise ValueError("analysed document semantic digest mismatch")
        object.__setattr__(self, "semantic_digest", expected)
        return self

    @property
    def mappings(self) -> tuple[TokenMapping, ...]:
        """Resolve membership from its owners without persisting a duplicate table."""
        memberships: dict[str, list[str]] = {token.token_id: [] for token in self.tokens}
        for edu in self.edus:
            for token_id in edu.token_ids:
                memberships[token_id].append(edu.edu_id)
        return tuple(
            TokenMapping(
                token_id=token.token_id,
                edu_id=edu_id,
                sentence_id=token.sentence_id,
                paragraph_id=token.paragraph_id,
            )
            for token in self.tokens
            for edu_id in memberships[token.token_id]
        )


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
            hex_digest=semantic_sha256(self.model_dump(exclude={"semantic_digest", "unit_durations_ms"}))
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
    primary_inference: PrimaryInferenceEvidence
    erst_completion: ErstCompletionEvidence | None
    composite_identity: CompositeAnalysisIdentity
    loaded_components: tuple[LoadedComponentReceipt, ...]
    recombination: RecombinationReceipt | None
    validation: ValidationReceipt

    @field_validator("primary_inference", mode="before", json_schema_input_type=StoredPrimaryInferenceEvidence)
    @classmethod
    def resolve_stored_inference(cls, value: Any, info: ValidationInfo) -> PrimaryInferenceEvidence:
        if isinstance(value, PrimaryInferenceEvidence):
            return value
        stored = (
            StoredPrimaryInferenceEvidence.model_validate_json(json.dumps(value, allow_nan=False))
            if info.mode == "json" else StoredPrimaryInferenceEvidence.model_validate(value)
        )
        return stored.resolve()

    @field_serializer("primary_inference")
    def store_inference(self, value: PrimaryInferenceEvidence) -> StoredPrimaryInferenceEvidence:
        return StoredPrimaryInferenceEvidence.capture(value)

    @field_validator("analysis", mode="before", json_schema_input_type=StoredRstGraph)
    @classmethod
    def resolve_stored_graph(cls, value: Any, info: ValidationInfo) -> RstAnalysis:
        if isinstance(value, RstAnalysis):
            return value
        document = info.data.get("analysed_document")
        if not isinstance(document, AnalysedDocument):
            raise ValueError("stored graph requires its validated analysed document")
        stored = (
            StoredRstGraph.model_validate_json(json.dumps(value, allow_nan=False))
            if info.mode == "json" else StoredRstGraph.model_validate(value)
        )
        return stored.resolve(document.text)

    @field_serializer("analysis")
    def store_graph(self, value: RstAnalysis) -> StoredRstGraph:
        return StoredRstGraph.capture(value, self.analysed_document.text)

    def model_copy(self, *, update: Mapping[str, Any] | None = None, deep: bool = False) -> Self:
        if update is not None and "anchors" in update:
            raise ValueError("parser anchors are derived from canonical evidence")
        copied = super().model_copy(update=update, deep=deep)
        if "_anchor_projection" in copied.__dict__:
            object.__delattr__(copied, "_anchor_projection")
        return copied

    @cached_property
    def _anchor_projection(self) -> tuple[AnalysisAnchor, ...]:
        from rdam.ingest.parser_result import analysis_anchors

        return analysis_anchors(
            self.analysis, self.analysed_document, self.primary_inference,
            document_identity=self.analysis.document_id,
        )

    @property
    def anchors(self) -> tuple[AnalysisAnchor, ...]:
        return self._anchor_projection

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
    contract_version: CurrentContractVersion = WRITE_CONTRACT_VERSION
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
    parser_result: ParserAnalysisResult | None
    status: AnalysisStatus
    validation: ValidationReceipt | None
    cache_request_identity: Sha256Identity | None

    def model_copy(self, *, update: Mapping[str, Any] | None = None, deep: bool = False) -> Self:
        copied = super().model_copy(update=update, deep=deep)
        for name in ("_source_document", "_source_anchors"):
            if name in copied.__dict__:
                object.__delattr__(copied, name)
        return copied

    @cached_property
    def _source_document(self) -> AnalysedDocument | None:
        """Resolve source mappings without constructing descendant graph views."""
        if self.parser_result is None:
            return None
        from rdam.ingest.enrichment import enrich_parser_document

        return enrich_parser_document(self.preparation, self.parser_result)

    @cached_property
    def _source_anchors(self) -> tuple[AnalysisAnchor, ...]:
        document = self.analysed_document
        if self.parser_result is None or document is None:
            return ()
        from rdam.ingest.enrichment import enrich_parser_anchors

        return enrich_parser_anchors(self.preparation, self.parser_result, document)

    @property
    def analysed_document(self) -> AnalysedDocument | None:
        return self._source_document

    @property
    def anchors(self) -> tuple[AnalysisAnchor, ...]:
        return self._source_anchors

    @property
    def policy(self) -> AnalysisPolicy:
        return self.request.analysis_policy

    @property
    def composite_identity(self) -> CompositeAnalysisIdentity:
        return self.request.composite_analysis_identity

    @property
    def analysis(self) -> RstAnalysis | None:
        return self.parser_result.semantic.analysis if self.parser_result is not None else None

    @property
    def primary_inference(self) -> PrimaryInferenceEvidence | None:
        return self.parser_result.semantic.primary_inference if self.parser_result is not None else None

    @property
    def erst_completion(self) -> ErstCompletionEvidence | None:
        return self.parser_result.semantic.erst_completion if self.parser_result is not None else None

    @property
    def recombination(self) -> RecombinationReceipt | None:
        return self.parser_result.semantic.recombination if self.parser_result is not None else None

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
        elif (
            any(
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
            )
            or self.anchors
        ):
            raise ValueError("empty primary outcome cannot fabricate analysis evidence")
        return self


class AnalysedOutcome(StrictContractModel):
    contract: Literal["isanlp_rst.production"] = PRODUCTION_CONTRACT
    contract_version: CurrentContractVersion = WRITE_CONTRACT_VERSION
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
    contract_version: CurrentContractVersion = WRITE_CONTRACT_VERSION
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
    "AnalysedDocument",
    "AnalysedEdu",
    "AnalysedOutcome",
    "AnalysedToken",
    "AnalysisAnchor",
    "AnalysisExecutionEvidence",
    "AnalysisPolicy",
    "AnalysisRequest",
    "AnalysisSemanticEvidence",
    "AnalysisStatus",
    "AnalysisSubstrateTransformation",
    "AnchorTargetKind",
    "CacheStatus",
    "CheckClassification",
    "CheckOutcome",
    "EmptyPrimaryAnalysisOutcome",
    "EndpointAnchor",
    "FidelityClass",
    "LocalToGlobalMapping",
    "LossyInputPolicy",
    "MarkerRefinementMode",
    "ParserAnalysisExecutionEvidence",
    "ParserAnalysisResult",
    "ParserAnalysisSemanticEvidence",
    "ProductionAnalysisOutcome",
    "RecombinationReceipt",
    "RelationInterpretationPolicy",
    "StitchingDecision",
    "TokenMapping",
    "UnitExecutionReceipt",
    "ValidationCheckReceipt",
    "ValidationPolicy",
    "ValidationReceipt",
]
