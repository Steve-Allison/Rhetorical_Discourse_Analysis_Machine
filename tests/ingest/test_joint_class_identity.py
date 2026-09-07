"""Repeated checkpoint label text does not erase distinct classifier positions."""

import math

from pydantic import ValidationError
import pytest

from rdam.ingest.contracts.inference import JointRelationNuclearityEvidence


def test_duplicate_labels_preserve_scores_and_selected_position() -> None:
    evidence = JointRelationNuclearityEvidence(
        labels=("Concession_SN", "Concession_SN"),
        log_probabilities=(math.log(0.25), math.log(0.75)),
        selected_class=1,
    )
    restored = JointRelationNuclearityEvidence.model_validate_json(evidence.model_dump_json())
    assert restored == evidence
    assert restored.selected_class == 1
    assert restored.log_probabilities == (math.log(0.25), math.log(0.75))


def test_duplicate_labels_do_not_excuse_wrong_selection() -> None:
    with pytest.raises(ValidationError, match="selection contradicts"):
        JointRelationNuclearityEvidence(
            labels=("Concession_SN", "Concession_SN"),
            log_probabilities=(math.log(0.25), math.log(0.75)),
            selected_class=0,
        )
