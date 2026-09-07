"""Exercise actual transition decoding with controlled encoder and scorer inputs."""

from typing import Any

import pytest
import torch
from torch import Tensor, nn

from rdam.rst.inference_evidence import NetworkStructureDecision
from rdam.rst.universal_parser.src.parser.parsing_net_bottom_up import ParsingNetBottomUp


class _Encoder(nn.Module):
    def forward(self, *args: Any, **kwargs: Any) -> tuple[Tensor, None, None, list[list[int]], None]:
        return torch.tensor([[[1.0, 0.0], [0.0, 2.0], [3.0, 1.0]]]), None, None, [[0, 1, 2]], None


class _RelationClassifier(nn.Module):
    def forward(self, left: Tensor, right: Tensor) -> tuple[Tensor, Tensor]:
        logits = torch.cat((left.sum(dim=-1, keepdim=True), right.sum(dim=-1, keepdim=True)), dim=-1)
        return logits.softmax(dim=-1), logits.log_softmax(dim=-1)


@pytest.mark.parametrize("preferred_action", (0, 1))
def test_bottom_up_records_forced_actions_and_each_transition_once(
    preferred_action: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The encoder is controlled so the real decoding loop can be checked without
    # downloading or misrepresenting a trained bottom-up checkpoint.
    model = ParsingNetBottomUp.__new__(ParsingNetBottomUp)
    nn.Module.__init__(model)
    model.hidden_size = 2
    monkeypatch.setattr(model, "_cuda_device", torch.device("cpu"), raising=False)
    monkeypatch.setattr(model, "encoder", _Encoder(), raising=False)
    scorer = nn.Linear(6, 2)
    with torch.no_grad():
        scorer.weight.zero_()
        scorer.bias.zero_()
        scorer.bias[preferred_action] = 2.0
    model.action_scorer = nn.Sequential(scorer)
    model.dataset2classifier = [0]
    model.dataset_masks = None
    model.relation_tables = [["elaboration_NS", "joint_NN"]]
    model.label_classifiers = nn.ModuleList([_RelationClassifier()])
    captured: list[list[NetworkStructureDecision]] = []
    with torch.inference_mode():
        ordinary = model.testing_loss([[0, 1, 2]], None, None, None, [[0, 1, 2]], [[]], [[]], True, False, [0])
        observed = model.testing_loss(
            [[0, 1, 2]],
            None,
            None,
            None,
            [[0, 1, 2]],
            [[]],
            [[]],
            True,
            False,
            [0],
            decision_traces=captured,
        )
    assert ordinary == observed
    (decisions,) = captured
    assert len(decisions) == 2
    assert all(decision.split_log_probabilities is None for decision in decisions)
    transitions = [transition for decision in decisions for transition in decision.transitions]
    assert len(transitions) == 5
    assert sum(transition.applied_action == 0 for transition in transitions) == 3
    assert sum(transition.applied_action == 1 for transition in transitions) == 2
    assert all(transition.selected_action == preferred_action for transition in transitions)
    assert any(transition.applied_action != transition.selected_action for transition in transitions)
    assert transitions[0].stack_spans == ()
    assert transitions[0].next_edu == 0
    assert (decisions[-1].start, decisions[-1].end) == (0, 2)
    assert [decision.selected_class for decision in decisions] == observed[3][1]
    for transition in transitions:
        assert transition.action_logits[preferred_action] == 2.0
        assert transition.action_logits[1 - preferred_action] == 0.0
