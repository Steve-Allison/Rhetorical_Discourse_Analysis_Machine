"""Component identity and decision-complete inference evidence contracts."""

from enum import StrEnum
import math
from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from isanlp_rst.ingest.contracts.base import SemanticVersion, Sha256Identity, StrictContractModel
from isanlp_rst.ingest.contracts.source import SourceAnchor
from isanlp_rst.ingest.identity import semantic_sha256


class OutputFormalism(StrEnum):
    RST_TREE = "rst_tree"
    ERST_GRAPH = "erst_graph"


class EvidenceDetailPolicy(StrEnum):
    DECISION_COMPLETE = "decision_complete"
    NORMALIZED_DISTRIBUTIONS = "normalized_distributions"


class ComponentIdentityState(StrEnum):
    IMMUTABLE_RELEASE = "immutable_release"
    MUTABLE_INSTANCE = "mutable_instance"
    UNIDENTIFIED = "unidentified"
    NOT_USED = "not_used"


class ComponentFileIdentity(StrictContractModel):
    path: str
    role: str
    size_bytes: int = Field(gt=0)
    identity: Sha256Identity


class ImmutableComponentIdentity(StrictContractModel):
    state: Literal["immutable_release"] = "immutable_release"
    component: str
    release_id: str
    manifest_identity: Sha256Identity
    architecture: str
    capacity_identity: Sha256Identity | None = None
    files: tuple[ComponentFileIdentity, ...] = Field(min_length=1)


class MutableComponentIdentity(StrictContractModel):
    state: Literal["mutable_instance"] = "mutable_instance"
    component: str
    provider_type: str
    reason: str


class UnidentifiedComponentIdentity(StrictContractModel):
    state: Literal["unidentified"] = "unidentified"
    component: str
    provider_type: str
    reason: str


class NotUsedComponentIdentity(StrictContractModel):
    state: Literal["not_used"] = "not_used"
    component: str
    reason: str


type ComponentIdentity = Annotated[
    ImmutableComponentIdentity | MutableComponentIdentity | UnidentifiedComponentIdentity
    | NotUsedComponentIdentity,
    Field(discriminator="state"),
]


class CompositeAnalysisIdentity(StrictContractModel):
    primary_parser: ComponentIdentity
    segmenter: ComponentIdentity
    marker_refiner: ComponentIdentity
    erst_detector: ComponentIdentity
    erst_scorer: ComponentIdentity
    erst_decoder: ComponentIdentity
    calibration: ComponentIdentity
    relation_inventory: ComponentIdentity
    ontology_mapping: ComponentIdentity
    semantic_digest: Sha256Identity | None = None

    @model_validator(mode="after")
    def complete_identity(self) -> Self:
        payload = self.model_dump(exclude={"semantic_digest"})
        expected = Sha256Identity(hex_digest=semantic_sha256(payload))
        if self.semantic_digest is not None and self.semantic_digest != expected:
            raise ValueError("composite analysis identity mismatch")
        object.__setattr__(self, "semantic_digest", expected)
        return self

    @property
    def durable_cache_eligible(self) -> bool:
        return all(
            component.state in {
                ComponentIdentityState.IMMUTABLE_RELEASE,
                ComponentIdentityState.NOT_USED,
            }
            for component in (
                self.primary_parser,
                self.segmenter,
                self.marker_refiner,
                self.erst_detector,
                self.erst_scorer,
                self.erst_decoder,
                self.calibration,
                self.relation_inventory,
                self.ontology_mapping,
            )
        )


class LoadedComponentReceipt(StrictContractModel):
    component: str
    declared_identity: Sha256Identity
    resolved_member_identities: tuple[ComponentFileIdentity, ...]
    verified: Literal[True]


class ConfidenceKind(StrEnum):
    PROBABILITY = "probability"
    LOGIT = "logit"
    MARGIN = "margin"
    ENTROPY = "entropy"
    UNCALIBRATED_SCORE = "uncalibrated_score"
    DETERMINISTIC = "deterministic"


