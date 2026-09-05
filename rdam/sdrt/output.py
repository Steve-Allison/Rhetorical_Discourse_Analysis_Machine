"""Persisted SDRT output includes native counts and the structural-check result."""

from typing import Literal
from pydantic import Field
from rdam._native_output import ExtractionRecord
from rdam._strict import StrictModel
from rdam.sdrt.graph import ElementaryDiscourseUnit, ComplexDiscourseUnit, SdrtRelation


class SdrtOutput(StrictModel):
    edus: tuple[ElementaryDiscourseUnit, ...] = Field(min_length=1)
    cdus: tuple[ComplexDiscourseUnit, ...]
    relations: tuple[SdrtRelation, ...]
    edu_count: int = Field(ge=1)
    cdu_count: int = Field(ge=0)
    relation_count: int = Field(ge=0)
    right_frontier_validated: Literal[True]
    extraction: ExtractionRecord
