"""Persisted Walton output shape, including catalogue questions and state totals."""

from typing import Literal, Self
from pydantic import Field, model_validator
from rdam._native_output import ExtractionRecord
from rdam._strict import StrictModel
from rdam.ingest.contracts.evidence import SourceEvidenceSpan
from rdam.walton.schemes import CriticalQuestionStatus, NonEmpty, SchemeId, SchemeInstance, SCHEME_SET_ID


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

    @model_validator(mode="after")
    def instance_and_derived_fields_reproduce(self) -> Self:
        instance = SchemeInstance.model_validate({
            "scheme_id": self.scheme_id,
            "conclusion": self.conclusion,
            "premises": self.premises,
            "critical_questions": [question.model_dump(exclude={"question"}) for question in self.critical_questions],
        })
        if self.model_dump(mode="json") != instance.to_payload():
            raise ValueError("Walton instance must reproduce its catalogue and derived fields")
        return self


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

    @model_validator(mode="after")
    def totals_reproduce(self) -> Self:
        if self.scheme_set != SCHEME_SET_ID:
            raise ValueError("Walton output names an unsupported scheme set")
        if self.instance_count != len(self.instances) or self.total_open_questions != self.open_question_count:
            raise ValueError("Walton totals must reproduce the stored instances")
        for name in ("question_count", "addressed_count", "open_question_count", "not_assessable_count"):
            if getattr(self, name) != sum(getattr(instance, name) for instance in self.instances):
                raise ValueError("Walton totals must reproduce the stored instances")
        return self


class HistoricalWaltonOutput(StrictModel):
    instances: tuple[HistoricalInstanceOutput, ...]
    instance_count: int = Field(ge=0)
    total_open_questions: int = Field(ge=0)
    scheme_set: str
    extraction: ExtractionRecord
