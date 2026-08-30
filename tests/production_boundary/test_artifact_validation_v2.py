"""Wheel RECORD, content, metadata, and provenance validation tests."""

from collections.abc import Mapping
from pathlib import Path

from tools.production_boundary.artifacts import validate_release_artifacts


def test_built_pair_passes_complete_artifact_validation(
    built_release_pair: tuple[Path, Path, str],
) -> None:
    wheel, sdist, commit = built_release_pair
    evidence = validate_release_artifacts(
        wheel,
        sdist,
        expected_source_commit=commit,
    )
    assert evidence["valid"] is True
    wheel_validation = evidence["wheel_validation"]
    assert isinstance(wheel_validation, Mapping)
    assert wheel_validation["record_verified"] is True
