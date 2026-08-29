"""Deterministic dev-only temperature and edge-threshold calibration."""

import hashlib
import json
import math

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, model_validator


class TemperatureCalibration(BaseModel):
    """One reproducible scalar calibration fitted only on development labels."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    temperature: float = Field(gt=0.0)
    nll_before: float = Field(ge=0.0)
    nll_after: float = Field(ge=0.0)
    example_count: int = Field(gt=0)
    calibration_sha256: str = ""

    @model_validator(mode="after")
    def validate_calibration(self) -> "TemperatureCalibration":
        if self.nll_after > self.nll_before + 1e-12:
            raise ValueError("temperature calibration cannot increase fitted development NLL")
        encoded = json.dumps(
            self.model_dump(mode="json", exclude={"calibration_sha256"}),
            separators=(",", ":"),
            sort_keys=True,
        ).encode()
        expected = hashlib.sha256(encoded).hexdigest()
        if self.calibration_sha256 and self.calibration_sha256 != expected:
            raise ValueError("temperature calibration hash does not match canonical content")
        object.__setattr__(self, "calibration_sha256", expected)
        return self


def _binary_nll(logits: np.ndarray, targets: np.ndarray, temperature: float) -> float:
    scaled = logits / temperature
    losses = np.maximum(scaled, 0.0) - scaled * targets + np.log1p(np.exp(-np.abs(scaled)))
    return float(np.mean(losses))


def fit_temperature(
    probabilities: np.ndarray,
    targets: np.ndarray,
    *,
    iterations: int = 96,
) -> TemperatureCalibration:
    """Fit a positive scalar by deterministic golden-section search in log space."""

    if probabilities.ndim != 1 or targets.ndim != 1 or len(probabilities) != len(targets):
        raise ValueError("temperature inputs must be aligned one-dimensional arrays")
    if len(probabilities) == 0:
        raise ValueError("temperature calibration requires examples")
    if iterations < 32:
        raise ValueError("temperature search requires at least 32 iterations")
    if not np.all(np.isfinite(probabilities)) or np.any((probabilities < 0.0) | (probabilities > 1.0)):
        raise ValueError("temperature probabilities must be finite values in [0, 1]")
    if not np.all(np.isin(targets, (0.0, 1.0))):
        raise ValueError("temperature targets must be binary")
    clipped = np.clip(probabilities.astype(np.float64), 1e-7, 1.0 - 1e-7)
    logits = np.log(clipped) - np.log1p(-clipped)
    binary_targets = targets.astype(np.float64)
    left = -4.0
    right = 4.0
    ratio = (math.sqrt(5.0) - 1.0) / 2.0
    middle_left = right - ratio * (right - left)
    middle_right = left + ratio * (right - left)
    loss_left = _binary_nll(logits, binary_targets, math.exp(middle_left))
    loss_right = _binary_nll(logits, binary_targets, math.exp(middle_right))
    for _ in range(iterations):
        if loss_left <= loss_right:
            right = middle_right
            middle_right = middle_left
            loss_right = loss_left
            middle_left = right - ratio * (right - left)
            loss_left = _binary_nll(logits, binary_targets, math.exp(middle_left))
        else:
            left = middle_left
            middle_left = middle_right
            loss_left = loss_right
            middle_right = left + ratio * (right - left)
            loss_right = _binary_nll(logits, binary_targets, math.exp(middle_right))
    temperature = math.exp((left + right) / 2.0)
    before = _binary_nll(logits, binary_targets, 1.0)
    after = _binary_nll(logits, binary_targets, temperature)
    if after > before:
        temperature = 1.0
        after = before
    return TemperatureCalibration(
        temperature=temperature,
        nll_before=before,
        nll_after=after,
        example_count=len(probabilities),
    )


def apply_temperature(probabilities: np.ndarray, temperature: float) -> np.ndarray:
    """Apply a fitted scalar without changing candidate ordering."""

    if temperature <= 0.0:
        raise ValueError("temperature must be positive")
    clipped = np.clip(probabilities.astype(np.float64), 1e-7, 1.0 - 1e-7)
    logits = (np.log(clipped) - np.log1p(-clipped)) / temperature
    return 1.0 / (1.0 + np.exp(-logits))


def canonical_threshold_grid() -> tuple[float, ...]:
    """Frozen development threshold grid, including the neutral 0.5 point."""

    return tuple(index / 100.0 for index in range(5, 100, 5))


__all__ = [
    "TemperatureCalibration",
    "apply_temperature",
    "canonical_threshold_grid",
    "fit_temperature",
]
