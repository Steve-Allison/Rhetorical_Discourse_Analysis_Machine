"""Offline confidence calibration metrics and error estimators."""

from collections.abc import Sequence
from dataclasses import dataclass
import json
import hashlib
import math
from pathlib import Path
from numbers import Integral
from typing import Any

import numpy as np


class CalibrationFitError(ValueError):
    """The data has no identifiable finite positive temperature optimum."""


def _fit_temperature(logits: np.ndarray, labels: np.ndarray) -> float:
    """Solve the monotone NLL derivative in normalized inverse temperature.

    NLL is convex in inverse temperature: its second derivative is the mean
    softmax-weighted logit variance. Bracket its derivative zero from the data,
    then bisect to float64 square-root-epsilon relative precision. Zero and
    infinite temperature optima are explicit failures, not arbitrary cutoffs.
    """
    with np.errstate(over="raise", invalid="raise"):
        centered = logits - np.max(logits, axis=1, keepdims=True)
    scale = float(np.max(np.abs(centered)))
    if scale == 0.0:
        raise CalibrationFitError("temperature is unidentifiable for uniform logits")
    normalized = centered / scale
    selected = normalized[np.arange(len(labels)), labels]

    def derivative(inverse: float) -> float:
        weights = np.exp(normalized * inverse)
        probabilities = weights / np.sum(weights, axis=1, keepdims=True)
        return float(np.mean(np.sum(probabilities * normalized, axis=1) - selected))

    if derivative(0.0) >= 0.0:
        raise CalibrationFitError("NLL infimum requires infinite temperature")
    if np.all(selected == 0.0):
        raise CalibrationFitError("NLL infimum requires zero temperature")
    lower, upper = 0.0, 1.0
    while derivative(upper) < 0.0:
        lower, upper = upper, upper * 2.0
        if not math.isfinite(upper):
            raise CalibrationFitError("finite optimum is outside float64 representability")
    relative_precision = math.sqrt(np.finfo(np.float64).eps)
    while upper - lower > relative_precision * upper:
        middle = lower + (upper - lower) / 2.0
        if derivative(middle) < 0.0:
            lower = middle
        else:
            upper = middle
    temperature = scale / (lower + (upper - lower) / 2.0)
    if not math.isfinite(temperature) or temperature <= 0.0:
        raise CalibrationFitError("finite optimum is outside float64 representability")
    return temperature


@dataclass(frozen=True, slots=True)
class CalibrationBin:
    """A single bin in an expected calibration error histogram."""

    bin_index: int
    lower_bound: float
    upper_bound: float
    count: int
    mean_confidence: float | None
    accuracy: float | None
    error: float | None


@dataclass(frozen=True, slots=True)
class CalibrationSummary:
    """Expected Calibration Error summary metrics."""

    expected_calibration_error: float | None
    max_calibration_error: float | None
    sample_count: int
    bins: tuple[CalibrationBin, ...]


