"""Persisted Classical Rhetoric output contract."""

from typing import Self

from pydantic import NonNegativeInt, model_validator

from rdam._native_output import ExtractionRecord
from rdam._strict import StrictModel
from rdam.classical_rhetoric.rhetoric import (
    ETHOS_SUBMODES,
    LOGOS_SUBMODES,
    NonEmpty,
    PistisMode,
    RhetoricalScheme,
    StasisKind,
)
from rdam.ingest.contracts.evidence import SourceEvidenceSpan


class AppealOutput(StrictModel):
    appeal_id: NonEmpty
    pistis: PistisMode
    sub_mode: NonEmpty
    rationale: NonEmpty
    span: SourceEvidenceSpan

    @model_validator(mode="after")
    def verify_submode(self) -> Self:
        if self.pistis == "ethos" and self.sub_mode not in ETHOS_SUBMODES:
            raise ValueError("Invalid ethos sub_mode")
        if self.pistis == "logos" and self.sub_mode not in LOGOS_SUBMODES:
            raise ValueError("Invalid logos sub_mode")
        return self


class KairosCueOutput(StrictModel):
    cue_id: NonEmpty
    urgency_or_timeliness: NonEmpty
    span: SourceEvidenceSpan


class StasisOutput(StrictModel):
    dominant_stasis: StasisKind
    contested_question: NonEmpty | None = None
    span: SourceEvidenceSpan | None = None

    @model_validator(mode="after")
    def verify_stasis(self) -> Self:
        if self.dominant_stasis == "none":
            if self.contested_question is not None or self.span is not None:
                raise ValueError("dominant_stasis='none' cannot carry contested_question or span")
        elif self.contested_question is None or self.span is None:
            raise ValueError("Active stasis requires contested_question and span")
        return self


class RhetoricalFigureOutput(StrictModel):
    figure_id: NonEmpty
    scheme: RhetoricalScheme
    explanation: NonEmpty
    span: SourceEvidenceSpan


class PistisBalanceOutput(StrictModel):
    ethos: NonNegativeInt
    pathos: NonNegativeInt
    logos: NonNegativeInt


class ClassicalRhetoricOutput(StrictModel):
    appeals: tuple[AppealOutput, ...]
    pistis_balance: PistisBalanceOutput
    kairos_cues: tuple[KairosCueOutput, ...]
    stasis: StasisOutput
    figures: tuple[RhetoricalFigureOutput, ...]
    extraction: ExtractionRecord

    @model_validator(mode="after")
    def verify_balance(self) -> Self:
        if (
            self.pistis_balance.ethos != sum(a.pistis == "ethos" for a in self.appeals)
            or self.pistis_balance.pathos != sum(a.pistis == "pathos" for a in self.appeals)
            or self.pistis_balance.logos != sum(a.pistis == "logos" for a in self.appeals)
        ):
            raise ValueError("pistis_balance must reproduce counts in appeals")
        return self
