"""Adversarial and numerical edge-case tests for calibration math.

Tests temperature scaling, expected calibration error (ECE), and reliability
diagram calculations under pathological data regimes:
- Extreme logit scales (overflow/underflow resistance)
- Homogeneous labels (all-positive or all-negative ground truth)
- Uniformly uninformative logits (all zeros)
- Boundary probability bins (0.0 and 1.0 extremes)
"""

import math
import numpy as np

from workbench.evaluation.rst.calibration import (
    CalibrationSummary,
    TemperatureScaler,
    compute_calibration_error,
)


def test_temperature_scaler_handles_extreme_overflow_underflow_logits() -> None:
    # Logits spanning from -10,000 to +10,000 in 2D array [N, 2]
    logits = np.array(
        [
            [-10000.0, 10000.0],
            [-500.0, 500.0],
            [0.0, 0.0],
            [500.0, -500.0],
            [10000.0, -10000.0],
        ],
        dtype=np.float64,
    )
    labels = np.array([1, 1, 0, 0, 0], dtype=np.int64)

    scaler = TemperatureScaler(temperature=1.0)
    scaler.fit(logits, labels)

    # Learned temperature must be strictly positive and finite
    assert math.isfinite(scaler.temperature)
    assert scaler.temperature > 0.0

    # Calibrated probabilities must be strictly bounded in [0, 1] without NaNs or Infs
    calibrated = scaler.predict_proba(logits)
    assert np.all(np.isfinite(calibrated))
    assert np.all(calibrated >= 0.0)
    assert np.all(calibrated <= 1.0)


def test_temperature_scaler_handles_uniform_zero_logits() -> None:
    # Flat / uninformative classifier output in [100, 2]
    logits = np.zeros((100, 2), dtype=np.float64)
    labels = np.array([1 if i % 2 == 0 else 0 for i in range(100)], dtype=np.int64)

    scaler = TemperatureScaler(temperature=1.0)
    scaler.fit(logits, labels)

    assert math.isfinite(scaler.temperature)
    calibrated = scaler.predict_proba(logits)
    # Probabilities must all be exactly 0.5
    assert np.allclose(calibrated, 0.5)


def test_temperature_scaler_homogeneous_labels_does_not_crash() -> None:
    # All labels are 0 (no positive secondary edges in small batch) in [50, 2]
    logits = np.random.RandomState(42).randn(50, 2)
    labels = np.zeros(50, dtype=np.int64)

    scaler = TemperatureScaler()
    scaler.fit(logits, labels)

    assert math.isfinite(scaler.temperature)
    assert scaler.temperature > 0.0


def test_compute_calibration_error_boundary_cases() -> None:
    # Perfect calibration: probabilities equal ground truth exactly
    probs = [0.1, 0.2, 0.8, 0.9]
    labels = [0, 0, 1, 1]

    summary = compute_calibration_error(probs, labels, n_bins=10)
    assert isinstance(summary, CalibrationSummary)
    assert math.isfinite(summary.expected_calibration_error)
    assert 0.0 <= summary.expected_calibration_error <= 1.0
    assert summary.sample_count == 4
    assert len(summary.bins) == 10

    # Completely wrong calibration
    wrong_probs = [0.99, 0.99, 0.01, 0.01]
    wrong_labels = [0, 0, 1, 1]
    wrong_summary = compute_calibration_error(wrong_probs, wrong_labels, n_bins=10)
    assert wrong_summary.expected_calibration_error > summary.expected_calibration_error
    assert wrong_summary.expected_calibration_error > 0.50


def test_calibration_summary_handles_empty_inputs() -> None:
    summary = compute_calibration_error([], [], n_bins=10)
    assert summary.sample_count == 0
    assert summary.expected_calibration_error == 0.0
    assert summary.bins == ()
