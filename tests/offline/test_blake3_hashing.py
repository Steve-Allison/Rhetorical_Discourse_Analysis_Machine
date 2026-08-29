"""Unit tests for workbench.hashing (BLAKE3 & SHA-256 hybrid engine)."""

import hashlib
from pathlib import Path
import pytest
from pydantic import BaseModel

import blake3
from workbench.hashing import (
    blake3_digest,
    blake3_file_digest,
    canonical_json_bytes,
    canonical_json_digest,
    sha256_digest,
    sha256_file_digest,
)


class _SampleModel(BaseModel):
    name: str
    values: list[int]
    enabled: bool


def test_blake3_digest_matches_reference() -> None:
    data = b"discourse rhetorical analysis payload"
    expected = blake3.blake3(data).hexdigest()
    assert blake3_digest(data) == expected
    assert blake3_digest(data.decode("utf-8")) == expected
    assert len(blake3_digest(data)) == 64


def test_sha256_digest_matches_stdlib() -> None:
    data = b"discourse rhetorical analysis payload"
    expected = hashlib.sha256(data).hexdigest()
    assert sha256_digest(data) == expected
    assert sha256_digest(data.decode("utf-8")) == expected
    assert len(sha256_digest(data)) == 64


def test_streaming_file_digests(tmp_path: Path) -> None:
    test_file = tmp_path / "large_sample.bin"
    chunk = b"A" * 1024 * 1024  # 1 MB
    test_file.write_bytes(chunk * 5)  # 5 MB

    expected_blake3 = blake3.blake3(chunk * 5).hexdigest()
    expected_sha256 = hashlib.sha256(chunk * 5).hexdigest()

    assert blake3_file_digest(test_file) == expected_blake3
    assert sha256_file_digest(test_file) == expected_sha256


def test_canonical_json_bytes_ordering() -> None:
    obj_a = {"b": 2, "a": 1, "nested": {"z": 9, "y": 8}}
    obj_b = {"nested": {"y": 8, "z": 9}, "a": 1, "b": 2}

    assert canonical_json_bytes(obj_a) == canonical_json_bytes(obj_b)
    assert canonical_json_bytes(obj_a) == b'{"a":1,"b":2,"nested":{"y":8,"z":9}}'


def test_canonical_json_digest_model_support() -> None:
    model = _SampleModel(name="test_model", values=[1, 2, 3], enabled=True)
    digest_sha256 = canonical_json_digest(model, algorithm="sha256")
    digest_blake3 = canonical_json_digest(model, algorithm="blake3")

    assert len(digest_sha256) == 64
    assert len(digest_blake3) == 64
    assert digest_sha256 != digest_blake3


def test_canonical_json_digest_rejects_unknown_algo() -> None:
    with pytest.raises(ValueError, match="unsupported hashing algorithm"):
        canonical_json_digest({"a": 1}, algorithm="md5")
