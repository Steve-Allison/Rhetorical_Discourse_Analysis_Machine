"""Persisted PDTB output includes the actual derived relation/type counts."""

from typing import Self
from pydantic import Field, model_validator
from rdam._native_output import ExtractionRecord
from rdam._strict import StrictModel
from rdam.pdtb.relations import PdtbAnalysis, PdtbRelation, RelationType


class PdtbOutput(StrictModel):
    relations: tuple[PdtbRelation, ...]
    relation_count: int = Field(ge=0)
    relation_type_counts: dict[RelationType, int]
    extraction: ExtractionRecord

    @model_validator(mode="after")
    def counts_match_native_relations(self) -> Self:
        analysis = PdtbAnalysis(relations=self.relations)
        expected = dict.fromkeys(RelationType, 0)
        for relation in analysis.relations:
            expected[relation.relation_type] += 1
        if self.relation_count != len(analysis.relations) or self.relation_type_counts != expected:
            raise ValueError("PDTB counts must reproduce the stored relations")
        return self
