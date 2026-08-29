"""Fail-closed corpus and training completion guard tests."""

from pathlib import Path

import pytest
from safetensors.torch import save_file
import torch

from scripts.train_erst_scorer import (
    epoch_improves,
    require_checkpoint,
    require_positive_training_steps,
)


def test_zero_training_steps_are_an_error() -> None:
    with pytest.raises(ValueError, match="at least one"):
        require_positive_training_steps(0)
    with pytest.raises(ValueError, match="at least one"):
        require_positive_training_steps(-1)
    require_positive_training_steps(1)


def test_first_finite_epoch_always_establishes_a_checkpoint_metric() -> None:
    assert epoch_improves(0.0, None)
    assert epoch_improves(0.1, 0.0)
    assert not epoch_improves(0.1, 0.1)
    with pytest.raises(ValueError, match="finite"):
        epoch_improves(float("nan"), None)


def test_absent_or_empty_checkpoint_is_an_error(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="safetensors"):
        require_checkpoint(tmp_path / "model.pt")

    checkpoint = tmp_path / "training_state.safetensors"
    with pytest.raises(FileNotFoundError, match="checkpoint"):
        require_checkpoint(checkpoint)
    checkpoint.touch()
    with pytest.raises(FileNotFoundError, match="checkpoint"):
        require_checkpoint(checkpoint)
    checkpoint.unlink()
    save_file({"weight": torch.ones(1)}, checkpoint)
    require_checkpoint(checkpoint)

    invalid = tmp_path / "invalid.safetensors"
    invalid.write_bytes(b"not-safetensors")
    with pytest.raises(ValueError, match="valid safetensors"):
        require_checkpoint(invalid)
