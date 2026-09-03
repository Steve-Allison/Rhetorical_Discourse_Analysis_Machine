"""Native Penn Discourse Treebank 3.0 relation contracts."""

from enum import StrEnum
from typing import Annotated, Final, Self

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StringConstraints, model_validator

from rdam._strict import JsonValue

def _untrimmed_non_blank(value: str) -> str:
    if not value.strip():
        raise ValueError("value must not be blank")
    if value != value.strip():
        raise ValueError("value must not have surrounding whitespace")
    return value


type ExactText = Annotated[str, StringConstraints(min_length=1)]
type NonEmpty = Annotated[
    str,
    StringConstraints(min_length=1),
    AfterValidator(_untrimmed_non_blank),
]
type RelationId = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9_]*$")]


class RelationError(ValueError):
    """A proposed relation is not a valid native PDTB-3 annotation."""


class RelationType(StrEnum):
    EXPLICIT = "Explicit"
    IMPLICIT = "Implicit"
    ALTLEX = "AltLex"
    ALTLEXC = "AltLexC"
    ENTREL = "EntRel"
    HYPOPHORA = "Hypophora"
    NOREL = "NoRel"


class PdtbSense(StrEnum):
    TEMPORAL_SYNCHRONOUS = "Temporal.Synchronous"
    TEMPORAL_ASYNCHRONOUS_PRECEDENCE = "Temporal.Asynchronous.Precedence"
    TEMPORAL_ASYNCHRONOUS_SUCCESSION = "Temporal.Asynchronous.Succession"
    CONTINGENCY_CAUSE_REASON = "Contingency.Cause.Reason"
    CONTINGENCY_CAUSE_RESULT = "Contingency.Cause.Result"
    CONTINGENCY_CAUSE_NEG_RESULT = "Contingency.Cause.NegResult"
    CONTINGENCY_CAUSE_BELIEF_REASON = "Contingency.Cause+Belief.Reason+Belief"
    CONTINGENCY_CAUSE_BELIEF_RESULT = "Contingency.Cause+Belief.Result+Belief"
    CONTINGENCY_CAUSE_SPEECH_ACT_REASON = "Contingency.Cause+SpeechAct.Reason+SpeechAct"
    CONTINGENCY_CAUSE_SPEECH_ACT_RESULT = "Contingency.Cause+SpeechAct.Result+SpeechAct"
    CONTINGENCY_CONDITION_ARG1 = "Contingency.Condition.Arg1-as-cond"
    CONTINGENCY_CONDITION_ARG2 = "Contingency.Condition.Arg2-as-cond"
    CONTINGENCY_CONDITION_SPEECH_ACT = "Contingency.Condition+SpeechAct"
    CONTINGENCY_NEGATIVE_CONDITION_ARG1 = "Contingency.Negative-condition.Arg1-as-negCond"
    CONTINGENCY_NEGATIVE_CONDITION_ARG2 = "Contingency.Negative-condition.Arg2-as-negCond"
    CONTINGENCY_NEGATIVE_CONDITION_SPEECH_ACT = "Contingency.Negative-condition+SpeechAct"
    CONTINGENCY_PURPOSE_ARG1 = "Contingency.Purpose.Arg1-as-goal"
    CONTINGENCY_PURPOSE_ARG2 = "Contingency.Purpose.Arg2-as-goal"
    COMPARISON_CONCESSION_ARG1 = "Comparison.Concession.Arg1-as-denier"
    COMPARISON_CONCESSION_ARG2 = "Comparison.Concession.Arg2-as-denier"
    COMPARISON_CONCESSION_SPEECH_ACT_ARG2 = (
        "Comparison.Concession+SpeechAct.Arg2-as-denier+SpeechAct"
    )
    COMPARISON_CONTRAST = "Comparison.Contrast"
    COMPARISON_SIMILARITY = "Comparison.Similarity"
    EXPANSION_CONJUNCTION = "Expansion.Conjunction"
    EXPANSION_DISJUNCTION = "Expansion.Disjunction"
    EXPANSION_EQUIVALENCE = "Expansion.Equivalence"
    EXPANSION_EXCEPTION_ARG1 = "Expansion.Exception.Arg1-as-excpt"
    EXPANSION_EXCEPTION_ARG2 = "Expansion.Exception.Arg2-as-excpt"
    EXPANSION_INSTANTIATION_ARG1 = "Expansion.Instantiation.Arg1-as-instance"
    EXPANSION_INSTANTIATION_ARG2 = "Expansion.Instantiation.Arg2-as-instance"
    EXPANSION_LEVEL_OF_DETAIL_ARG1 = "Expansion.Level-of-detail.Arg1-as-detail"
    EXPANSION_LEVEL_OF_DETAIL_ARG2 = "Expansion.Level-of-detail.Arg2-as-detail"
    EXPANSION_MANNER_ARG1 = "Expansion.Manner.Arg1-as-manner"
    EXPANSION_MANNER_ARG2 = "Expansion.Manner.Arg2-as-manner"
    EXPANSION_SUBSTITUTION_ARG1 = "Expansion.Substitution.Arg1-as-subst"
    EXPANSION_SUBSTITUTION_ARG2 = "Expansion.Substitution.Arg2-as-subst"


PDTB3_SENSES: Final = tuple(item.value for item in PdtbSense)


