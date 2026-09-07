"""Invalid observations cannot improve a reported calibration error."""

import pytest

from workbench.evaluation.rst.calibration import compute_calibration_error


@pytest.mark.parametrize("confidence", [float("nan"), float("inf"), -0.1, 1.1, True])
def test_invalid_probability_rejected(confidence: float) -> None:
    with pytest.raises(ValueError, match="finite probabilities"):
        compute_calibration_error([confidence], [True])


@pytest.mark.parametrize("correct", [-1, 2])
def test_nonbinary_correctness_rejected(correct: int) -> None:
    with pytest.raises(ValueError, match="binary correctness"):
        compute_calibration_error([0.5], [correct])


def test_empty_bins_do_not_invent_observations() -> None:
    result = compute_calibration_error([0.0, 1.0], [False, True], n_bins=3)
    assert result.expected_calibration_error == 0.0
    assert sum(item.count for item in result.bins) == result.sample_count == 2
    empty = result.bins[1]
    assert empty.count == 0
    assert empty.mean_confidence is None
    assert empty.accuracy is None
    assert empty.error is None


def test_no_observations_means_unavailable_error() -> None:
    result = compute_calibration_error([], [])
    assert result.sample_count == 0
    assert result.expected_calibration_error is None
    assert result.max_calibration_error is None


def test_boolean_bin_count_rejected() -> None:
    with pytest.raises(ValueError, match="n_bins"):
        compute_calibration_error([0.5], [True], n_bins=True)