class ScoreValue(StrictContractModel):
    value: float
    confidence_kind: ConfidenceKind
    minimum: float
    maximum: float
    calibration_identity: Sha256Identity | None = None
    producing_component_identity: Sha256Identity

    @model_validator(mode="after")
    def within_declared_range(self) -> Self:
        if (
            not all(math.isfinite(value) for value in (self.value, self.minimum, self.maximum))
            or self.maximum < self.minimum
            or not self.minimum <= self.value <= self.maximum
        ):
            raise ValueError("score is outside its declared finite range")
        return self


class LabelledScore(StrictContractModel):
    label: str
    score: ScoreValue


class NormalizedDistribution(StrictContractModel):
    entries: tuple[LabelledScore, ...] = Field(min_length=1)
    tolerance: float = Field(default=1e-9, gt=0.0, le=1e-6)

    @model_validator(mode="after")
    def normalized_unique_probabilities(self) -> Self:
        labels = [entry.label for entry in self.entries]
        if len(labels) != len(set(labels)):
            raise ValueError("distribution labels must be unique")
        if any(entry.score.confidence_kind is not ConfidenceKind.PROBABILITY for entry in self.entries):
            raise ValueError("normalized distributions require probability scores")
        if abs(sum(entry.score.value for entry in self.entries) - 1.0) > self.tolerance:
            raise ValueError("normalized distribution probabilities must sum to one")
        return self


class MappingStatus(StrEnum):
    MAPPED = "mapped"
    IDENTITY_ONLY = "identity_only"
    NOT_MAPPED = "not_mapped"
    NOT_AVAILABLE = "not_available"


class RelationInterpretation(StrictContractModel):
    raw_label: str
    relation_scheme: str
    inventory_identity: Sha256Identity
    selected_ontology_concept: str | None = None
    mapping_status: MappingStatus
    mapping_algorithm: str | None = None
    mapping_version: SemanticVersion | None = None
    ontology_version: str | None = None
    ontology_identity: Sha256Identity | None = None
    confidence: ScoreValue | None = None

    @model_validator(mode="after")
    def mapping_fields_are_honest(self) -> Self:
        if self.mapping_status is MappingStatus.MAPPED and self.selected_ontology_concept is None:
            raise ValueError("mapped relation requires an ontology concept")
        if self.mapping_status is MappingStatus.IDENTITY_ONLY and self.selected_ontology_concept != self.raw_label:
            raise ValueError("identity_only concept must equal the raw relation label")
        return self


class SegmentationDecisionEvidence(StrictContractModel):
    decision_id: str
    boundary_id: str
    selected_boundary: bool
    decision_basis: Literal["model", "presegmented", "deterministic_rule"]
    confidence: ScoreValue | None = None
    distribution: NormalizedDistribution | None = None
    token_ids: tuple[str, ...]
    resulting_edu_ids: tuple[str, ...]
    producing_component_identity: Sha256Identity

    @model_validator(mode="after")
    def evidence_matches_basis(self) -> Self:
        if self.decision_basis == "presegmented" and (
            self.confidence is not None or self.distribution is not None
        ):
            raise ValueError("presegmented boundaries cannot fabricate provider scores")
        if self.distribution is not None and self.confidence is None:
            raise ValueError("segmentation distribution requires provider confidence")
        return self


class PrimaryStructureDecisionEvidence(StrictContractModel):
    decision_id: str
    node_ids: tuple[int, ...]
    primary_edge_ids: tuple[str, ...]
    analysed_start: int = Field(ge=0)
    analysed_end: int = Field(gt=0)
    selected_split: int | None = Field(default=None, ge=0)
    nuclearity: str
    relation: RelationInterpretation
    confidence: ScoreValue
    split_entropy: ScoreValue | None = None
    split_distribution: NormalizedDistribution | None = None
    relation_distribution: NormalizedDistribution | None = None
    nuclearity_distribution: NormalizedDistribution | None = None
    producing_component_identity: Sha256Identity

    @model_validator(mode="after")
    def ordered_span(self) -> Self:
        if self.analysed_end <= self.analysed_start:
            raise ValueError("primary decision analysed span is reversed")
        return self