class _ClosedModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class TextSpan(_ClosedModel):
    """One exact, half-open source span."""

    start: int = Field(strict=True, ge=0)
    end: int = Field(strict=True, gt=0)
    text: ExactText

    @model_validator(mode="after")
    def positive_span(self) -> Self:
        if self.end <= self.start:
            raise RelationError("span end must be greater than start")
        return self

    def overlaps(self, other: Self) -> bool:
        return self.start < other.end and other.start < self.end

    def to_payload(self) -> dict[str, JsonValue]:
        return {"start": self.start, "end": self.end, "text": self.text}


class PdtbArgument(_ClosedModel):
    """One PDTB argument, including discontinuous ordered spans."""

    spans: tuple[TextSpan, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def ordered_non_overlapping_spans(self) -> Self:
        for previous, current in zip(self.spans, self.spans[1:], strict=False):
            if current.start < previous.end:
                raise RelationError("argument spans must be ordered and non-overlapping")
        return self

    def to_payload(self) -> dict[str, JsonValue]:
        return {"spans": [item.to_payload() for item in self.spans]}


class PdtbRelation(_ClosedModel):
    """One type-safe PDTB-3 binary relation."""

    relation_id: RelationId
    relation_type: RelationType
    arg1: PdtbArgument
    arg2: PdtbArgument
    senses: tuple[PdtbSense, ...] = ()
    connective_spans: tuple[TextSpan, ...] = ()
    inferred_connectives: tuple[NonEmpty, ...] = ()
    alternative_lexicalization_spans: tuple[TextSpan, ...] = ()

    @model_validator(mode="after")
    def type_specific_contract(self) -> Self:
        if any(left.overlaps(right) for left in self.arg1.spans for right in self.arg2.spans):
            raise RelationError("argument spans overlap")
        if len(self.senses) != len(set(self.senses)):
            raise RelationError("relation senses must be unique")
        sense_bearing = {
            RelationType.EXPLICIT,
            RelationType.IMPLICIT,
            RelationType.ALTLEX,
            RelationType.ALTLEXC,
        }
        if self.relation_type in sense_bearing and not self.senses:
            raise RelationError(f"{self.relation_type.value} requires at least one PDTB-3 sense")
        if self.relation_type not in sense_bearing and self.senses:
            raise RelationError(f"{self.relation_type.value} must not carry senses")

        if self.relation_type is RelationType.EXPLICIT:
            if not self.connective_spans:
                raise RelationError("Explicit requires explicit connective source evidence")
            if self.inferred_connectives or self.alternative_lexicalization_spans:
                raise RelationError("Explicit may carry only explicit connective evidence")
        elif self.relation_type is RelationType.IMPLICIT:
            if not self.inferred_connectives:
                raise RelationError("Implicit requires at least one inferred connective")
            if self.connective_spans or self.alternative_lexicalization_spans:
                raise RelationError("Implicit may carry only inferred connective evidence")
        elif self.relation_type in {RelationType.ALTLEX, RelationType.ALTLEXC}:
            if not self.alternative_lexicalization_spans:
                raise RelationError(f"{self.relation_type.value} requires alternative lexicalization evidence")
            if self.connective_spans or self.inferred_connectives:
                raise RelationError(f"{self.relation_type.value} may carry only alternative lexicalization evidence")
        elif self.connective_spans or self.inferred_connectives or self.alternative_lexicalization_spans:
            raise RelationError(f"{self.relation_type.value} must not carry connective evidence")
        return self

    def quoted_spans(self) -> tuple[TextSpan, ...]:
        return tuple(
            [
                *self.arg1.spans,
                *self.arg2.spans,
                *self.connective_spans,
                *self.alternative_lexicalization_spans,
            ]
        )

    def to_payload(self) -> dict[str, JsonValue]:
        return {
            "relation_id": self.relation_id,
            "relation_type": self.relation_type.value,
            "arg1": self.arg1.to_payload(),
            "arg2": self.arg2.to_payload(),
            "senses": [sense.value for sense in self.senses],
            "connective_spans": [item.to_payload() for item in self.connective_spans],
            "inferred_connectives": list(self.inferred_connectives),
            "alternative_lexicalization_spans": [
                item.to_payload() for item in self.alternative_lexicalization_spans
            ],
        }


class PdtbAnalysis(_ClosedModel):
    """Every PDTB-3 relation found in one source."""

    relations: tuple[PdtbRelation, ...] = ()

    @model_validator(mode="after")
    def unique_relation_ids(self) -> Self:
        ids = [relation.relation_id for relation in self.relations]
        if len(ids) != len(set(ids)):
            raise RelationError("relation ids must be unique")
        return self

    def validate_source(self, source: str) -> Self:
        for relation in self.relations:
            for item in relation.quoted_spans():
                if item.end > len(source) or source[item.start : item.end] != item.text:
                    raise RelationError(
                        f"span {item.start}:{item.end} in relation {relation.relation_id!r} does not equal source slice"
                    )
        return self

    def to_payload(self) -> dict[str, JsonValue]:
        counts = {relation_type.value: 0 for relation_type in RelationType}
        for relation in self.relations:
            counts[relation.relation_type.value] += 1
        return {
            "relations": [relation.to_payload() for relation in self.relations],
            "relation_count": len(self.relations),
            "relation_type_counts": counts,
        }


__all__ = [
    "PDTB3_SENSES",
    "PdtbAnalysis",
    "PdtbArgument",
    "PdtbRelation",
    "PdtbSense",
    "RelationError",
    "RelationType",
    "TextSpan",
]
