"""Store native classifier inventories and score metadata once, preserving values."""

from collections.abc import Iterator
from typing import Literal, Self

from pydantic import Field, model_validator

from rdam.ingest.contracts.base import SemanticVersion, Sha256Identity, StrictContractModel
from rdam.ingest.contracts.decoding import NetworkTransitionDecision
from rdam.ingest.contracts.inference import (
    ConfidenceKind, JointRelationNuclearityEvidence, LabelledScore, MappingStatus,
    NormalizedDistribution, PrimaryInferenceEvidence, PrimaryStructureDecisionEvidence,
    RefinementRecord, RelationInterpretation, ScoreValue, SegmentationDecisionEvidence,
)
from rdam.ingest.vocabulary import RuntimeRelationVocabulary


class ScoreContext(StrictContractModel):
    confidence_kind: ConfidenceKind
    minimum: float
    maximum: float
    calibration_identity: Sha256Identity | None
    producing_component_identity: Sha256Identity


class StoredScore(StrictContractModel):
    value: float
    context: int = Field(ge=0, description="Index into the owning score_contexts array.")

    def resolve(self, contexts: tuple[ScoreContext, ...]) -> ScoreValue:
        if self.context >= len(contexts):
            raise ValueError("score references an absent context")
        return ScoreValue(value=self.value, **contexts[self.context].model_dump())


class _ScoreWriter:
    def __init__(self) -> None:
        self.contexts: list[ScoreContext] = []
        self.indices: dict[str, int] = {}

    def capture(self, score: ScoreValue | None) -> StoredScore | None:
        if score is None:
            return None
        context = ScoreContext.model_validate(score.model_dump(exclude={"value"}))
        key = context.model_dump_json()
        if key not in self.indices:
            self.indices[key] = len(self.contexts)
            self.contexts.append(context)
        return StoredScore(value=score.value, context=self.indices[key])


class StoredLabelledScore(StrictContractModel):
    label: str
    score: StoredScore


class StoredDistribution(StrictContractModel):
    entries: tuple[StoredLabelledScore, ...] = Field(min_length=1)
    tolerance: float

    def resolve(self, contexts: tuple[ScoreContext, ...]) -> NormalizedDistribution:
        return NormalizedDistribution(
            entries=tuple(LabelledScore(label=item.label, score=item.score.resolve(contexts)) for item in self.entries),
            tolerance=self.tolerance,
        )

    @classmethod
    def capture(cls, value: NormalizedDistribution, writer: _ScoreWriter) -> Self:
        entries: list[StoredLabelledScore] = []
        for item in value.entries:
            score = writer.capture(item.score)
            if score is None:
                raise ValueError("a labelled distribution entry requires its score")
            entries.append(StoredLabelledScore(label=item.label, score=score))
        return cls(entries=tuple(entries), tolerance=value.tolerance)


def _distribution(value: NormalizedDistribution | None, writer: _ScoreWriter) -> StoredDistribution | None:
    return None if value is None else StoredDistribution.capture(value, writer)


class StoredRelationInterpretation(StrictContractModel):
    raw_label: str
    relation_scheme: str
    inventory_identity: Sha256Identity
    selected_ontology_concept: str | None
    mapping_status: MappingStatus
    mapping_reason: str | None
    mapping_algorithm: str | None
    mapping_version: SemanticVersion | None
    ontology_version: str | None
    ontology_identity: Sha256Identity | None
    confidence: StoredScore | None

    def resolve(self, contexts: tuple[ScoreContext, ...]) -> RelationInterpretation:
        return RelationInterpretation(
            **self.model_dump(exclude={"confidence"}),
            confidence=None if self.confidence is None else self.confidence.resolve(contexts),
        )


