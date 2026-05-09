"""Argument-validation tests for the two predictor families.

These DO NOT load models. Each test asserts the predictor raises the right
error type before any HF download or torch.load is reached.
"""

from __future__ import annotations

import pytest

from isanlp_rst.dmrst_parser.predictor import PredictorDMRST
from isanlp_rst.universal_parser.predictor import PredictorUniRST


class TestDMRSTArgValidation:
    def test_no_args_raises(self):
        with pytest.raises(ValueError, match="Pass either"):
            PredictorDMRST()

    def test_both_args_raises(self):
        with pytest.raises(ValueError, match="not both"):
            PredictorDMRST(model_dir="/tmp/x", hf_model_name="y")


class TestUniRSTArgValidation:
    def test_no_args_raises(self):
        with pytest.raises(ValueError, match="Pass either"):
            PredictorUniRST()

    def test_both_args_raises(self):
        with pytest.raises(ValueError, match="not both"):
            PredictorUniRST(model_dir="/tmp/x", hf_model_name="y")
