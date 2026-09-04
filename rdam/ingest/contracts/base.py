"""Shared invariants and identities for production contract 2.0.0."""

from enum import StrEnum
import re
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, RootModel, model_validator

PRODUCTION_CONTRACT = "isanlp_rst.production"
WRITE_CONTRACT_VERSION = "2.0.0"
READABLE_CONTRACT_VERSIONS = (WRITE_CONTRACT_VERSION,)
INGEST_SCHEMA_NAME = PRODUCTION_CONTRACT
INGEST_SCHEMA_VERSION = WRITE_CONTRACT_VERSION
INGEST_PIPELINE_VERSION = WRITE_CONTRACT_VERSION

_SEMANTIC_VERSION = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")


class StrictContractModel(BaseModel):
    """Closed immutable base used recursively by every persisted contract value."""

    model_config = ConfigDict(
        allow_inf_nan=False,
        extra="forbid",
        frozen=True,
        ser_json_bytes="base64",
        strict=True,
        validate_default=True,
        val_json_bytes="base64",
    )


class SemanticVersion(RootModel[str]):
    """Normalized public-contract version with no prerelease or local suffix."""

    model_config = ConfigDict(frozen=True, strict=True)

    @model_validator(mode="after")
    def normalized_release_triplet(self) -> Self:
        if _SEMANTIC_VERSION.fullmatch(self.root) is None:
            raise ValueError("semantic version must be a normalized major.minor.patch release")
        return self

    def __str__(self) -> str:
        return self.root


class Sha256Identity(StrictContractModel):
    """Unambiguous SHA-256 identity used by every semantic digest field."""

    algorithm: Literal["sha256"] = "sha256"
    hex_digest: str = Field(pattern=r"^[0-9a-f]{64}$")


class CoverageUnit(StrEnum):
    CHARACTERS = "characters"
    ITEMS = "items"
    SEGMENTS = "segments"
    ANCHORS = "anchors"


class ExactCoverage(StrictContractModel):
    """Exact coverage counts; a float is only a derived display convenience."""

    covered_units: int = Field(ge=0)
    total_units: int = Field(ge=0)
    unit: CoverageUnit

    @model_validator(mode="after")
    def covered_does_not_exceed_total(self) -> Self:
        if self.covered_units > self.total_units:
            raise ValueError("covered_units cannot exceed total_units")
        return self

    @property
    def ratio(self) -> float | None:
        return None if self.total_units == 0 else self.covered_units / self.total_units


class EmptyExecution(StrictContractModel):
    """Explicit empty execution section for non-executing contract records."""


__all__ = [
    "INGEST_PIPELINE_VERSION",
    "INGEST_SCHEMA_NAME",
    "INGEST_SCHEMA_VERSION",
    "PRODUCTION_CONTRACT",
    "READABLE_CONTRACT_VERSIONS",
    "WRITE_CONTRACT_VERSION",
    "CoverageUnit",
    "EmptyExecution",
    "ExactCoverage",
    "SemanticVersion",
    "Sha256Identity",
    "StrictContractModel",
]
