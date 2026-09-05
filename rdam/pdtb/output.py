"""Persisted PDTB output includes the actual derived relation/type counts."""

from pydantic import Field
from rdam._native_output import ExtractionRecord
from rdam._strict import StrictModel
from rdam.pdtb.relations import PdtbRelation, RelationType


class PdtbOutput(StrictModel):
    relations: tuple[PdtbRelation, ...]
    relation_count: int = Field(ge=0)
    relation_type_counts: dict[RelationType, int]
    extraction: ExtractionRecord