class StoredSegmentationDecision(StrictContractModel):
    decision_id: str
    boundary_id: str
    selected_boundary: bool
    decision_basis: Literal["model", "presegmented", "deterministic_rule"]
    confidence: StoredScore | None
    distribution: StoredDistribution | None
    scores_unavailable_reason: Literal["presegmented_input", "deterministic_boundary_rule", "not_captured_by_backend"] | None
    token_ids: tuple[str, ...]
    resulting_edu_ids: tuple[str, ...]
    producing_component_identity: Sha256Identity

    def resolve(self, contexts: tuple[ScoreContext, ...]) -> SegmentationDecisionEvidence:
        return SegmentationDecisionEvidence(
            **self.model_dump(exclude={"confidence", "distribution"}),
            confidence=None if self.confidence is None else self.confidence.resolve(contexts),
            distribution=None if self.distribution is None else self.distribution.resolve(contexts),
        )

    def scores(self) -> Iterator[StoredScore]:
        if self.confidence is not None:
            yield self.confidence
        if self.distribution is not None:
            yield from (item.score for item in self.distribution.entries)


class StoredJointEvidence(StrictContractModel):
    class_inventory: int = Field(ge=0, description="Index into the owning joint_class_inventories array.")
    log_probabilities: tuple[float | None, ...] = Field(min_length=1)
    selected_class: int = Field(ge=0)

    def resolve(self, inventories: tuple[tuple[str, ...], ...]) -> JointRelationNuclearityEvidence:
        if self.class_inventory >= len(inventories):
            raise ValueError("joint evidence references an absent class inventory")
        return JointRelationNuclearityEvidence(
            labels=inventories[self.class_inventory], log_probabilities=self.log_probabilities,
            selected_class=self.selected_class,
        )


class StoredStructureDecision(StrictContractModel):
    decision_id: str
    node_ids: tuple[int, ...]
    primary_edge_ids: tuple[str, ...]
    analysed_start: int = Field(ge=0)
    analysed_end: int = Field(gt=0)
    selected_split: int | None = Field(ge=0)
    nuclearity: str
    relation: StoredRelationInterpretation
    confidence: StoredScore | None
    confidence_basis: Literal["joint_relation_nuclearity_given_selected_split", "unscored_deterministic_recombination"]
    split_basis: Literal["pointer", "forced_two_edu", "bottom_up_transitions", "deterministic_recombination"]
    transitions: tuple[NetworkTransitionDecision, ...]
    split_entropy: StoredScore | None
    split_distribution: StoredDistribution | None
    relation_distribution: StoredDistribution | None
    nuclearity_distribution: StoredDistribution | None
    producing_component_identity: Sha256Identity
    joint: StoredJointEvidence | None

    def resolve(
        self, inventories: tuple[tuple[str, ...], ...], contexts: tuple[ScoreContext, ...],
    ) -> PrimaryStructureDecisionEvidence:
        return PrimaryStructureDecisionEvidence(
            **self.model_dump(exclude={
                "joint", "relation", "confidence", "split_entropy", "split_distribution",
                "relation_distribution", "nuclearity_distribution",
            }),
            joint=None if self.joint is None else self.joint.resolve(inventories),
            relation=self.relation.resolve(contexts),
            confidence=None if self.confidence is None else self.confidence.resolve(contexts),
            split_entropy=None if self.split_entropy is None else self.split_entropy.resolve(contexts),
            split_distribution=None if self.split_distribution is None else self.split_distribution.resolve(contexts),
            relation_distribution=None if self.relation_distribution is None else self.relation_distribution.resolve(contexts),
            nuclearity_distribution=None if self.nuclearity_distribution is None else self.nuclearity_distribution.resolve(contexts),
        )

    def scores(self) -> Iterator[StoredScore]:
        for score in (self.relation.confidence, self.confidence, self.split_entropy):
            if score is not None:
                yield score
        for distribution in (self.split_distribution, self.relation_distribution, self.nuclearity_distribution):
            if distribution is not None:
                yield from (item.score for item in distribution.entries)


