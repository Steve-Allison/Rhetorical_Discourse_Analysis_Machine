"""Production model-release validation and offline promotion tests."""

import json
from pathlib import Path, PurePosixPath

import pytest

from datetime import UTC, datetime
from rdam.rst.model_loading import ModelReleaseError, load_model_release, validate_model_release
from rdam.rst.model_loading.release import (
    MODEL_RELEASE_MANIFEST,
    CompatibilityRedeclaration,
    ModelReleaseManifest,
    canonical_json_bytes,
    compatibility_redeclaration_path,
)
from workbench.promotion import promote_model_release, write_candidate_manifest
from workbench.promotion.compatibility import redeclare_compatibility

_RUNTIME_CONTRACT = "isanlp_rst.parser/dmrst-v1"


def _candidate(tmp_path: Path, *, release_id: str = "gumrrg-test-release") -> Path:
    candidate = tmp_path / f"candidate-{release_id}"
    (candidate / "weights").mkdir(parents=True)
    (candidate / "config.json").write_text('{"architecture":"tiny"}', encoding="utf-8")
    (candidate / "weights/model.safetensors").write_bytes(b"safe-test-weights")
    write_candidate_manifest(
        candidate,
        release_id=release_id,
        model_task="rst-parsing",
        architecture="tiny-test-parser",
        runtime_contract=_RUNTIME_CONTRACT,
        compatibility_range=">=5,<7",
        source_model_identity="fixture/tiny-test-parser",
        source_revision="a" * 40,
        licence="CC-BY-NC-4.0",
        use_restrictions=("non-commercial",),
        roles={
            PurePosixPath("config.json"): "configuration",
            PurePosixPath("weights/model.safetensors"): "model-weights",
        },
        evaluation_evidence="fixture parity test",
    )
    return candidate


def test_valid_candidate_promotes_atomically_and_loads_from_store(tmp_path: Path) -> None:
    candidate = _candidate(tmp_path)
    store = tmp_path / "production-store"

    receipt = promote_model_release(candidate, store)
    release = load_model_release(store, "gumrrg-test-release", expected_runtime_contract=_RUNTIME_CONTRACT)

    assert receipt.succeeded
    assert receipt.verified_files == 2
    assert receipt.candidate_manifest_sha256 == receipt.release_manifest_sha256
    assert release.path == (store / "gumrrg-test-release").resolve()
    assert (release.path / "weights/model.safetensors").read_bytes() == b"safe-test-weights"


def test_loose_and_unpromoted_inputs_are_rejected(tmp_path: Path) -> None:
    loose = tmp_path / "loose"
    loose.mkdir()
    (loose / "model.safetensors").write_bytes(b"weights")

    with pytest.raises(ModelReleaseError, match="missing a regular release-manifest.json"):
        validate_model_release(loose)
    with pytest.raises(ModelReleaseError, match="must be a real local directory"):
        load_model_release(tmp_path / "store", "not-promoted", expected_runtime_contract=_RUNTIME_CONTRACT)


def test_partial_changed_and_unknown_members_are_rejected(tmp_path: Path) -> None:
    partial = _candidate(tmp_path, release_id="partial")
    (partial / "config.json").unlink()
    with pytest.raises(ModelReleaseError, match="membership mismatch"):
        validate_model_release(partial, require_release_name=False)

    changed = _candidate(tmp_path, release_id="changed")
    (changed / "weights/model.safetensors").write_bytes(b"SAFE-test-weights")
    with pytest.raises(ModelReleaseError, match="SHA-256 mismatch"):
        validate_model_release(changed, require_release_name=False)

    unknown = _candidate(tmp_path, release_id="unknown")
    (unknown / "undeclared.txt").write_text("unexpected", encoding="utf-8")
    with pytest.raises(ModelReleaseError, match="membership mismatch"):
        validate_model_release(unknown, require_release_name=False)


