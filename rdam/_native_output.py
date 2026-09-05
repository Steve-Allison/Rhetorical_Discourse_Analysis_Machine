"""Shared factual extraction and caller-declared lineage metadata."""

from pydantic import Field
from rdam._strict import StrictModel
from rdam.frameworks import Technique


class ExtractionRecord(StrictModel):
    model: str = Field(min_length=1)
    output_attempts: int = Field(ge=1)
    transport_attempts: int = Field(ge=1)
    instructions_digest: str = Field(pattern=r"^[0-9a-f]{64}$")


class DerivedFromRecord(StrictModel):
    technique: Technique
    result_identity: str = Field(pattern=r"^[0-9a-f]{64}$")
