"""Hand-computed likelihood, Brier and selective-error checks."""

import math

import pytest

from workbench.evaluation.rst.conditional_calibration import calibration_metrics


def test_metrics_match_hand_computed_scores_and_keep_coverage_denominators() -> None:
    logits = [[math.log(0.8), math.log(0.2)], [math.log(0.25), math.log(0.75)]]
    result = calibration_metrics(logits, [0, 0], temperature=1.0, bins=2)
    assert result["negative_log_likelihood"] == pytest.approx((-math.log(0.8) - math.log(0.25)) / 2)
    assert result["multiclass_brier"] == pytest.approx((0.08 + 1.125) / 2)
    assert result["reliability"]["expected_calibration_error"] == pytest.approx(0.275)
    assert [(row["retained"], row["errors"]) for row in result["error_coverage"]] == [(1, 0), (2, 1)]
    shifted = calibration_metrics([[value + 1000 for value in row] for row in logits], [0, 0], temperature=1.0, bins=2)
    assert shifted["negative_log_likelihood"] == pytest.approx(result["negative_log_likelihood"])


def test_metrics_reject_invalid_target_class() -> None:
    with pytest.raises(ValueError, match="valid nonempty"):
        calibration_metrics([[0.0, -1.0]], [2], temperature=1.0, bins=2)
