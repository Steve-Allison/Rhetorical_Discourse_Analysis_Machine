"""Comparison uncertainty preserves document pairing and micro denominators."""

import pytest

from workbench.evaluation.rst.comparison import Counts, paired_f1


def test_identical_predictions_have_zero_paired_difference() -> None:
    counts = (Counts(1, 1, 1), Counts(9, 9, 0))
    result = paired_f1(counts, counts, confidence=0.95, resamples=100, seed=0)
    assert result["reference_f1"] == 0.1
    assert result["candidate_minus_reference"] == 0.0
    assert result["paired_document_percentile_interval"] == {"lower": 0.0, "upper": 0.0}


def test_constant_improvement_preserves_paired_interval_and_predicted_denominator() -> None:
    result = paired_f1((Counts(4, 6, 2),) * 3, (Counts(4, 4, 3),) * 3,
                       confidence=0.95, resamples=100, seed=0)
    assert result["candidate_minus_reference"] == pytest.approx(0.35)
    assert result["paired_document_percentile_interval"]["lower"] == pytest.approx(0.35)
    assert result["paired_document_percentile_interval"]["upper"] == pytest.approx(0.35)


def test_pairing_rejects_changed_gold_and_unavailable_denominators() -> None:
    with pytest.raises(ValueError, match="identical gold"):
        paired_f1((Counts(4, 4, 2),), (Counts(5, 4, 2),), confidence=0.95, resamples=100, seed=0)
    with pytest.raises(ValueError, match="undefined"):
        paired_f1((Counts(0, 0, 0),), (Counts(0, 0, 0),), confidence=0.95, resamples=100, seed=0)
