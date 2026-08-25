"""Canonical analytical identities for production source ingest."""

from dataclasses import asdict, is_dataclass
from datetime import datetime
from enum import Enum
import hashlib
from pathlib import Path, PurePath
from typing import Any

from pydantic import BaseModel
import rfc8785


def _json_value(value: Any) -> Any:
    """Project supported values to the JSON data model without losing meaning."""

    if isinstance(value, BaseModel):
        return _json_value(value.model_dump(mode="json", exclude_none=False))
    if is_dataclass(value) and not isinstance(value, type):
        return _json_value(asdict(value))
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, PurePath):
        return value.as_posix()
    if isinstance(value, bytes):
        return value.hex()
    if isinstance(value, tuple | list):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        if any(not isinstance(key, str) for key in value):
            raise TypeError("canonical semantic mappings require string keys")
        return {key: _json_value(item) for key, item in value.items()}
    if value is None or isinstance(value, str | int | float | bool):
        return value
    raise TypeError(f"unsupported canonical semantic value: {type(value).__name__}")


def canonical_json_bytes(value: Any) -> bytes:
    """Serialize a value with RFC 8785 JSON Canonicalization Scheme."""

    return rfc8785.dumps(_json_value(value))


def semantic_sha256(value: Any) -> str:
    """Return the SHA-256 identity of a canonical semantic value."""

    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def sha256_bytes(value: bytes) -> str:
    """Return a lower-case SHA-256 digest for immutable bytes."""

    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    """Stream a local regular file into a SHA-256 digest."""

    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


__all__ = ["canonical_json_bytes", "semantic_sha256", "sha256_bytes", "sha256_file"]
