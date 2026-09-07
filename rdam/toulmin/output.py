"""Persisted Toulmin output shape, including computed qualification fields."""

from typing import Literal, Self
from pydantic import Field, model_validator
from rdam._native_output import ExtractionRecord
from rdam._strict import StrictModel
from rdam.ingest.contracts.evidence import SourceEvidenceSpan
from rdam.toulmin.argument import NonEmpty, Rebuttal, ToulminLayout


class HistoricalLayoutOutput(StrictModel):
    claim: NonEmpty
    grounds: tuple[NonEmpty, ...] = Field(min_length=1)
    warrant: NonEmpty
    backing: tuple[NonEmpty, ...]
    qualifier: NonEmpty | None
    rebuttals: tuple[Rebuttal, ...]
    elements_present: tuple[Literal["claim", "grounds", "warrant", "backing", "qualifier", "rebuttal"], ...]
    is_qualified: bool


class LayoutOutput(HistoricalLayoutOutput):
    warrant_origin: Literal["explicit", "reconstructed", "undetermined"]
    warrant_evidence: tuple[SourceEvidenceSpan, ...]
    warrant_origin_reason: Literal["insufficient_context", "ambiguous_source"] | None

    @model_validator(mode="after")
    def derived_fields_match_layout(self) -> Self:
        layout = ToulminLayout.model_validate(self.model_dump(exclude={"elements_present", "is_qualified"}))
        if self.elements_present != layout.elements_present or self.is_qualified != layout.is_qualified:
            raise ValueError("Toulmin derived fields must reproduce the stored layout")
        return self


class ToulminOutput(StrictModel):
    layouts: tuple[LayoutOutput, ...]
    layout_count: int = Field(ge=0)
    qualified_layout_count: int = Field(ge=0)
    extraction: ExtractionRecord

    @model_validator(mode="after")
    def counts_match_native_layouts(self) -> Self:
        if self.layout_count != len(self.layouts) or self.qualified_layout_count != sum(
            layout.is_qualified for layout in self.layouts
        ):
            raise ValueError("Toulmin counts must reproduce the stored layouts")
        return self


class HistoricalToulminOutput(StrictModel):
    layouts: tuple[HistoricalLayoutOutput, ...]
    layout_count: int = Field(ge=0)
    fully_qualified_count: int = Field(ge=0)
    extraction: ExtractionRecord
