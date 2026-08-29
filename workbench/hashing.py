"""High-performance hybrid cryptographic hashing for the offline workbench.

Provides ultra-fast BLAKE3 hashing for internal dataset sharding, candidate
indexing, and cache keys alongside NIST SHA-256 for public RFC-8785 JSON receipts
and release manifests.
"""

from collections.abc import Mapping
import hashlib
import json
from pathlib import Path
from typing import Any

import blake3
from pydantic import BaseModel

_BUFFER_SIZE = 1024 * 1024  # 1 MB read chunks


def blake3_digest(data: bytes | str) -> str:
    """Compute a 64-character lowercase hex BLAKE3 digest of in-memory data."""
    raw = data.encode("utf-8") if isinstance(data, str) else data
    return blake3.blake3(raw).hexdigest()


def blake3_file_digest(path: Path | str) -> str:
    """Compute a streaming BLAKE3 digest for a file on disk."""
    file_path = Path(path)
    hasher = blake3.blake3()
    with file_path.open("rb") as stream:
        while chunk := stream.read(_BUFFER_SIZE):
            hasher.update(chunk)
    return hasher.hexdigest()


def sha256_digest(data: bytes | str) -> str:
    """Compute a 64-character lowercase hex NIST SHA-256 digest of in-memory data."""
    raw = data.encode("utf-8") if isinstance(data, str) else data
    return hashlib.sha256(raw).hexdigest()


def sha256_file_digest(path: Path | str) -> str:
    """Compute a streaming NIST SHA-256 digest for a file on disk."""
    file_path = Path(path)
    hasher = hashlib.sha256()
    with file_path.open("rb") as stream:
        while chunk := stream.read(_BUFFER_SIZE):
            hasher.update(chunk)
    return hasher.hexdigest()


def canonical_json_bytes(value: BaseModel | Mapping[str, object] | Any) -> bytes:
    """Serialize a mapping or Pydantic model to RFC-8785 sorted canonical JSON bytes."""
    if isinstance(value, BaseModel):
        payload = value.model_dump(mode="json")
    elif isinstance(value, Mapping):
        payload = dict(value)
    else:
        payload = value
    return json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode("utf-8")


def canonical_json_digest(value: BaseModel | Mapping[str, object] | Any, *, algorithm: str = "sha256") -> str:
    """Compute a cryptographic digest of RFC-8785 canonical JSON bytes."""
    raw = canonical_json_bytes(value)
    if algorithm == "blake3":
        return blake3_digest(raw)
    if algorithm == "sha256":
        return sha256_digest(raw)
    raise ValueError(f"unsupported hashing algorithm: {algorithm!r} (expected 'blake3' or 'sha256')")