def compute_calibration_error(
    confidences: Sequence[float],
    accuracies: Sequence[bool | int],
    n_bins: int = 10,
) -> CalibrationSummary:
    """Compute Expected Calibration Error (ECE) and Maximum Calibration Error (MCE).

    Empty samples have unavailable errors. Empty bins have unavailable confidence,
    accuracy and error; their zero count excludes them from the weighted estimate.

    Args:
        confidences: Sequence of predicted probabilities in [0.0, 1.0].
        accuracies: Sequence of ground truth correctness indicators (True/1 or False/0).
        n_bins: Number of equal-width bins over [0.0, 1.0].
    """
    if len(confidences) != len(accuracies):
        raise ValueError(f"Length mismatch: {len(confidences)} confidences vs {len(accuracies)} accuracies")
    if isinstance(n_bins, bool) or not isinstance(n_bins, Integral) or n_bins < 1:
        raise ValueError(f"n_bins must be at least 1, got {n_bins}")
    for confidence in confidences:
        if isinstance(confidence, bool) or not math.isfinite(confidence) or not 0.0 <= confidence <= 1.0:
            raise ValueError("confidences must be finite probabilities within [0, 1]")
    for correct in accuracies:
        if not isinstance(correct, (Integral, np.bool_)) or correct not in (0, 1):
            raise ValueError("accuracies must be binary correctness indicators")

    total_samples = len(confidences)
    if total_samples == 0:
        return CalibrationSummary(
            expected_calibration_error=None,
            max_calibration_error=None,
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
            mean_conf = None
            acc = None
            err = None

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

    __slots__ = ("_temperature", "_fit_digest", "_fit_sample_count")

    _temperature: float
    _fit_digest: str | None
    _fit_sample_count: int

    def __init__(self, temperature: float = 1.0) -> None:
        self._fit_digest = None
        self._fit_sample_count = 0
        self.temperature = temperature

    @property
    def temperature(self) -> float:
        return self._temperature

    @temperature.setter
    def temperature(self, value: float) -> None:
        if isinstance(value, bool) or not math.isfinite(value) or value <= 0.0:
            raise ValueError(f"temperature must be finite and positive, got {value}")
        self._temperature = value
        self._fit_digest = None
        self._fit_sample_count = 0

    @staticmethod
    def _softmax(logits: np.ndarray, temp: float) -> np.ndarray:
        with np.errstate(over="raise", invalid="raise", divide="raise"):
            shifted = (logits - np.max(logits, axis=-1, keepdims=True)) / temp
        exp_vals = np.exp(shifted)
        return exp_vals / np.sum(exp_vals, axis=-1, keepdims=True)

    def fit(self, logits: Sequence[Sequence[float]] | np.ndarray, labels: Sequence[int] | np.ndarray) -> float:
        """Fit optimal temperature on validation logits and labels minimizing NLL."""
        logits_arr = np.asarray(logits, dtype=np.float64)
        raw_labels = np.asarray(labels)

        if logits_arr.ndim != 2:
            raise ValueError(f"logits must be 2D array [N, K], got shape {logits_arr.shape}")
        if raw_labels.ndim != 1 or len(raw_labels) != len(logits_arr):
            raise ValueError("labels must be 1D array with length matching logits")
        if not logits_arr.shape[0] or logits_arr.shape[1] < 2 or not np.all(np.isfinite(logits_arr)):
            raise ValueError("fitting requires nonempty finite logits with at least two classes")
        if not np.issubdtype(raw_labels.dtype, np.integer):
            raise ValueError("labels must be integer class indices")
        if np.any(raw_labels < 0) or np.any(raw_labels >= logits_arr.shape[1]):
            raise ValueError("label outside the class inventory")
        labels_arr = raw_labels.astype(np.int64)

        n_samples = len(labels_arr)

        self.temperature = _fit_temperature(logits_arr, labels_arr)
        encoded = json.dumps({"logits": logits_arr.tolist(), "labels": labels_arr.tolist()},
                             sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
        self._fit_digest = hashlib.sha256(encoded).hexdigest()
        self._fit_sample_count = n_samples
        return self.temperature

    def predict_proba(self, logits: Sequence[Sequence[float]] | np.ndarray) -> np.ndarray:
        """Return calibrated class probabilities."""
        logits_arr = np.asarray(logits, dtype=np.float64)
        if logits_arr.ndim != 2 or logits_arr.shape[1] < 2 or not np.all(np.isfinite(logits_arr)):
            raise ValueError("prediction requires finite 2D logits with at least two classes")
        return self._softmax(logits_arr, self.temperature)

    def export(
        self,
        path: Path | str,
        ece_before: float | None = None,
        ece_after: float | None = None,
        extra_metadata: dict[str, Any] | None = None,
    ) -> None:
        """Export parameters and fitting provenance.

        ``calibrated`` records that these parameters were fitted, not evidence of
        improved held-out reliability. ECE values are caller-supplied measurements;
        the fitting-data digest identifies normalized logits and labels, not a
        corpus split or a guarantee against training/test overlap.
        """
        reserved = {"schema_version", "temperature", "calibrated", "ece_before", "ece_after",
                    "fit_data_digest", "fit_sample_count"}
        if extra_metadata is not None and reserved.intersection(extra_metadata):
            raise ValueError("extra metadata cannot override calibration fields")
        for value in (ece_before, ece_after):
            if value is not None and (not math.isfinite(value) or not 0.0 <= value <= 1.0):
                raise ValueError("ECE must be finite and within [0, 1]")
        data = {
            "schema_version": "isanlp_rst_calibration/v2",
            "temperature": self.temperature,
            "calibrated": self._fit_digest is not None,
            "fit_data_digest": self._fit_digest,
            "fit_sample_count": self._fit_sample_count,
            "ece_before": ece_before,
            "ece_after": ece_after,
            **(extra_metadata or {}),
        }
        Path(path).write_text(json.dumps(data, indent=2, sort_keys=True, allow_nan=False), encoding="utf-8")
