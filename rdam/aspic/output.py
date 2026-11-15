"""Persisted ASPIC+ output contract."""

from typing import Literal, Self

from pydantic import Field, NonNegativeInt, model_validator

from rdam._native_output import DerivedFromRecord, ExtractionRecord
from rdam._strict import StrictModel
from rdam.aspic.theory import (
     AspicTheoryInput,
    AttackKind,
    NonEmpty,
)
from rdam.dung.output import ExtensionOutput
from rdam.ingest.contracts.evidence import SourceEvidenceSpan


class ConstructedArgumentOutput(StrictModel):
    id: NonEmpty
    conclusion: NonEmpty
    top_rule_id: NonEmpty | None = None
    top_rule_strict: bool
    direct_sub_ids: tuple[NonEmpty, ...]
    all_sub_ids: tuple[NonEmpty, ...] = Field(min_length=1)
    ordinary_premises_used: tuple[NonEmpty, ...]
    defeasible_rules_used: tuple[NonEmpty, ...]
    last_defeasible_rules: tuple[NonEmpty, ...]
    is_strict: bool
    is_firm: bool


class AspicAttackOutput(StrictModel):
    attacker: NonEmpty
    target: NonEmpty
    on_sub_argument: NonEmpty
    kind: AttackKind
    succeeded_as_defeat: bool


class DefeatFrameworkOutput(StrictModel):
    arguments: tuple[NonEmpty, ...]
    attacks: tuple[tuple[NonEmpty, NonEmpty], ...]


class RationalityPostulatesOutput(StrictModel):
    sub_argument_closure: bool
    strict_closure: bool
    direct_consistency: bool
    indirect_consistency: bool
    all_satisfied: bool

    @model_validator(mode="after")
    def verify_conjunction(self) -> Self:
        expected = (
            self.sub_argument_closure
            and self.strict_closure
            and self.direct_consistency
            and self.indirect_consistency
        )
        if self.all_satisfied != expected:
            raise ValueError("all_satisfied must equal conjunction of the four Caminada-Amgoud postulates")
        return self


class AspicEvidenceRecord(StrictModel):
    item_kind: Literal["premise", "rule"]
    identifier: NonEmpty
    span: SourceEvidenceSpan


class AspicOutput(StrictModel):
    theory: AspicTheoryInput
    input_origin: Literal["supplied", "explicitly_derived", "extracted"]
    extraction: ExtractionRecord | None = None
    arguments: tuple[ConstructedArgumentOutput, ...]
    attacks: tuple[AspicAttackOutput, ...]
    defeat_framework: DefeatFrameworkOutput
    extensions: ExtensionOutput
    rationality_postulates: RationalityPostulatesOutput
    argument_count: NonNegativeInt
    defeat_count: NonNegativeInt
    evidence: tuple[AspicEvidenceRecord, ...] | None = None
    derived_from: DerivedFromRecord | None = None

    @model_validator(mode="after")
    def verify_mode_and_counts(self) -> Self:
        if self.argument_count != len(self.arguments) or self.defeat_count != len(self.defeat_framework.attacks):
            raise ValueError("ASPIC+ counts must match arguments and defeat_framework.attacks")
        if self.input_origin == "extracted":
            if self.extraction is None:
                raise ValueError("Extracted ASPIC+ output requires extraction provenance")
            if self.derived_from is not None:
                raise ValueError("Extracted ASPIC+ output cannot set derived_from")
        else:
            if self.extraction is not None:
                raise ValueError("Supplied/derived ASPIC+ output cannot carry LLM extraction provenance")
            if (self.input_origin == "explicitly_derived") != (self.derived_from is not None):
                raise ValueError("derived_from must match explicitly_derived input_origin")
        return self
