"""Walton's argumentation schemes: the scheme set, and what makes an instance well formed.

Walton, Reed and Macagno (*Argumentation Schemes*, 2008) catalogue the stereotypical
patterns of defeasible reasoning people actually use. A scheme is not a validity template:
it is a *presumptive* pattern, and each one comes with **critical questions** — the moves
that shift the burden back onto the arguer. An argument matching a scheme stands only
until one of its critical questions is pressed and goes unanswered.

Two things follow, and both are enforced here:

1. **An instance must fill its scheme's premise roles.** Each scheme names the specific
   roles its premises play (an expert-opinion argument needs a *source*, a *domain*, and
   an *assertion* — not just "some premises"). Filling the wrong roles, leaving one out,
   or inventing a role is a malformed instance, refused rather than repaired.
2. **The critical questions are the analysis.** Identifying the scheme is only half of it;
   what matters analytically is which critical questions the text addresses and which it
   leaves open. Open questions are recorded, never answered by this provider — answering
   them is the reader's job, and inventing an answer would be fabrication.

This module is the table and its validator only. Nothing here judges whether an argument
is good; that judgement is exactly what the critical questions hand to the reader.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Annotated, Final, Self

from pydantic import BaseModel, Field, StringConstraints, model_validator

from rdam._strict import JsonValue

type NonEmpty = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class SchemeError(ValueError):
    """The supplied structure is not a well-formed instance of its declared scheme."""


class SchemeId(StrEnum):
    """The schemes this provider recognises, by Walton's names."""

    EXPERT_OPINION = "expert_opinion"
    POSITION_TO_KNOW = "position_to_know"
    POPULAR_OPINION = "popular_opinion"
    ANALOGY = "analogy"
    EXAMPLE = "example"
    SIGN = "sign"
    CAUSE_TO_EFFECT = "cause_to_effect"
    CONSEQUENCES = "consequences"
    PRACTICAL_REASONING = "practical_reasoning"
    VERBAL_CLASSIFICATION = "verbal_classification"
    SLIPPERY_SLOPE = "slippery_slope"
    AD_HOMINEM = "ad_hominem"


class CriticalQuestionStatus(StrEnum):
    """What the source does with a critical question — never what the answer is."""

    ADDRESSED = "addressed"
    """The passage itself takes up the question."""

    OPEN = "open"
    """The passage leaves it unaddressed. This is a finding, not a defect."""


@dataclass(frozen=True, slots=True)
class Scheme:
    """One scheme: the roles its premises play, and the questions that test it."""

    scheme_id: SchemeId
    name: str
    premise_roles: tuple[str, ...]
    critical_questions: tuple[str, ...]


def _scheme(
    scheme_id: SchemeId, name: str, roles: tuple[str, ...], questions: tuple[str, ...]
) -> tuple[SchemeId, Scheme]:
    return scheme_id, Scheme(scheme_id=scheme_id, name=name, premise_roles=roles, critical_questions=questions)


SCHEMES: Final[Mapping[SchemeId, Scheme]] = dict(
    (
        _scheme(
            SchemeId.EXPERT_OPINION,
            "Argument from Expert Opinion",
            ("source", "domain", "assertion"),
            (
                "How credible is the source as an expert?",
                "Is the source an expert in the domain the assertion falls under?",
                "What did the source actually assert?",
                "Is the source personally reliable as a source?",
                "Is the assertion consistent with what other experts say?",
                "Is the assertion based on evidence?",
            ),
        ),
        _scheme(
            SchemeId.POSITION_TO_KNOW,
            "Argument from Position to Know",
            ("source", "situation", "assertion"),
            (
                "Is the source in a position to know about the situation?",
                "Is the source honest and reliable?",
                "Did the source actually assert this?",
            ),
        ),
        _scheme(
            SchemeId.POPULAR_OPINION,
            "Argument from Popular Opinion",
            ("proposition", "acceptance"),
            (
                "What evidence is there that the proposition really is generally accepted?",
                "Does general acceptance give any reason to think it true?",
                "Is there other evidence that counts against it?",
            ),
        ),
        _scheme(
            SchemeId.ANALOGY,
            "Argument from Analogy",
            ("source_case", "target_case", "similarity", "conclusion_property"),
            (
                "Are the two cases similar in the respect claimed?",
                "Is the property in the source case true as stated?",
                "Are there relevant differences that defeat the analogy?",
                "Is there a third case more similar to the target that points the other way?",
            ),
        ),
        _scheme(
            SchemeId.EXAMPLE,
            "Argument from Example",
            ("example", "generalisation"),
            (
                "Is the example actually true?",
                "Does the example genuinely instance the generalisation?",
                "Is the example typical, or is it special in some way?",
                "How strong is the generalisation given how many examples support it?",
                "Are there counter-examples?",
            ),
        ),
        _scheme(
            SchemeId.SIGN,
            "Argument from Sign",
            ("finding", "indicated"),
            (
                "How strongly does the finding indicate what is claimed?",
                "Could the finding indicate something else instead?",
            ),
        ),
        _scheme(
            SchemeId.CAUSE_TO_EFFECT,
            "Argument from Cause to Effect",
            ("cause", "effect", "causal_generalisation"),
            (
                "How strong is the causal generalisation?",
                "Is the evidence for the causal relation strong enough?",
                "Are there other causal factors that could interfere?",
                "Could the correlation be coincidence, or the causation run the other way?",
            ),
        ),
        _scheme(
            SchemeId.CONSEQUENCES,
            "Argument from Consequences",
            ("action", "consequence", "valence"),
            (
                "How likely is the consequence if the action is taken?",
                "What evidence supports that this consequence would follow?",
                "Are there opposite consequences that should be weighed against it?",
            ),
        ),
        _scheme(
            SchemeId.PRACTICAL_REASONING,
            "Practical Reasoning",
            ("goal", "means", "conclusion_action"),
            (
                "Are there alternative means to the same goal?",
                "Is this means the most efficient one?",
                "Is the goal itself acceptable?",
                "Are there conflicting goals that should take priority?",
                "Does the means have side effects that outweigh the goal?",
            ),
        ),
        _scheme(
            SchemeId.VERBAL_CLASSIFICATION,
            "Argument from Verbal Classification",
            ("individual", "property", "classification"),
            (
                "Does the individual really have the property?",
                "Does having the property really place it in the class as defined?",
                "Is the classification vague or contestable in this case?",
            ),
        ),
        _scheme(
            SchemeId.SLIPPERY_SLOPE,
            "Slippery Slope Argument",
            ("first_step", "sequence", "outcome"),
            (
                "What are the intervening steps, and is each one plausible?",
                "What keeps the sequence from being stopped part-way?",
                "How likely is the final outcome given the first step?",
            ),
        ),
        _scheme(
            SchemeId.AD_HOMINEM,
            "Argument Against the Person",
            ("person", "attack", "claim_attacked"),
            (
                "Is the attack on the person relevant to the claim at all?",
                "Is what is alleged about the person actually true?",
                "Even if true, does it bear on the truth of the claim?",
            ),
        ),
    )
)
"""Every recognised scheme with its premise roles and Walton's critical questions."""


