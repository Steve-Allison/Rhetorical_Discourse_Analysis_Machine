"""Persisted Walton output shape, including catalogue questions and state totals."""

from typing import Literal
from pydantic import Field
from rdam._native_output import ExtractionRecord
from rdam._strict import StrictModel
from rdam.ingest.contracts.evidence import SourceEvidenceSpan
from rdam.walton.schemes import CriticalQuestionStatus, NonEmpty, SchemeId


class HistoricalQuestionOutput(StrictModel):
    index: int = Field(ge=0)
    question: NonEmpty
    status: Literal["addressed", "open"]
    note: NonEmpty | None


class QuestionOutput(StrictModel):
    index: int = Field(ge=0)
    question: NonEmpty
    status: CriticalQuestionStatus
    note: NonEmpty | None
    evidence: tuple[SourceEvidenceSpan, ...]
    reason: Literal["insufficient_context", "ambiguous_source"] | None


class HistoricalInstanceOutput(StrictModel):
    scheme_id: SchemeId
    scheme_name: NonEmpty
    conclusion: NonEmpty
    premises: dict[str, NonEmpty]
    critical_questions: tuple[HistoricalQuestionOutput, ...]
    open_questions: tuple[NonEmpty, ...]
    open_question_count: int = Field(ge=0)


class InstanceOutput(StrictModel):
    scheme_id: SchemeId
    scheme_name: NonEmpty
    conclusion: NonEmpty
    premises: dict[str, NonEmpty]
    critical_questions: tuple[QuestionOutput, ...]
    open_questions: tuple[NonEmpty, ...]
    open_question_count: int = Field(ge=0)
    question_count: int = Field(ge=0)
    addressed_count: int = Field(ge=0)
    not_assessable_count: int = Field(ge=0)


class WaltonOutput(StrictModel):
    instances: tuple[InstanceOutput, ...]
    instance_count: int = Field(ge=0)
    total_open_questions: int = Field(ge=0)
    question_count: int = Field(ge=0)
    addressed_count: int = Field(ge=0)
    open_question_count: int = Field(ge=0)
    not_assessable_count: int = Field(ge=0)
    scheme_set: str
    extraction: ExtractionRecord


class HistoricalWaltonOutput(StrictModel):
    instances: tuple[HistoricalInstanceOutput, ...]
    instance_count: int = Field(ge=0)
    total_open_questions: int = Field(ge=0)
    scheme_set: str
    extraction: ExtractionRecord
