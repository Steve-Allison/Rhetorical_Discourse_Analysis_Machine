"""Confidence calibration metrics and error estimators."""

from collections.abc import Sequence
from dataclasses import dataclass
import math


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