def test_incompatible_contract_version_and_symlink_are_rejected(tmp_path: Path) -> None:
    candidate = _candidate(tmp_path, release_id="incompatible")
    manifest_path = candidate / MODEL_RELEASE_MANIFEST
    manifest = ModelReleaseManifest.model_validate_json(manifest_path.read_bytes())

    wrong_contract = manifest.model_copy(update={"runtime_contract": "different/runtime-v9"})
    manifest_path.write_bytes(canonical_json_bytes(wrong_contract))
    with pytest.raises(ModelReleaseError, match="runtime contract mismatch"):
        validate_model_release(
            candidate,
            expected_runtime_contract=_RUNTIME_CONTRACT,
            require_release_name=False,
        )

    incompatible = manifest.model_copy(update={"compatibility_range": ">=99"})
    manifest_path.write_bytes(canonical_json_bytes(incompatible))
    with pytest.raises(ModelReleaseError, match="outside the declared model compatibility range"):
        validate_model_release(candidate, require_release_name=False)

    manifest_path.write_bytes(canonical_json_bytes(manifest))
    (candidate / "unsafe-link").symlink_to(candidate / "config.json")
    with pytest.raises(ModelReleaseError, match="contains a symlink"):
        validate_model_release(candidate, require_release_name=False)


def test_promotion_never_overwrites_an_existing_release(tmp_path: Path) -> None:
    candidate = _candidate(tmp_path)
    store = tmp_path / "production-store"
    first = promote_model_release(candidate, store)
    assert first.succeeded
    with pytest.raises(FileExistsError, match="immutable model release already exists"):
        promote_model_release(candidate, store)


def test_compatibility_redeclaration_widens_the_range_for_this_exact_manifest(tmp_path: Path) -> None:
    """An immutable release stays loadable under a later package line only through an explicit,
    manifest-bound re-declaration beside it — the manifest bytes never change."""

    candidate = _candidate(tmp_path)
    store = tmp_path / "production-store"
    promote_model_release(candidate, store)
    release = store / "gumrrg-test-release"
    manifest_before = (release / MODEL_RELEASE_MANIFEST).read_bytes()
    with pytest.raises(ModelReleaseError, match="outside the declared model compatibility range"):
        validate_model_release(release, package_version="7.5.0")

    redeclaration = redeclare_compatibility(
        store,
        "gumrrg-test-release",
        compatibility_range=">=5,<8",
        declared_by="test",
        reason="fixture runtime contract unchanged across the 7.x line",
        basis=("tests/offline/test_model_promotion.py",),
    )
    validated = validate_model_release(release, package_version="7.5.0")
    assert validated.redeclaration == redeclaration
    assert validated.compatibility_range == ">=5,<8"
    assert validated.manifest.compatibility_range == ">=5,<7"
    assert (release / MODEL_RELEASE_MANIFEST).read_bytes() == manifest_before
    assert compatibility_redeclaration_path(release).parent == store
    with pytest.raises(ModelReleaseError, match="outside the re-declared model compatibility range"):
        validate_model_release(release, package_version="8.0.0")
    with pytest.raises(FileExistsError, match="different compatibility re-declaration"):
        redeclare_compatibility(
            store, "gumrrg-test-release", compatibility_range=">=5,<9", declared_by="test", reason="other", basis=("x",)
        )


def test_compatibility_redeclaration_for_another_manifest_is_refused(tmp_path: Path) -> None:
    candidate = _candidate(tmp_path)
    store = tmp_path / "production-store"
    promote_model_release(candidate, store)
    release = store / "gumrrg-test-release"
    stale = CompatibilityRedeclaration(
        release_id="gumrrg-test-release",
        manifest_sha256="0" * 64,
        compatibility_range=">=5,<8",
        declared_at=datetime(2026, 9, 2, tzinfo=UTC),
        declared_by="test",
        reason="names a manifest that is not this one",
        basis=("fixture",),
    )
    compatibility_redeclaration_path(release).write_bytes(canonical_json_bytes(stale))
    with pytest.raises(ModelReleaseError, match="does not name this release's manifest"):
        validate_model_release(release)
    with pytest.raises(ModelReleaseError, match="does not name this release's manifest"):
        load_model_release(store, "gumrrg-test-release", expected_runtime_contract=_RUNTIME_CONTRACT)


def test_manifest_is_strict_and_requires_honest_evaluation_evidence(tmp_path: Path) -> None:
    candidate = tmp_path / "candidate"
    candidate.mkdir()
    (candidate / "config.json").write_text(json.dumps({"ok": True}), encoding="utf-8")
    with pytest.raises(ValueError, match="evaluation_evidence or evaluation_unavailable_reason"):
        write_candidate_manifest(
            candidate,
            release_id="missing-evidence",
            model_task="rst-parsing",
            architecture="tiny",
            runtime_contract=_RUNTIME_CONTRACT,
            compatibility_range=">=5,<7",
            source_model_identity="fixture/tiny",
            source_revision="a" * 40,
            licence="MIT",
            use_restrictions=(),
            roles={PurePosixPath("config.json"): "configuration"},
        )
