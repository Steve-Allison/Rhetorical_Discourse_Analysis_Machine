from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path

from isanlp_rst.model_loading.release import ParserCapacity, validate_model_release
from isanlp_rst.model_loading import ParserInput


def _release(tmp_path: Path) -> Path:
    release = tmp_path / "test-release"
    release.mkdir()
    model = release / "model.bin"
    model.write_bytes(b"immutable model")
    manifest = {
        "schema_version": "isanlp_rst_model_release/v1",
        "release_id": "test-release",
        "model_task": "rst-parsing",
        "architecture": "test-parser",
        "runtime_contract": "isanlp_rst.parser/dmrst-v1",
        "compatibility_range": ">=4,<5",
        "source_model_identity": "test/source@one",
        "source_revision": "a" * 40,
        "licence": "MIT",
        "use_restrictions": [],
        "evaluation_evidence": "local:test",
        "evaluation_unavailable_reason": None,
        "created_at": datetime(2026, 8, 25, tzinfo=UTC).isoformat(),
        "producer_version": "4.0.0",
        "files": [
            {
                "path": "model.bin",
                "role": "weights",
                "size_bytes": model.stat().st_size,
                "sha256": hashlib.sha256(model.read_bytes()).hexdigest(),
            }
        ],
    }
    (release / "release-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return release


def test_validated_release_exposes_complete_analytical_identity(tmp_path: Path) -> None:
    release = validate_model_release(
        _release(tmp_path),
        expected_runtime_contract="isanlp_rst.parser/dmrst-v1",
        package_version="4.0.0",
    )
    identity = release.analysis_identity(ParserCapacity(unit="edu_count", maximum=512, source="parser-v1"))
    assert identity.release_id == "test-release"
    assert identity.files[0].sha256 == hashlib.sha256(b"immutable model").hexdigest()
    assert identity.capacity.maximum == 512
    assert len(identity.semantic_digest) == 64


def test_capacity_is_strict_and_uses_the_actual_unit() -> None:
    capacity = ParserCapacity(unit="edu_count", maximum=512, source="parser-v1")
    assert capacity.unit == "edu_count"
    assert ParserInput(edu_breaks=[2, 7, 11]).edu_count == 3
