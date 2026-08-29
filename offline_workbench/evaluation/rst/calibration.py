"""Offline confidence calibration metrics and error estimators."""

from collections.abc import Sequence
from dataclasses import dataclass
import json
import math
from pathlib import Path
from typing import Any

import numpy as np


def _golden_section_search_1d(
    func: Any,
    a: float = 0.05,
    b: float = 10.0,
    tol: float = 1e-5,
    max_iter: int = 100,
) -> float:
    """Minimize a unimodal 1D scalar function over [a, b] using golden-section search."""
    invphi = (math.sqrt(5) - 1.0) / 2.0
    invphi2 = (3.0 - math.sqrt(5)) / 2.0

    h = b - a
    if h <= tol:
        return (a + b) / 2.0

    c = a + invphi2 * h
    d = a + invphi * h
    yc = func(c)
    yd = func(d)

    for _ in range(max_iter):
        if h * invphi < tol:
            break
        if yc < yd:
            b = d
            d = c
            yd = yc
            h = invphi * h
            c = a + invphi2 * h
            yc = func(c)
        else:
            a = c
            c = d
            yc = yd
            h = invphi * h
            d = a + invphi * h
            yd = func(d)

    return (a + b) / 2.0


@dataclass(frozen=True, slots=True)
class CalibrationBin:
    """A single bin in an expected calibration error histogram."""

    bin_index: int
    lower_bound: float
    upper_bound: float
    count: int
    mean_confidence: float
    accuracy: float
    error: float


@dataclass(frozen=True, slots=True)
class CalibrationSummary:
    """Expected Calibration Error summary metrics."""

    expected_calibration_error: float
    max_calibration_error: float
    sample_count: int
    bins: tuple[CalibrationBin, ...]


def compute_calibration_error(
    confidences: Sequence[float],
    accuracies: Sequence[bool | int],
    n_bins: int = 10,
) -> CalibrationSummary:
    """Compute Expected Calibration Error (ECE) and Maximum Calibration Error (MCE).

    Args:
        confidences: Sequence of predicted probabilities in [0.0, 1.0].
        accuracies: Sequence of ground truth correctness indicators (True/1 or False/0).
        n_bins: Number of equal-width bins over [0.0, 1.0].
    """
    if len(confidences) != len(accuracies):
        raise ValueError(f"Length mismatch: {len(confidences)} confidences vs {len(accuracies)} accuracies")
    if n_bins < 1:
        raise ValueError(f"n_bins must be at least 1, got {n_bins}")

    total_samples = len(confidences)
    if total_samples == 0:
        return CalibrationSummary(
            expected_calibration_error=0.0,
            max_calibration_error=0.0,
            sample_count=0,
            bins=(),
        )

    bin_width = 1.0 / n_bins
    bin_records: list[CalibrationBin] = []

    weighted_ece = 0.0
    max_mce = 0.0

    for i in range(n_bins):
        lower = i * bin_width
        upper = (i + 1) * bin_width

        # In last bin, include right edge 1.0
        if i == n_bins - 1:
            indices = [idx for idx, conf in enumerate(confidences) if lower <= conf <= upper]
        else:
            indices = [idx for idx, conf in enumerate(confidences) if lower <= conf < upper]

        bin_count = len(indices)
        if bin_count > 0:
            mean_conf = sum(confidences[idx] for idx in indices) / bin_count
            acc = sum(1 for idx in indices if bool(accuracies[idx])) / bin_count
            err = math.fabs(acc - mean_conf)
            weighted_ece += (bin_count / total_samples) * err
            if err > max_mce:
                max_mce = err
        else:
            mean_conf = (lower + upper) / 2.0
            acc = 0.0
            err = 0.0

        bin_records.append(
            CalibrationBin(
                bin_index=i,
                lower_bound=lower,
                upper_bound=upper,
                count=bin_count,
                mean_confidence=mean_conf,
                accuracy=acc,
                error=err,
            )
        )

    return CalibrationSummary(
        expected_calibration_error=weighted_ece,
        max_calibration_error=max_mce,
        sample_count=total_samples,
        bins=tuple(bin_records),
    )


class TemperatureScaler:
    """Post-hoc temperature scaling calibrator for multi-class relation logits."""

    __slots__ = ("temperature",)

    temperature: float

    def __init__(self, temperature: float = 1.0) -> None:
        if temperature <= 0.0:
            raise ValueError(f"temperature must be positive, got {temperature}")
        self.temperature = temperature

    @staticmethod
    def _softmax(logits: np.ndarray, temp: float) -> np.ndarray:
        scaled = logits / temp
        shifted = scaled - np.max(scaled, axis=-1, keepdims=True)
        exp_vals = np.exp(shifted)
        return exp_vals / np.sum(exp_vals, axis=-1, keepdims=True)

    def fit(self, logits: Sequence[Sequence[float]] | np.ndarray, labels: Sequence[int] | np.ndarray) -> float:
        """Fit optimal temperature on validation logits and labels minimizing NLL."""
        logits_arr = np.asarray(logits, dtype=np.float64)
        labels_arr = np.asarray(labels, dtype=np.int64)

        if logits_arr.ndim != 2:
            raise ValueError(f"logits must be 2D array [N, K], got shape {logits_arr.shape}")
        if labels_arr.ndim != 1 or len(labels_arr) != len(logits_arr):
            raise ValueError("labels must be 1D array with length matching logits")

        n_samples = len(labels_arr)

        def _nll(temp_val: float) -> float:
            probs = self._softmax(logits_arr, temp_val)
            eps = 1e-15
            clipped_probs = np.clip(probs, eps, 1.0 - eps)
            correct_probs = clipped_probs[np.arange(n_samples), labels_arr]
            return float(-np.mean(np.log(correct_probs)))

        optimal_t = _golden_section_search_1d(_nll, a=0.05, b=10.0)
        self.temperature = optimal_t
        return self.temperature

    def predict_proba(self, logits: Sequence[Sequence[float]] | np.ndarray) -> np.ndarray:
        """Return calibrated class probabilities."""
        logits_arr = np.asarray(logits, dtype=np.float64)
        return self._softmax(logits_arr, self.temperature)

    def export(
        self,
        path: Path | str,
        ece_before: float | None = None,
        ece_after: float | None = None,
        extra_metadata: dict[str, Any] | None = None,
    ) -> None:
        """Export calibration parameters to JSON."""
        data = {
            "schema_version": "isanlp_rst_calibration/v1",
            "temperature": self.temperature,
            "calibrated": True,
            "ece_before": ece_before,
            "ece_after": ece_after,
            **(extra_metadata or {}),
        }
        Path(path).write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
