"""Unit tests for offline probability calibration and temperature scaling."""

from pathlib import Path
import numpy as np

from workbench.evaluation.rst.calibration import (
    CalibrationSummary,
    TemperatureScaler,
    compute_calibration_error,
)


def test_compute_calibration_error_perfect():
    confidences = [0.1, 0.2, 0.8, 0.9]
    accuracies = [0, 0, 1, 1]
    summary = compute_calibration_error(confidences, accuracies, n_bins=5)
    assert isinstance(summary, CalibrationSummary)
    assert summary.sample_count == 4
    assert len(summary.bins) == 5
    assert summary.expected_calibration_error >= 0.0


def test_temperature_scaler_fit_and_predict(tmp_path: Path):
    np.random.seed(42)
    # Generate synthetic overconfident logits: 100 samples, 4 classes
    true_labels = np.random.randint(0, 4, size=100)
    logits = np.random.randn(100, 4) * 3.0
    for i, label in enumerate(true_labels):
        logits[i, label] += 2.0

    scaler = TemperatureScaler()
    fitted_t = scaler.fit(logits, true_labels)
    assert fitted_t > 0.0

    probs = scaler.predict_proba(logits)
    assert probs.shape == (100, 4)
    assert np.allclose(np.sum(probs, axis=1), 1.0)

    calib_file = tmp_path / "calibration.json"
    scaler.export(calib_file, ece_before=0.25, ece_after=0.08)
    assert calib_file.is_file()
    content = calib_file.read_text(encoding="utf-8")
    assert '"temperature"' in content
    assert '"calibrated": true' in content
