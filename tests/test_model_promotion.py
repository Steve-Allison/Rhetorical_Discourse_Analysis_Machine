"""Production model-release validation and offline promotion tests."""

import json
from pathlib import Path, PurePosixPath

import pytest

from isanlp_rst.model_loading import ModelReleaseError, load_model_release, validate_model_release
from isanlp_rst.model_loading.release import MODEL_RELEASE_MANIFEST, ModelReleaseManifest, canonical_json_bytes
from offline_workbench.promotion import promote_model_release, write_candidate_manifest

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
        compatibility_range=">=4,<5",
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
    with pytest.raises(ModelReleaseError, match="outside model compatibility range"):
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
            compatibility_range=">=4,<5",
            source_model_identity="fixture/tiny",
            source_revision="a" * 40,
            licence="MIT",
            use_restrictions=(),
            roles={PurePosixPath("config.json"): "configuration"},
        )
