"""Production model-release validation and offline promotion tests."""

import json
from pathlib import Path, PurePosixPath

import pytest

from isanlp_rst.model_authority import MODERNBERT_BASE_MODEL_ID
from isanlp_rst.model_loading import ModelReleaseError, load_model_release, validate_model_release
from isanlp_rst.model_loading.release import MODEL_RELEASE_MANIFEST, ModelReleaseManifest, canonical_json_bytes
from workbench.promotion import promote_model_release, write_candidate_manifest
from workbench.promotion.modernbert import EVIDENCE_UNAVAILABLE_REASON, prepare_and_promote_modernbert

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
        compatibility_range=">=5,<6",
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


def _modernbert_candidate(tmp_path: Path, *, receipt: str | None) -> Path:
    candidate = tmp_path / "modernbert-candidate"
    candidate.mkdir()
    (candidate / "config.json").write_text('{"architecture":"tiny"}', encoding="utf-8")
    (candidate / "model.safetensors").write_bytes(b"safe-test-weights")
    (candidate / "relation_inventory.json").write_text('["elaboration","joint"]', encoding="utf-8")
    (candidate / "tokenizer.json").write_text("{}", encoding="utf-8")
    if receipt is not None:
        (candidate / "training_receipt.json").write_text(receipt, encoding="utf-8")
    return candidate


def _released_manifest(release_path: Path) -> ModelReleaseManifest:
    return ModelReleaseManifest.model_validate_json((release_path / MODEL_RELEASE_MANIFEST).read_bytes())


def test_modernbert_promotion_without_receipt_declares_evidence_unavailable(tmp_path: Path) -> None:
    """A candidate with no quality record must say so — never claim a verification that never ran."""

    candidate = _modernbert_candidate(tmp_path, receipt=None)
    release_path = prepare_and_promote_modernbert(candidate, tmp_path / "store")
    manifest = _released_manifest(release_path)

    assert manifest.evaluation_evidence is None
    assert manifest.evaluation_unavailable_reason == EVIDENCE_UNAVAILABLE_REASON
    assert "verified" not in EVIDENCE_UNAVAILABLE_REASON
    assert manifest.source_model_identity == MODERNBERT_BASE_MODEL_ID
    assert manifest.release_id.startswith("modernbert-v1-")


def test_modernbert_promotion_records_receipt_verbatim_and_preserves_it(tmp_path: Path) -> None:
    """The training receipt becomes the evidence verbatim and survives beside the candidate."""

    receipt = '{"run_id": "r1", "eval_metrics": {"test_full_f1": 0.198}}'
    candidate = _modernbert_candidate(tmp_path, receipt=receipt)
    release_path = prepare_and_promote_modernbert(candidate, tmp_path / "store")
    manifest = _released_manifest(release_path)

    assert manifest.evaluation_evidence == receipt
    assert manifest.evaluation_unavailable_reason is None
    preserved = candidate.with_name("modernbert-candidate.training_receipt.json")
    assert preserved.read_text(encoding="utf-8") == receipt
    assert not (candidate / "training_receipt.json").exists()
    assert not (release_path / "training_receipt.json").exists()
    assert {item.path.as_posix() for item in manifest.files} == {
        "config.json",
        "model.safetensors",
        "relation_inventory.json",
        "tokenizer.json",
    }


def test_modernbert_explicit_evidence_wins_over_receipt_without_deleting_it(tmp_path: Path) -> None:
    receipt = '{"run_id": "r1"}'
    candidate = _modernbert_candidate(tmp_path, receipt=receipt)
    release_path = prepare_and_promote_modernbert(
        candidate, tmp_path / "store", evaluation_evidence="explicit external evaluation"
    )
    manifest = _released_manifest(release_path)

    assert manifest.evaluation_evidence == "explicit external evaluation"
    assert candidate.with_name("modernbert-candidate.training_receipt.json").read_text(encoding="utf-8") == receipt


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
            compatibility_range=">=5,<6",
            source_model_identity="fixture/tiny",
            source_revision="a" * 40,
            licence="MIT",
            use_restrictions=(),
            roles={PurePosixPath("config.json"): "configuration"},
        )
