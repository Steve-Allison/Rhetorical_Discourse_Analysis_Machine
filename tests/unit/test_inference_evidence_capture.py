"""Evidence snapshots preserve network scores rather than reconstructing them."""

from dataclasses import replace

import pytest
import torch

from rdam.rst.inference_evidence import NetworkStructureDecision, capture_structure_decision


def test_capture_preserves_joint_scores_mask_and_independent_snapshot() -> None:
    logits = torch.tensor([[0.2, -0.4, float("-inf"), 1.7]], dtype=torch.float64)
    log_probabilities = logits.log_softmax(dim=-1)
    splits = torch.tensor([[0.7, -0.2]], dtype=torch.float64).log_softmax(dim=-1)
    captured: list[NetworkStructureDecision] = []
    capture_structure_decision(
        captured,
        start=2,
        end=4,
        split=2,
        joint_labels=("cause_NS", "cause_SN", "joint_NN", "elaboration_NS"),
        selected_class=3,
        joint_log_probabilities=log_probabilities,
        split_log_probabilities=splits,
    )
    (decision,) = captured
    assert decision.joint_log_probabilities == tuple(float(value) for value in log_probabilities[0].unbind())
    assert decision.split_log_probabilities == tuple(float(value) for value in splits[0].unbind())
    log_probabilities.zero_()
    splits.zero_()
    assert decision.joint_log_probabilities[2] == float("-inf")
    assert decision.joint_log_probabilities[3] < 0
    assert decision.split_log_probabilities is not None and decision.split_log_probabilities[0] < 0
    with pytest.raises(ValueError, match="contradicts"):
        replace(decision, selected_class=0)
    with pytest.raises(ValueError, match="masked"):
        replace(decision, selected_class=2)
    with pytest.raises(ValueError, match="contradicts"):
        replace(decision, split=3)
    with pytest.raises(ValueError, match="forced split"):
        replace(decision, split_log_probabilities=None)


def test_two_edu_split_is_explicitly_forced() -> None:
    scores = torch.tensor([[2.0, -1.0]], dtype=torch.float64).log_softmax(dim=-1)
    captured: list[NetworkStructureDecision] = []
    capture_structure_decision(
        captured,
        start=4,
        end=5,
        split=4,
        joint_labels=("elaboration_NS", "joint_NN"),
        selected_class=0,
        joint_log_probabilities=scores,
    )
    assert captured[0].split_log_probabilities is None
    assert captured[0].joint_log_probabilities == tuple(float(value) for value in scores[0].unbind())
