"""Wheel RECORD, content, metadata, and provenance validation tests."""

from collections.abc import Mapping
import json
from pathlib import Path
import zipfile

import pytest
import rfc8785

from tools.production_boundary.artifacts import _validate_provenance, validate_release_artifacts


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


def test_provenance_with_an_extra_field_fails_the_artifact_gate(
    built_release_pair: tuple[Path, Path, str],
) -> None:
    """The artifact validator enforces the runtime reader's exact field set.

    A field the installed reader does not know would make every analysis fail at
    runtime; that must be caught here, not by the clean install.
    """

    wheel, _, _ = built_release_pair
    with zipfile.ZipFile(wheel) as archive:
        payload = json.loads(archive.read("isanlp_rst/build-provenance.json"))
    assert _validate_provenance(rfc8785.dumps(payload) + b"\n", None) == payload

    drifted = {**payload, "source_tag": None}
    with pytest.raises(ValueError, match="exact runtime field set"):
        _validate_provenance(rfc8785.dumps(drifted) + b"\n", None)
