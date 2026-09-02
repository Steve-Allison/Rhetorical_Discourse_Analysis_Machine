"""Exact lexical-boundary tests for padded and unpadded fast-tokenizer batches."""

import pytest
import torch
from torch import nn

from rdam.rst.erst.neural_scorer import BoundaryAwareSpanEncoder


def _encoder() -> BoundaryAwareSpanEncoder:
    encoder = BoundaryAwareSpanEncoder(hidden_size=1, proj_dim=1)
    encoder.proj = nn.Sequential(nn.Identity())
    encoder.attn_pool.query.weight.data.zero_()
    encoder.eval()
    return encoder


def test_padding_and_special_tokens_never_become_lexical_boundaries() -> None:
    encoder = _encoder()
    padded_states = torch.tensor([[[100.0], [1.0], [3.0], [200.0], [300.0], [400.0]]])
    padded = encoder(
        padded_states,
        attention_mask=torch.tensor([[1, 1, 1, 1, 0, 0]]),
        special_tokens_mask=torch.tensor([[1, 0, 0, 1, 1, 1]]),
        offset_mapping=torch.tensor([[[0, 0], [0, 1], [2, 3], [0, 0], [0, 0], [0, 0]]]),
    )
    unpadded = encoder(
        padded_states[:, :4],
        attention_mask=torch.tensor([[1, 1, 1, 1]]),
        special_tokens_mask=torch.tensor([[1, 0, 0, 1]]),
        offset_mapping=torch.tensor([[[0, 0], [0, 1], [2, 3], [0, 0]]]),
    )
    expected = torch.tensor([[1.0, 3.0, 2.0]])
    assert torch.equal(padded, expected)
    assert torch.equal(unpadded, expected)


def test_empty_lexical_span_fails_instead_of_selecting_sep_or_pad() -> None:
    encoder = _encoder()
    with pytest.raises(ValueError, match="lexical token"):
        encoder(
            torch.tensor([[[100.0], [200.0], [300.0]]]),
            attention_mask=torch.tensor([[1, 1, 0]]),
            special_tokens_mask=torch.tensor([[1, 1, 1]]),
            offset_mapping=torch.zeros((1, 3, 2), dtype=torch.long),
        )