class StoredPrimaryInferenceEvidence(StrictContractModel):
    joint_class_inventories: tuple[tuple[str, ...], ...] = Field(
        description="Distinct ordered native joint-class inventories, in first-use order. Repeated labels within an inventory retain distinct class positions.",
    )
    score_contexts: tuple[ScoreContext, ...] = Field(
        description="Exact score kind, range, calibration and producer metadata, in first-use order; values remain attached to each decision.",
    )
    segmentation_decisions: tuple[StoredSegmentationDecision, ...]
    structure_decisions: tuple[StoredStructureDecision, ...]
    refinements: tuple[RefinementRecord, ...]
    relation_vocabulary: RuntimeRelationVocabulary | None = Field(default=None, exclude_if=lambda value: value is None)

    @model_validator(mode="after")
    def inventories_and_native_decisions_are_valid(self) -> Self:
        if len(set(self.joint_class_inventories)) != len(self.joint_class_inventories):
            raise ValueError("joint class inventories must not be duplicated")
        used = tuple(dict.fromkeys(
            decision.joint.class_inventory for decision in self.structure_decisions if decision.joint is not None
        ))
        if used != tuple(range(len(self.joint_class_inventories))):
            raise ValueError("joint class inventories must all be referenced in first-use order")
        if len({item.model_dump_json() for item in self.score_contexts}) != len(self.score_contexts):
            raise ValueError("score contexts must not be duplicated")
        used_contexts = tuple(dict.fromkeys(
            score.context for decision in (*self.segmentation_decisions, *self.structure_decisions) for score in decision.scores()
        ))
        if used_contexts != tuple(range(len(self.score_contexts))):
            raise ValueError("score contexts must all be referenced in first-use order")
        self.resolve()
        return self

    def resolve(self) -> PrimaryInferenceEvidence:
        return PrimaryInferenceEvidence(
            segmentation_decisions=tuple(item.resolve(self.score_contexts) for item in self.segmentation_decisions),
            structure_decisions=tuple(item.resolve(self.joint_class_inventories, self.score_contexts) for item in self.structure_decisions),
            refinements=self.refinements, relation_vocabulary=self.relation_vocabulary,
        )

    @classmethod
    def capture(cls, value: PrimaryInferenceEvidence) -> Self:
        inventories: dict[tuple[str, ...], int] = {}
        writer = _ScoreWriter()
        segmentation = tuple(StoredSegmentationDecision(
            **decision.model_dump(exclude={"confidence", "distribution"}),
            confidence=writer.capture(decision.confidence), distribution=_distribution(decision.distribution, writer),
        ) for decision in value.segmentation_decisions)
        decisions: list[StoredStructureDecision] = []
        for decision in value.structure_decisions:
            joint = decision.joint
            stored_joint = None
            if joint is not None:
                inventory = inventories.setdefault(joint.labels, len(inventories))
                stored_joint = StoredJointEvidence(
                    class_inventory=inventory, log_probabilities=joint.log_probabilities,
                    selected_class=joint.selected_class,
                )
            decisions.append(StoredStructureDecision(
                **decision.model_dump(exclude={
                    "joint", "relation", "confidence", "split_entropy", "split_distribution",
                    "relation_distribution", "nuclearity_distribution",
                }),
                joint=stored_joint,
                relation=StoredRelationInterpretation(
                    **decision.relation.model_dump(exclude={"confidence"}), confidence=writer.capture(decision.relation.confidence),
                ),
                confidence=writer.capture(decision.confidence), split_entropy=writer.capture(decision.split_entropy),
                split_distribution=_distribution(decision.split_distribution, writer),
                relation_distribution=_distribution(decision.relation_distribution, writer),
                nuclearity_distribution=_distribution(decision.nuclearity_distribution, writer),
            ))
        return cls(
            joint_class_inventories=tuple(inventories), score_contexts=tuple(writer.contexts),
            segmentation_decisions=segmentation, structure_decisions=tuple(decisions),
            refinements=value.refinements, relation_vocabulary=value.relation_vocabulary,
        )


__all__ = ["StoredJointEvidence", "StoredPrimaryInferenceEvidence", "StoredStructureDecision"]
