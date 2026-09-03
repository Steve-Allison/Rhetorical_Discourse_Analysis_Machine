"""Toulmin's layout of argument: the six elements and what makes a layout complete.

Stephen Toulmin (*The Uses of Argument*, 1958) analysed practical argument into six
functional elements. Three are structural and always present in an argument worth the
name:

| element | Toulmin's question | role |
|---|---|---|
| **claim** | "What are you saying?" | the assertion to be established |
| **grounds** (data) | "What have you got to go on?" | the facts offered for it |
| **warrant** | "How do you get there?" | the general licence from grounds to claim |

Three are optional and qualify the step rather than constitute it:

| element | Toulmin's question | role |
|---|---|---|
| **backing** | "Why is the warrant good?" | what stands behind the warrant |
| **qualifier** | "How sure are you?" | the force of the claim (*presumably*, *necessarily*) |
| **rebuttal** | "When would it not hold?" | the conditions that defeat the step |

**The warrant is not optional (006 FR-019).** Claim-and-premise extraction is not a
Toulmin analysis: the warrant is the whole point of the layout — it is what distinguishes
Toulmin from a bare premise-conclusion pair, and what makes backing and rebuttal
meaningful. A layout offering only a claim and its grounds is refused here as
:class:`IncompleteLayoutError` rather than returned as a Toulmin result.

Backing backs the warrant, never the claim directly; a rebuttal states a defeating
condition on the step. Both are recorded against the element they qualify so the layout
stays a layout and not a bag of sentences.
"""

from typing import Annotated, Self

from pydantic import BaseModel, Field, StringConstraints, model_validator

from rdam._strict import JsonValue

type NonEmpty = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class LayoutError(ValueError):
    """The supplied structure is not a Toulmin layout."""


class IncompleteLayoutError(LayoutError):
    """Claim and grounds without a warrant — a premise-conclusion pair, not a layout (FR-019)."""


class Rebuttal(BaseModel):
    """A condition under which the warrant would not license the claim."""

    model_config = {"extra": "forbid"}

    condition: NonEmpty = Field(description="The circumstance in which the step from grounds to claim fails.")
    source_text: NonEmpty | None = Field(default=None, description="The span of the source stating it, if it is stated.")


class ToulminLayout(BaseModel):
    """One complete Toulmin layout: the core triad, plus whatever qualifies it.

    This is also the extraction contract handed to the model, so the field descriptions
    are the instructions the model is validated against.
    """

    model_config = {"extra": "forbid"}

    claim: NonEmpty = Field(description="The assertion the arguer wants accepted.")
    grounds: list[NonEmpty] = Field(
        min_length=1,
        description="The facts, evidence, or data offered in support of the claim. At least one.",
    )
    warrant: NonEmpty = Field(
        description=(
            "The general principle or inference licence that authorises moving from these grounds to this claim. "
            "Usually implicit in the text; state it as the arguer would have to accept it. Never restate the claim "
            "or the grounds here — if there is genuinely no licence connecting them, this is not an argument."
        )
    )
    backing: list[NonEmpty] = Field(
        default_factory=list,
        description="What stands behind the warrant and makes it credible. Backs the warrant, not the claim.",
    )
    qualifier: NonEmpty | None = Field(
        default=None,
        description="The force attached to the claim, such as 'presumably', 'in most cases', 'necessarily'.",
    )
    rebuttals: list[Rebuttal] = Field(
        default_factory=list,
        description="Conditions under which the warrant would not license the claim.",
    )

    @model_validator(mode="after")
    def a_layout_is_not_a_premise_conclusion_pair(self) -> Self:
        """FR-019: the warrant is what makes this Toulmin; a bare claim and grounds is not."""

        if self.warrant.strip().casefold() == self.claim.strip().casefold():
            raise IncompleteLayoutError("the warrant restates the claim; no inference licence was identified")
        if any(self.warrant.strip().casefold() == ground.strip().casefold() for ground in self.grounds):
            raise IncompleteLayoutError("the warrant restates a ground; no inference licence was identified")
        if self.backing and not self.warrant:
            raise LayoutError("backing supports a warrant; there is no warrant to back")
        return self

    @property
    def elements_present(self) -> tuple[str, ...]:
        """Which of the six elements this layout actually carries, in Toulmin's order."""

        present = ["claim", "grounds", "warrant"]
        if self.backing:
            present.append("backing")
        if self.qualifier is not None:
            present.append("qualifier")
        if self.rebuttals:
            present.append("rebuttal")
        return tuple(present)

    @property
    def is_qualified(self) -> bool:
        """A qualified layout states the force of its claim or the conditions that defeat it."""

        return self.qualifier is not None or bool(self.rebuttals)

    def to_payload(self) -> dict[str, JsonValue]:
        return {
            "claim": self.claim,
            "grounds": list(self.grounds),
            "warrant": self.warrant,
            "backing": list(self.backing),
            "qualifier": self.qualifier,
            "rebuttals": [
                {"condition": item.condition, "source_text": item.source_text} for item in self.rebuttals
            ],
            "elements_present": list(self.elements_present),
            "is_qualified": self.is_qualified,
        }


class ToulminAnalysis(BaseModel):
    """Every layout found in one source."""

    model_config = {"extra": "forbid"}

    layouts: list[ToulminLayout] = Field(
        default_factory=list,
        description=(
            "One entry per distinct argument in the passage. A passage that argues nothing yields an empty list — "
            "never invent a layout to fill it."
        ),
    )

    def to_payload(self) -> dict[str, JsonValue]:
        return {
            "layouts": [layout.to_payload() for layout in self.layouts],
            "layout_count": len(self.layouts),
            "fully_qualified_count": sum(layout.is_qualified for layout in self.layouts),
        }


__all__ = [
    "IncompleteLayoutError",
    "LayoutError",
    "NonEmpty",
    "Rebuttal",
    "ToulminAnalysis",
    "ToulminLayout",
]
