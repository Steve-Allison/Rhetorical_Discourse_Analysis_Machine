"""Strict, canonical, content-addressed record semantics for the machine layer.

These adopt the semantics of the RST provider's contract base (standardised pattern
P3: RFC 8785 canonical JSON, SHA-256 semantic digests, closed immutable models) without
importing that provider — the machine layer owns its own copy of the *semantics*, per
the 006 standardised-patterns register.
"""

from collections.abc import Mapping, Sequence
import re
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, RootModel, model_validator

from rdam._canonical import canonical_json_bytes, json_projection, semantic_sha256, sha256_bytes

_SEMANTIC_VERSION = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")

type JsonScalar = str | int | float | bool | None
type JsonValue = JsonScalar | Sequence["JsonValue"] | Mapping[str, "JsonValue"]


class StrictModel(BaseModel):
    """Closed, immutable, strictly validated base for every machine-layer record."""

    model_config = ConfigDict(
        allow_inf_nan=False,
        extra="forbid",
        frozen=True,
        strict=True,
        validate_default=True,
    )


class SemanticVersion(RootModel[str]):
    """Normalized ``major.minor.patch`` with no prerelease or local suffix."""

    model_config = ConfigDict(frozen=True, strict=True)

    @model_validator(mode="after")
    def normalized_release_triplet(self) -> Self:
        if _SEMANTIC_VERSION.fullmatch(self.root) is None:
            raise ValueError("semantic version must be a normalized major.minor.patch release")
        return self

    def __str__(self) -> str:
        return self.root


class Sha256Identity(StrictModel):
    """Unambiguous SHA-256 identity used by every semantic digest field."""

    algorithm: Literal["sha256"] = "sha256"
    hex_digest: str = Field(pattern=r"^[0-9a-f]{64}$")


__all__ = [
    "JsonScalar",
    "JsonValue",
    "SemanticVersion",
    "Sha256Identity",
    "StrictModel",
    "canonical_json_bytes",
    "json_projection",
    "semantic_sha256",
    "sha256_bytes",
]