class CriticalQuestion(BaseModel):
    """One critical question and what the source does with it."""

    model_config = {"extra": "forbid"}

    index: int = Field(ge=0, description="Zero-based index into the scheme's critical questions.")
    status: CriticalQuestionStatus = Field(description="Whether the passage addresses this question or leaves it open.")
    note: NonEmpty | None = Field(
        default=None,
        description="How the passage addresses it, quoting the passage. Required when status is 'addressed'.",
    )

    @model_validator(mode="after")
    def addressed_questions_say_how(self) -> Self:
        if self.status is CriticalQuestionStatus.ADDRESSED and not self.note:
            raise SchemeError("a critical question marked addressed must say how the passage addresses it")
        return self


class SchemeInstance(BaseModel):
    """One argument in the passage, matched to a scheme and tested against its questions."""

    model_config = {"extra": "forbid"}

    scheme_id: SchemeId = Field(description="Which scheme this argument instances.")
    conclusion: NonEmpty = Field(description="The conclusion the argument presses.")
    premises: dict[str, NonEmpty] = Field(
        description=(
            "The scheme's premise roles, filled from the passage. Every role the scheme names must be present, "
            "and no other key may appear."
        )
    )
    critical_questions: list[CriticalQuestion] = Field(
        default_factory=list,
        description="The scheme's critical questions, each marked addressed or open by the passage.",
    )

    @model_validator(mode="after")
    def instance_matches_its_scheme(self) -> Self:
        scheme = SCHEMES[self.scheme_id]
        required = set(scheme.premise_roles)
        supplied = set(self.premises)
        if missing := sorted(required - supplied):
            raise SchemeError(f"{self.scheme_id.value} requires premise roles {missing}; they are missing")
        if unknown := sorted(supplied - required):
            raise SchemeError(f"{self.scheme_id.value} has no premise roles {unknown}; permitted roles are {sorted(required)}")
        seen: set[int] = set()
        for question in self.critical_questions:
            if question.index >= len(scheme.critical_questions):
                raise SchemeError(
                    f"{self.scheme_id.value} has {len(scheme.critical_questions)} critical questions; index {question.index} does not exist"
                )
            if question.index in seen:
                raise SchemeError(f"critical question {question.index} is reported twice")
            seen.add(question.index)
        return self

    @property
    def scheme(self) -> Scheme:
        return SCHEMES[self.scheme_id]

    @property
    def open_questions(self) -> tuple[str, ...]:
        """The critical questions this passage leaves unanswered — the analytical payload."""

        reported = {item.index: item.status for item in self.critical_questions}
        return tuple(
            text
            for index, text in enumerate(self.scheme.critical_questions)
            if reported.get(index, CriticalQuestionStatus.OPEN) is CriticalQuestionStatus.OPEN
        )

    def to_payload(self) -> dict[str, JsonValue]:
        return {
            "scheme_id": self.scheme_id.value,
            "scheme_name": self.scheme.name,
            "conclusion": self.conclusion,
            "premises": dict(self.premises),
            "critical_questions": [
                {
                    "index": item.index,
                    "question": self.scheme.critical_questions[item.index],
                    "status": item.status.value,
                    "note": item.note,
                }
                for item in self.critical_questions
            ],
            "open_questions": list(self.open_questions),
            "open_question_count": len(self.open_questions),
        }


class WaltonAnalysis(BaseModel):
    """Every scheme instance found in one source."""

    model_config = {"extra": "forbid"}

    instances: list[SchemeInstance] = Field(
        default_factory=list,
        description=(
            "One entry per argument in the passage that instances a recognised scheme. A passage that argues "
            "nothing, or argues in no recognised pattern, yields an empty list — never force a scheme onto it."
        ),
    )

    def to_payload(self) -> dict[str, JsonValue]:
        return {
            "instances": [instance.to_payload() for instance in self.instances],
            "instance_count": len(self.instances),
            "total_open_questions": sum(len(instance.open_questions) for instance in self.instances),
            "scheme_set": "walton-reed-macagno-2008-subset-v1",
        }


__all__ = [
    "SCHEMES",
    "CriticalQuestion",
    "CriticalQuestionStatus",
    "NonEmpty",
    "Scheme",
    "SchemeError",
    "SchemeId",
    "SchemeInstance",
    "WaltonAnalysis",
]
