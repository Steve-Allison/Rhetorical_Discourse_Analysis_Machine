"""Persisted SDRT output includes native counts and the structural-check result."""

from typing import Literal, Self
from pydantic import Field, model_validator
from rdam._native_output import ExtractionRecord
from rdam._strict import StrictModel
from rdam.sdrt.graph import ElementaryDiscourseUnit, ComplexDiscourseUnit, SdrtRelation, SdrtAnalysis


class SdrtOutput(StrictModel):
    edus: tuple[ElementaryDiscourseUnit, ...] = Field(min_length=1)
    cdus: tuple[ComplexDiscourseUnit, ...]
    relations: tuple[SdrtRelation, ...]
    edu_count: int = Field(ge=1)
    cdu_count: int = Field(ge=0)
    relation_count: int = Field(ge=0)
    right_frontier_validated: Literal[True]
    extraction: ExtractionRecord

    @model_validator(mode="after")
    def graph_and_counts_reproduce(self) -> Self:
        graph = SdrtAnalysis(edus=list(self.edus), cdus=list(self.cdus), relations=list(self.relations))
        if (self.edu_count, self.cdu_count, self.relation_count) != (
            len(graph.edus), len(graph.cdus), len(graph.relations)
        ):
            raise ValueError("SDRT counts must reproduce the stored graph")
        return self
