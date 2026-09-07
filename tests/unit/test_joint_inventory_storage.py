"""Indexed inventories preserve trained positions, including repeated label text."""

import pytest

from rdam.ingest.contracts.inference_storage import StoredJointEvidence


def test_duplicate_labels_keep_distinct_scores_and_selected_position() -> None:
    inventories = (("cause_NS", "cause_NS", "joint_NN"), ("elaboration_NS", "joint_NN"))
    stored = StoredJointEvidence(class_inventory=0, log_probabilities=(-2.0, -0.2, None), selected_class=1)
    native = stored.resolve(inventories)
    assert native.labels == ("cause_NS", "cause_NS", "joint_NN")
    assert native.selected_class == 1
    assert native.log_probabilities == (-2.0, -0.2, None)
    other = StoredJointEvidence(class_inventory=1, log_probabilities=(-0.1, -3.0), selected_class=0)
    assert other.resolve(inventories).labels == inventories[1]
    with pytest.raises(ValueError, match="absent"):
        stored.resolve(())
    with pytest.raises(ValueError, match="align"):
        stored.resolve((inventories[1],))
