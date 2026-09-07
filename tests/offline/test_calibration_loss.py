"""Temperature fitting must not hide confidently wrong predictions by clipping."""

import math
import numpy as np
import pytest

from workbench.evaluation.rst.calibration import CalibrationFitError, TemperatureScaler


def test_extreme_error_is_not_clipped_out_of_fitting_objective() -> None:
    # The wrong example costs roughly 1000/T; the correct one costs at most log(2).
    # The unrestricted optimum is infinite temperature, not a finite cutoff.
    # Clipping the wrong probability to epsilon makes its cost constant, reversing
    # the optimizer's preference and incorrectly selecting the lower end instead.
    scaler = TemperatureScaler()
    with pytest.raises(CalibrationFitError, match="infinite temperature"):
        scaler.fit([[1000.0, 0.0], [1.0, 0.0]], [1, 0])


@pytest.mark.parametrize("gap", [0.001, 2.0, 1000.0])
def test_analytic_optimum_is_not_limited_by_temperature_bounds(gap: float) -> None:
    # Three correct and one wrong example: optimal predicted probability is 3/4,
    # hence exp(gap/T) = 3 and T = gap/log(3).
    scaler = TemperatureScaler()
    fitted = scaler.fit([[gap, 0.0]] * 4, [0, 0, 0, 1])
    assert fitted == pytest.approx(gap / math.log(3), rel=2e-8)


def test_separable_data_has_no_finite_optimum() -> None:
    with pytest.raises(CalibrationFitError, match="zero temperature"):
        TemperatureScaler().fit([[1.0, 0.0]], [0])


def test_common_large_logit_offset_does_not_overflow_scaling() -> None:
    scaler = TemperatureScaler(0.05)
    probabilities = scaler.predict_proba([[1e308, 1e308]])
    np.testing.assert_array_equal(probabilities, [[0.5, 0.5]])


@pytest.mark.parametrize("logits", [
    np.array([0.0, 1.0]),
    np.array([[float("nan"), 0.0]]),
    np.array([[float("inf"), 0.0]]),
    np.empty((1, 0)),
])
def test_invalid_prediction_logits_rejected(logits: np.ndarray) -> None:
    with pytest.raises(ValueError, match="finite 2D logits"):
        TemperatureScaler().predict_proba(logits)
