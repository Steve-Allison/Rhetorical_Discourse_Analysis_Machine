"""Isolated wheel runner fails closed before executing ambiguous candidates."""

from pathlib import Path
from typing import cast

import pytest

import tools.production_ingest.runner as runner
from tools.production_ingest.contracts import GoldSetManifest


def test_candidate_runner_requires_model_store_and_release_as_one_identity() -> None:
    with pytest.raises(ValueError, match="supplied together"):
        runner.run_candidate_preparation(
            wheel=Path("missing.whl"),
            manifest=cast(GoldSetManifest, object()),
            gold_root=Path("gold"),
            output_root=Path("output"),
            repository_root=Path.cwd(),
            model_store=Path("model-store"),
        )


def test_candidate_runner_rejects_nonexistent_wheel() -> None:
    with pytest.raises(FileNotFoundError, match="candidate wheel not found"):
        runner.run_candidate_preparation(
            wheel=Path("missing.whl"),
            manifest=cast(GoldSetManifest, object()),
            gold_root=Path("gold"),
            output_root=Path("output"),
            repository_root=Path.cwd(),
        )


@pytest.mark.parametrize("repetitions", [0, 3])
def test_candidate_runner_rejects_invalid_determinism_run_counts(repetitions: int) -> None:
    with pytest.raises(ValueError, match="repetitions|even"):
        runner.run_candidate_preparation(
            wheel=Path("missing.whl"),
            manifest=cast(GoldSetManifest, object()),
            gold_root=Path("gold"),
            output_root=Path("output"),
            repository_root=Path.cwd(),
            repetitions=repetitions,
        )


def test_baseline_runner_requires_full_immutable_commit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(runner, "_git", lambda *_args: "f" * 40)
    with pytest.raises(ValueError, match="full immutable Git revision"):
        runner.run_baseline_gold_analysis(
            repository_root=Path.cwd(),
            baseline_commit="main",
            manifest=cast(GoldSetManifest, object()),
            gold_root=Path("gold"),
            output_root=Path("output"),
            model_store=Path("model-store"),
            model_release_id="release-1",
        )


def test_runner_scripts_enforce_repository_and_offline_evaluation_boundaries() -> None:
    for script in (runner._CANDIDATE_SCRIPT, runner._BASELINE_ANALYSIS_SCRIPT):
        assert "repository onto sys.path" in script
        assert 'module_exists("workbench")' in script
        assert 'module_exists("tools.production_ingest")' in script
    assert "HF_HUB_OFFLINE" in runner.run_candidate_preparation.__code__.co_consts
    assert "unique_semantic_digests" in runner._CANDIDATE_SCRIPT
    assert "cache_statuses" in runner._CANDIDATE_SCRIPT


def test_runner_public_annotations_name_the_gold_authority() -> None:
    assert runner.run_candidate_preparation.__annotations__["manifest"] is GoldSetManifest