class RefinementRecord(StrictContractModel):
    refinement_id: str
    decision_kind: str
    before_value: str
    after_value: str
    trigger_signal_ids: tuple[str, ...]
    trigger_anchors: tuple[SourceAnchor, ...]
    policy_identity: Sha256Identity
    algorithm_version: SemanticVersion
    graph_element_ids: tuple[str, ...]
    explanation_code: str
    semantic_digest: Sha256Identity | None = None

    @model_validator(mode="after")
    def changed_value_and_identity(self) -> Self:
        if self.before_value == self.after_value:
            raise ValueError("refinement before and after values must differ")
        if not self.trigger_signal_ids or not self.trigger_anchors:
            raise ValueError("refinement requires trigger identities and source anchors")
        if not self.graph_element_ids:
            raise ValueError("refinement requires affected graph elements")
        expected = Sha256Identity(hex_digest=semantic_sha256(self.model_dump(exclude={"semantic_digest"})))
        if self.semantic_digest is not None and self.semantic_digest != expected:
            raise ValueError("refinement semantic digest mismatch")
        object.__setattr__(self, "semantic_digest", expected)
        return self


class PrimaryInferenceEvidence(StrictContractModel):
    segmentation_decisions: tuple[SegmentationDecisionEvidence, ...]
    structure_decisions: tuple[PrimaryStructureDecisionEvidence, ...]
    refinements: tuple[RefinementRecord, ...]


class ErstDecision(StrEnum):
    ACCEPTED = "accepted"
    REJECTED_INSUFFICIENT_SIGNAL = "rejected_insufficient_signal"
    REJECTED_SCORE = "rejected_score"
    REJECTED_CONSTRAINT = "rejected_constraint"


class ErstCandidateDecision(StrictContractModel):
    candidate_id: str
    source_node_id: int
    target_node_id: int
    supporting_signal_ids: tuple[str, ...] = Field(min_length=1)
    edge_probability: ScoreValue
    relation: RelationInterpretation
    relation_probability: ScoreValue
    joint_selection_score: ScoreValue
    calibration_identity: Sha256Identity
    decision: ErstDecision
    decoder_order: int = Field(ge=0)
    secondary_edge_id: str | None = None

    @model_validator(mode="after")
    def accepted_edge_is_explicit(self) -> Self:
        if (self.decision is ErstDecision.ACCEPTED) != (self.secondary_edge_id is not None):
            raise ValueError("accepted eRST candidate must name exactly one secondary edge")
        if self.source_node_id == self.target_node_id:
            raise ValueError("eRST candidate cannot be a self-loop")
        return self


class NamedCount(StrictContractModel):
    name: str
    count: int = Field(ge=0)


class ErstDecodeReceipt(StrictContractModel):
    policy: str
    policy_version: SemanticVersion
    candidate_decision_ids: tuple[str, ...]
    input_count: int = Field(ge=0)
    accepted_count: int = Field(ge=0)
    rejected_count: int = Field(ge=0)
    constraint_checks: tuple[NamedCount, ...]
    rejection_reasons: tuple[NamedCount, ...]
    ordering_identity: Sha256Identity
    warnings: tuple[str, ...]
    semantic_digest: Sha256Identity | None = None

    @model_validator(mode="after")
    def counts_and_identity_reconcile(self) -> Self:
        if self.input_count != self.accepted_count + self.rejected_count:
            raise ValueError("eRST decoder counts do not reconcile")
        if self.input_count != len(self.candidate_decision_ids):
            raise ValueError("eRST decoder input count differs from ordered decisions")
        if len(self.candidate_decision_ids) != len(set(self.candidate_decision_ids)):
            raise ValueError("eRST decoder candidate decision identities must be unique")
        expected = Sha256Identity(hex_digest=semantic_sha256(self.model_dump(exclude={"semantic_digest"})))
        if self.semantic_digest is not None and self.semantic_digest != expected:
            raise ValueError("eRST decode receipt semantic digest mismatch")
        object.__setattr__(self, "semantic_digest", expected)
        return self


class SupportingSignalEvidence(StrictContractModel):
    signal_id: str
    signal_type: str
    anchors: tuple[SourceAnchor, ...] = Field(min_length=1)
    candidate_ids: tuple[str, ...] = Field(min_length=1)
    edge_ids: tuple[str, ...]


