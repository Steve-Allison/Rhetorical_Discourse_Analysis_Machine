"""Persisted Toulmin output shape, including computed qualification fields."""

from typing import Literal
from pydantic import Field
from rdam._native_output import ExtractionRecord
from rdam._strict import StrictModel
from rdam.ingest.contracts.evidence import SourceEvidenceSpan
from rdam.toulmin.argument import NonEmpty, Rebuttal


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


class ToulminOutput(StrictModel):
    layouts: tuple[LayoutOutput, ...]
    layout_count: int = Field(ge=0)
    qualified_layout_count: int = Field(ge=0)
    extraction: ExtractionRecord


class HistoricalToulminOutput(StrictModel):
    layouts: tuple[HistoricalLayoutOutput, ...]
    layout_count: int = Field(ge=0)
    fully_qualified_count: int = Field(ge=0)
    extraction: ExtractionRecord
