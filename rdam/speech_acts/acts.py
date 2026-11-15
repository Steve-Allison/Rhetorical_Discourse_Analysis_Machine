"""Searle (1969/1976) & ISO 24617-2 speech-act structures with deterministic grounding."""

from typing import Annotated, Final, Literal, Self

from pydantic import Field, StringConstraints, model_validator

from rdam._grounding import GroundingCollector, QuoteRef
from rdam._strict import StrictModel
from rdam.ingest.contracts.evidence import SourceEvidenceSpan

type NonEmpty = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]

type SearleClass = Literal[
    "assertive",
    "directive",
    "commissive",
    "expressive",
    "declaration",
]

type IsoCommunicativeFunction = Literal[
    "inform",
    "agreement",
    "disagreement",
    "correction",
    "answer",
    "confirm",
    "disconfirm",
    "question",
    "request",
    "instruct",
    "suggest",
    "promise",
    "offer",
    "threat",
    "apology",
    "thank",
    "congratulate",
    "declare",
]

type CommitmentOperation = Literal[
    "assert",
    "concede",
    "retract",
    "challenge",
    "none",
]

ALLOWED_FUNCTIONS_BY_SEARLE: Final[dict[SearleClass, frozenset[IsoCommunicativeFunction]]] = {
    "assertive": frozenset(
        {"inform", "agreement", "disagreement", "correction", "answer", "confirm", "disconfirm"}
    ),
    "directive": frozenset({"question", "request", "instruct", "suggest"}),
    "commissive": frozenset({"promise", "offer", "threat"}),
    "expressive": frozenset({"apology", "thank", "congratulate"}),
    "declaration": frozenset({"declare"}),
}


class SpeechActError(ValueError):
    """Raised when a speech-act proposal violates Searle/ISO 24617-2 or source invariants."""


class SpeechActItemProposal(StrictModel):
    act_id: NonEmpty
    speaker: NonEmpty = Field(default="author")
    searle_class: SearleClass
    iso_communicative_function: IsoCommunicativeFunction
    propositional_content: NonEmpty
    commitment_operation: CommitmentOperation
    target_proposition: NonEmpty | None = None
    evidence: QuoteRef

    @model_validator(mode="after")
    def validate_act_taxonomy(self) -> Self:
        allowed = ALLOWED_FUNCTIONS_BY_SEARLE[self.searle_class]
        if self.iso_communicative_function not in allowed:
            raise ValueError(
                f"Speech act {self.act_id!r}: iso_communicative_function "
                f"{self.iso_communicative_function!r} is incompatible with searle_class "
                f"{self.searle_class!r} (expected one of {sorted(allowed)})."
            )
        needs_target = self.commitment_operation in {"retract", "challenge"}
        if needs_target and self.target_proposition is None:
            raise ValueError(
                f"Speech act {self.act_id!r}: commitment_operation={self.commitment_operation!r} "
                "requires target_proposition."
            )
        if not needs_target and self.target_proposition is not None:
            raise ValueError(
                f"Speech act {self.act_id!r}: target_proposition must be null when "
                f"commitment_operation={self.commitment_operation!r}."
            )
        return self


class SpeechActProposal(StrictModel):
    acts: list[SpeechActItemProposal] = Field(default_factory=list[SpeechActItemProposal])

    @model_validator(mode="after")
    def unique_act_ids(self) -> Self:
        seen: set[str] = set()
        for act in self.acts:
            if act.act_id in seen:
                raise ValueError(f"Duplicate speech-act act_id: {act.act_id!r}")
            seen.add(act.act_id)
        return self

    def validate_source(self, source_text: str) -> dict[str, SourceEvidenceSpan]:
        collector = GroundingCollector(source_text)
        resolved: dict[str, SourceEvidenceSpan] = {}
        for idx, act in enumerate(self.acts):
            span = collector.resolve(act.evidence, field_name=f"acts[{idx}] ({act.act_id}).evidence")
            if span is not None:
                resolved[act.act_id] = span
        try:
            collector.raise_if_errors()
        except ValueError as exc:
            raise SpeechActError(str(exc)) from exc
        return resolved


__all__ = [
    "ALLOWED_FUNCTIONS_BY_SEARLE",
    "CommitmentOperation",
    "IsoCommunicativeFunction",
    "SearleClass",
    "SpeechActError",
    "SpeechActItemProposal",
    "SpeechActProposal",
]
