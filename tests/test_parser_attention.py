"""Regression tests for shared DMRST and UniRST attention/classifier mathematics."""

from collections.abc import Callable
from typing import Any

import pytest
import torch
from torch import Tensor, nn

from isanlp_rst.dmrst_parser.src.parser.modules import (
    DefaultPlusBiMPMClassifier as DmrstDefaultPlusBiMPMClassifier,
)
from isanlp_rst.dmrst_parser.src.parser.modules import PointerAtten as DmrstPointerAtten
from isanlp_rst.universal_parser.src.parser.modules import (
    DefaultPlusBiMPMClassifier as UnirstDefaultPlusBiMPMClassifier,
)
from isanlp_rst.universal_parser.src.parser.modules import PointerAtten as UnirstPointerAtten


_POINTER_CLASSES = (DmrstPointerAtten, UnirstPointerAtten)
_COMBINED_CLASSES = (DmrstDefaultPlusBiMPMClassifier, UnirstDefaultPlusBiMPMClassifier)


@pytest.mark.parametrize("pointer_class", _POINTER_CLASSES)
@pytest.mark.parametrize("attention_model", ("Dotproduct", "Biaffine"))
def test_pointer_attention_preserves_matmul_scores(
    pointer_class: Callable[[str, int], Any], attention_model: str
) -> None:
    """The MPS-safe elementwise reduction remains mathematically equivalent to GEMV."""

    torch.manual_seed(7)
    encoder_outputs = torch.randn(5, 4)
    decoder_output = torch.randn(4)
    pointer = pointer_class(attention_model, 4)

    if attention_model == "Dotproduct":
        expected_scores = torch.matmul(encoder_outputs, decoder_output).unsqueeze(0)
        softmax_dimension = 1
    else:
        projected = pointer.weight1(encoder_outputs)
        expected_scores = (
            torch.matmul(projected, decoder_output).unsqueeze(1) + pointer.weight2(encoder_outputs)
        ).permute(1, 0)
        softmax_dimension = 0

    weights, log_weights = pointer(encoder_outputs, decoder_output)

    torch.testing.assert_close(weights, torch.softmax(expected_scores, dim=softmax_dimension))
    torch.testing.assert_close(log_weights, torch.log_softmax(expected_scores + 1e-6, dim=softmax_dimension))


class _RecordingDefaultEncoder(nn.Module):
    """Capture the representations passed by the combined classifier."""

    def __init__(self) -> None:
        super().__init__()
        self.input_size = 2
        self.hidden_size = 2
        self._cuda_device = torch.device("cpu")
        self.labelspace_left = nn.Linear(2, 2, bias=False)
        self.labelspace_right = nn.Linear(2, 2, bias=False)
        self.recorded: tuple[Tensor, Tensor] | None = None

    def forward(self, left: Tensor, right: Tensor) -> tuple[Tensor, Tensor]:
        self.recorded = (left, right)
        return left, right


class _DistinctBiMpmEncoder:
    hidden_size = 2

    def encode(self, _left_edus: Tensor, _right_edus: Tensor) -> tuple[Tensor, Tensor, Tensor]:
        left = torch.tensor([[[1.0, 2.0]], [[3.0, 4.0]]])
        right = torch.tensor([[[5.0, 6.0]], [[7.0, 8.0]]])
        lengths = torch.tensor([[9.0, 10.0]])
        return left, right, lengths


@pytest.mark.parametrize("combined_class", _COMBINED_CLASSES)
def test_combined_classifier_uses_distinct_right_representation(combined_class: type[nn.Module]) -> None:
    """The right DU must use right BiMPM features and its own length."""

    default_encoder = _RecordingDefaultEncoder()
    classifier: Any = combined_class(default_encoder, _DistinctBiMpmEncoder())
    left_du = torch.tensor([[11.0, 12.0]])
    right_du = torch.tensor([[13.0, 14.0]])

    classifier(torch.empty(0), torch.empty(0), left_du, right_du)

    assert default_encoder.recorded is not None
    recorded_left, recorded_right = default_encoder.recorded
    torch.testing.assert_close(recorded_left, torch.tensor([[1.0, 2.0, 3.0, 4.0, 9.0, 11.0, 12.0]]))
    torch.testing.assert_close(recorded_right, torch.tensor([[5.0, 6.0, 7.0, 8.0, 10.0, 13.0, 14.0]]))
