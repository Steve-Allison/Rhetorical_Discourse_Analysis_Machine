"""PyTorch RNN dropout is inter-layer only. A 1-layer LSTM with non-zero
dropout is a no-op and emits UserWarning. DecoderRNN already gated this;
ToNySegmenter did not.
"""

import warnings

import pytest

from workbench.archive.legacy_2021.dmrst_parser.src.parser.segmenters import ToNySegmenter as DmrstTony
from workbench.archive.legacy_2021.universal_parser.src.parser.segmenters import ToNySegmenter as UnirstTony


@pytest.mark.parametrize("cls", [DmrstTony, UnirstTony])
def test_tony_one_layer_lstm_does_not_warn(cls) -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("error", UserWarning)
        cls(embedding_dim=8, hidden_dim=4, num_layers=1, lstm_dropout=0.2)


@pytest.mark.parametrize("cls", [DmrstTony, UnirstTony])
def test_tony_stacked_lstm_keeps_dropout(cls) -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("error", UserWarning)
        seg = cls(embedding_dim=8, hidden_dim=4, num_layers=2, lstm_dropout=0.2)
    assert seg.lstm.dropout == 0.2
