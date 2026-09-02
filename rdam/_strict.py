"""Strict, canonical, content-addressed record semantics for the machine layer.

These adopt the semantics of the RST provider's contract base (standardised pattern
P3: RFC 8785 canonical JSON, SHA-256 semantic digests, closed immutable models) without
importing that provider — the machine layer owns its own copy of the *semantics*, per
the 006 standardised-patterns register.
"""

from collections.abc import Mapping, Sequence
from datetime import datetime
from enum import Enum
import hashlib
from pathlib import PurePath
import re
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, RootModel, model_validator
import rfc8785

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


def json_projection(value: Any) -> Any:
    """Project supported values onto the JSON data model without losing meaning."""

    if isinstance(value, BaseModel):
        return json_projection(value.model_dump(mode="json", exclude_none=False))
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, PurePath):
        return value.as_posix()
    if isinstance(value, bytes):
        return value.hex()
    if isinstance(value, tuple | list):
        return [json_projection(item) for item in value]
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise TypeError("canonical mappings require string keys")
        return {key: json_projection(item) for key, item in value.items()}
    if value is None or isinstance(value, str | int | float | bool):
        return value
    raise TypeError(f"unsupported canonical value: {type(value).__name__}")


def canonical_json_bytes(value: Any) -> bytes:
    """RFC 8785 canonical bytes of the JSON projection of ``value``."""

    return rfc8785.dumps(json_projection(value))


def semantic_sha256(value: Any) -> str:
    """SHA-256 hex digest of the canonical JSON projection of ``value``."""

    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


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
