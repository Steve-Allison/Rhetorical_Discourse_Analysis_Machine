"""One canonical JSON and SHA-256 kernel for every RDAM runtime contract."""

from collections.abc import Mapping, Sequence
from dataclasses import asdict, is_dataclass
from datetime import datetime
from enum import Enum
import hashlib
from pathlib import Path, PurePath
from typing import Any, Final, cast

from pydantic import BaseModel
import rfc8785

_IJSON_INTEGER_LIMIT: Final = 9_007_199_254_740_991


def json_projection(value: Any) -> Any:
    """Project supported Python values onto the JSON data model without loss."""

    if isinstance(value, BaseModel):
        return json_projection(value.model_dump(mode="json", exclude_none=False))
    if is_dataclass(value) and not isinstance(value, type):
        return json_projection(asdict(value))
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, PurePath):
        return value.as_posix()
    if isinstance(value, bytes):
        return value.hex()
    if isinstance(value, tuple | list):
        sequence = cast(Sequence[Any], value)
        return [json_projection(item) for item in sequence]
    if isinstance(value, Mapping):
        mapping = cast(Mapping[Any, Any], value)
        if any(not isinstance(key, str) for key in mapping):
            raise TypeError("canonical mappings require string keys")
        return {cast(str, key): json_projection(item) for key, item in mapping.items()}
    if value is None or isinstance(value, str | int | float | bool):
        return value
    raise TypeError(f"unsupported canonical value: {type(value).__name__}")


def validate_ijson_value(value: Any) -> None:
    """Reject values outside the interoperable JSON subset used by contracts."""

    if isinstance(value, str):
        if any(0xD800 <= ord(character) <= 0xDFFF for character in value):
            raise ValueError("unpaired Unicode surrogate is forbidden by I-JSON")
        return
    if isinstance(value, bool) or value is None:
        return
    if isinstance(value, int):
        if abs(value) > _IJSON_INTEGER_LIMIT:
            raise ValueError("integer exceeds the interoperable I-JSON range")
        return
    if isinstance(value, float):
        if not (-float("inf") < value < float("inf")):
            raise ValueError("non-finite JSON number is forbidden")
        return
    if isinstance(value, list | tuple):
        for item in cast(Sequence[Any], value):
            validate_ijson_value(item)
        return
    if isinstance(value, Mapping):
        for key, item in cast(Mapping[Any, Any], value).items():
            if not isinstance(key, str):
                raise TypeError("JSON object keys must be strings")
            validate_ijson_value(key)
            validate_ijson_value(item)
        return
    raise TypeError(f"value is outside the JSON data model: {type(value).__name__}")


def canonical_json_bytes(value: Any) -> bytes:
    """Return RFC 8785 bytes for the canonical JSON projection of ``value``."""

    projected = json_projection(value)
    validate_ijson_value(projected)
    return rfc8785.dumps(projected)


def semantic_sha256(value: Any) -> str:
    """Return the SHA-256 digest of a value's canonical JSON bytes."""

    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def sha256_bytes(payload: bytes) -> str:
    """Return a lower-case SHA-256 digest for immutable bytes."""

    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    """Stream a local regular file into a SHA-256 digest."""

    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


__all__ = [
    "canonical_json_bytes",
    "json_projection",
    "semantic_sha256",
    "sha256_bytes",
    "sha256_file",
    "validate_ijson_value",
]
