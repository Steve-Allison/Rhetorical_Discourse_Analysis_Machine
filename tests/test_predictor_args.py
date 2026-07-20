"""Argument-validation tests for the two predictor families.

These DO NOT load models. Each test asserts the predictor raises the right
error type before any HF download or torch.load is reached.
"""

from __future__ import annotations

import json

import pytest

from isanlp_rst.base_predictor import resolve_device
from isanlp_rst.dmrst_parser.predictor import PredictorDMRST
from isanlp_rst.universal_parser.predictor import PredictorUniRST


class TestDMRSTArgValidation:
    def test_no_args_raises(self):
        with pytest.raises(ValueError, match="Pass either"):
            PredictorDMRST()

    def test_both_args_raises(self):
        with pytest.raises(ValueError, match="not both"):
            PredictorDMRST(model_dir="/tmp/x", hf_model_name="y")

    def test_parse_rst_rejects_empty_and_non_str(self):
        dummy = object.__new__(PredictorDMRST)
        with pytest.raises(ValueError, match="non-empty"):
            PredictorDMRST.parse_rst(dummy, "   ")
        with pytest.raises(ValueError, match="must be provided"):
            PredictorDMRST.parse_rst(dummy, None)  # type: ignore[arg-type]
        with pytest.raises(TypeError, match="must be a str"):
            PredictorDMRST.parse_rst(dummy, 123)  # type: ignore[arg-type]


class TestUniRSTArgValidation:
    def test_no_args_raises(self):
        with pytest.raises(ValueError, match="Pass either"):
            PredictorUniRST()

    def test_both_args_raises(self):
        with pytest.raises(ValueError, match="not both"):
            PredictorUniRST(model_dir="/tmp/x", hf_model_name="y")

    def test_parse_rst_rejects_empty_and_non_str(self):
        dummy = object.__new__(PredictorUniRST)
        with pytest.raises(ValueError, match="non-empty"):
            PredictorUniRST.parse_rst(dummy, "\n\t")
        with pytest.raises(ValueError, match="must be provided"):
            PredictorUniRST.parse_rst(dummy, None)  # type: ignore[arg-type]
        with pytest.raises(TypeError, match="must be a str"):
            PredictorUniRST.parse_rst(dummy, b"bytes")  # type: ignore[arg-type]

    def test_relinventory_idx_out_of_bounds_raises_before_weight_load(
        self, tmp_path
    ):
        """OOB idx must fail on config alone — never reach torch.load."""
        (tmp_path / "config.json").write_text(
            json.dumps(
                {
                    "data": {
                        "corpora": ["eng.rst.rstdt", "eng.erst.gum"],
                    },
                    "model": {
                        "transformer": {
                            "model_name": "unused/for-oob-test",
                            "emb_size": 768,
                        }
                    },
                }
            ),
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="out of bounds"):
            PredictorUniRST(
                model_dir=str(tmp_path),
                hf_model_name=None,
                relinventory_idx=99,
            )

    def test_unknown_relinventory_name_raises_before_weight_load(self, tmp_path):
        (tmp_path / "config.json").write_text(
            json.dumps(
                {
                    "data": {"corpora": ["eng.rst.rstdt", "eng.erst.gum"]},
                    "model": {
                        "transformer": {
                            "model_name": "unused/for-name-test",
                            "emb_size": 768,
                        }
                    },
                }
            ),
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="Unknown relinventory"):
            PredictorUniRST(
                model_dir=str(tmp_path),
                hf_model_name=None,
                relinventory="not.a.corpus",
            )


class TestCudaDeviceValidation:
    def test_cuda_device_below_minus_one_raises(self):
        with pytest.raises(ValueError, match="cuda_device must be -1"):
            resolve_device(cuda_device=-2)

    def test_cuda_device_bool_raises(self):
        """``True`` is a subclass of ``int`` — must still be rejected."""
        with pytest.raises(ValueError, match="cuda_device must be an int"):
            resolve_device(cuda_device=True)  # type: ignore[arg-type]
