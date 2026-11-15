"""Persisted Speech Act & Hamblin Commitment Store output shape."""

from typing import Self

from pydantic import NonNegativeInt, model_validator

from rdam._native_output import ExtractionRecord
from rdam._strict import StrictModel
from rdam.ingest.contracts.evidence import SourceEvidenceSpan
from rdam.speech_acts.acts import (
    ALLOWED_FUNCTIONS_BY_SEARLE,
    CommitmentOperation,
    IsoCommunicativeFunction,
    NonEmpty,
    SearleClass,
)


class SpeechActOutputItem(StrictModel):
    act_id: NonEmpty
    speaker: NonEmpty
    searle_class: SearleClass
    iso_communicative_function: IsoCommunicativeFunction
    propositional_content: NonEmpty
    commitment_operation: CommitmentOperation
    target_proposition: NonEmpty | None = None
    span: SourceEvidenceSpan

    @model_validator(mode="after")
    def check_function_compatibility(self) -> Self:
        if self.iso_communicative_function not in ALLOWED_FUNCTIONS_BY_SEARLE[self.searle_class]:
            raise ValueError("Incompatible Searle class and ISO 24617-2 communicative function")
        return self


class SpeakerCommitmentOutput(StrictModel):
    speaker: NonEmpty
    active_commitments: tuple[NonEmpty, ...]
    retracted_commitments: tuple[NonEmpty, ...]
    challenges_raised: tuple[NonEmpty, ...]


class CommitmentConflictOutput(StrictModel):
    speaker: NonEmpty
    earlier_act_id: NonEmpty
    later_act_id: NonEmpty
    earlier_proposition: NonEmpty
    later_proposition: NonEmpty


class SpeechActsOutput(StrictModel):
    acts: tuple[SpeechActOutputItem, ...]
    act_count: NonNegativeInt
    commitment_store: tuple[SpeakerCommitmentOutput, ...]
    conflicts: tuple[CommitmentConflictOutput, ...]
    extraction: ExtractionRecord

    @model_validator(mode="after")
    def verify_counts(self) -> Self:
        if self.act_count != len(self.acts):
            raise ValueError("SpeechActsOutput act_count must match len(acts)")
        return self