class ErstCompletionEvidence(StrictContractModel):
    signals: tuple[SupportingSignalEvidence, ...]
    candidate_decisions: tuple[ErstCandidateDecision, ...]
    decode_receipt: ErstDecodeReceipt
    scorer_identity: ComponentIdentity
    calibration_identity: ComponentIdentity
    relation_inventory_identity: ComponentIdentity
    semantic_digest: Sha256Identity | None = None

    @model_validator(mode="after")
    def complete_identity(self) -> Self:
        candidates = {item.candidate_id: item for item in self.candidate_decisions}
        if len(candidates) != len(self.candidate_decisions):
            raise ValueError("eRST candidate identities must be unique")
        if tuple(candidates) != self.decode_receipt.candidate_decision_ids:
            raise ValueError("eRST candidate order differs from decoder receipt")
        signal_ids = {signal.signal_id for signal in self.signals}
        if len(signal_ids) != len(self.signals):
            raise ValueError("eRST supporting signal identities must be unique")
        if any(
            not set(candidate.supporting_signal_ids) <= signal_ids
            for candidate in self.candidate_decisions
        ):
            raise ValueError("eRST candidate references an absent supporting signal")
        if any(
            not set(signal.candidate_ids) <= candidates.keys()
            for signal in self.signals
        ):
            raise ValueError("eRST signal references an absent candidate")
        accepted = tuple(
            item.secondary_edge_id
            for item in self.candidate_decisions
            if item.decision is ErstDecision.ACCEPTED
        )
        if len(accepted) != self.decode_receipt.accepted_count:
            raise ValueError("eRST accepted decisions differ from decoder receipt")
        if any(
            signal_id not in {
                supporting.signal_id
                for supporting in self.signals
                if candidate.candidate_id in supporting.candidate_ids
            }
            for candidate in self.candidate_decisions
            for signal_id in candidate.supporting_signal_ids
        ):
            raise ValueError("eRST candidate-to-signal links are not reciprocal")
        expected = Sha256Identity(hex_digest=semantic_sha256(self.model_dump(exclude={"semantic_digest"})))
        if self.semantic_digest is not None and self.semantic_digest != expected:
            raise ValueError("eRST completion semantic digest mismatch")
        object.__setattr__(self, "semantic_digest", expected)
        return self


class InferenceEvidence(StrictContractModel):
    request_identity: Sha256Identity
    analysed_document_identity: Sha256Identity
    composite_identity: Sha256Identity
    unit_identities: tuple[Sha256Identity, ...]
    primary_evidence_identity: Sha256Identity | None
    erst_evidence_identity: Sha256Identity | None
    output_node_count: int = Field(ge=0)
    output_primary_edge_count: int = Field(ge=0)
    output_secondary_edge_count: int = Field(ge=0)
    completed_unit_count: int = Field(ge=0)
    expected_unit_count: int = Field(ge=0)

    @model_validator(mode="after")
    def completed_units_do_not_exceed_expected(self) -> Self:
        if self.completed_unit_count > self.expected_unit_count:
            raise ValueError("completed inference units exceed expected units")
        return self


__all__ = [
    "ComponentFileIdentity", "ComponentIdentity", "ComponentIdentityState",
    "CompositeAnalysisIdentity", "ConfidenceKind", "ErstCandidateDecision",
    "ErstCompletionEvidence", "ErstDecision", "ErstDecodeReceipt", "EvidenceDetailPolicy",
    "ImmutableComponentIdentity", "InferenceEvidence", "LabelledScore",
    "LoadedComponentReceipt", "MappingStatus", "MutableComponentIdentity", "NamedCount",
    "NormalizedDistribution", "NotUsedComponentIdentity", "OutputFormalism",
    "PrimaryInferenceEvidence", "PrimaryStructureDecisionEvidence", "RefinementRecord",
    "RelationInterpretation", "ScoreValue", "SegmentationDecisionEvidence",
    "SupportingSignalEvidence", "UnidentifiedComponentIdentity",
]
