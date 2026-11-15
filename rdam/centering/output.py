"""Persisted Centering Theory and Entity Grid output contract."""

from typing import Self

from pydantic import Field, NonNegativeInt, model_validator

from rdam._strict import StrictModel
from rdam.centering.grid import CenteringTransition, GrammaticalRole
from rdam.ingest.contracts.evidence import SourceEvidenceSpan


class EntityMentionOutput(StrictModel):
    utterance_id: str = Field(min_length=1)
    role: GrammaticalRole
    span: SourceEvidenceSpan
    is_pronoun: bool


class DiscourseEntityOutput(StrictModel):
    entity_id: str = Field(min_length=1)
    canonical_name: str = Field(min_length=1)
    is_plural: bool
    mentions: tuple[EntityMentionOutput, ...] = Field(min_length=1)


class UtteranceCenteringOutput(StrictModel):
    utterance_id: str = Field(min_length=1)
    sentence_index: NonNegativeInt
    span: SourceEvidenceSpan
    speaker: str | None = None
    cf_ranking: tuple[str, ...]
    cp: str | None = None
    cb: str | None = None
    transition: CenteringTransition

    @model_validator(mode="after")
    def validate_centers(self) -> Self:
        if self.cf_ranking:
            if self.cp != self.cf_ranking[0]:
                raise ValueError("preferred center cp must equal cf_ranking[0]")
        elif self.cp is not None:
            raise ValueError("empty cf_ranking cannot have a preferred center cp")
        if self.cb is not None and self.cb not in self.cf_ranking:
            raise ValueError("backward-looking center cb must belong to cf_ranking")
        return self


class EntityGridRowOutput(StrictModel):
    entity_id: str = Field(min_length=1)
    roles: tuple[GrammaticalRole, ...]


class TransitionCountsOutput(StrictModel):
    establishment: NonNegativeInt
    continue_count: NonNegativeInt
    retain: NonNegativeInt
    smooth_shift: NonNegativeInt
    rough_shift: NonNegativeInt
    zero_cb: NonNegativeInt


class CenteringOutput(StrictModel):
    entities: tuple[DiscourseEntityOutput, ...]
    utterances: tuple[UtteranceCenteringOutput, ...]
    entity_grid: tuple[EntityGridRowOutput, ...]
    transition_counts: TransitionCountsOutput
    local_coherence_score: float = Field(ge=0.0, le=1.0)
    entity_count: NonNegativeInt
    utterance_count: NonNegativeInt

    @model_validator(mode="after")
    def validate_consistency(self) -> Self:
        if self.entity_count != len(self.entities) or self.utterance_count != len(self.utterances):
            raise ValueError("Centering counts must match entities and utterances")
        known_entities = {ent.entity_id for ent in self.entities}
        if len(known_entities) != len(self.entities):
            raise ValueError("Entity IDs must be unique")
        if len(self.entity_grid) != len(self.entities):
            raise ValueError("entity_grid must contain one row per entity")
        for row in self.entity_grid:
            if row.entity_id not in known_entities:
                raise ValueError(f"Unknown entity_id in entity_grid: {row.entity_id}")
            if len(row.roles) != len(self.utterances):
                raise ValueError("Each entity_grid row must match utterance_count")
        return self
