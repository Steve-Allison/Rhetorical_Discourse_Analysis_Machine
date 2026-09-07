"""Fitting provenance must survive export without fabricated calibration claims."""

import json
from pathlib import Path

import numpy as np
import pytest

from workbench.evaluation.rst.calibration import TemperatureScaler


def test_unfitted_export_is_explicit(tmp_path: Path) -> None:
    path = tmp_path / "parameters.json"
    TemperatureScaler().export(path)
    data = json.loads(path.read_text())
    assert data["calibrated"] is False
    assert data["fit_data_digest"] is None
    assert data["fit_sample_count"] == 0


def test_fit_provenance_and_parameter_replacement(tmp_path: Path) -> None:
    scaler = TemperatureScaler()
    logits = [[2.0, 0.0]] * 4
    scaler.fit(logits, [0, 0, 0, 1])
    path = tmp_path / "parameters.json"
    scaler.export(path)
    fitted = json.loads(path.read_text())
    assert fitted["calibrated"] is True
    assert fitted["fit_sample_count"] == 4
    assert len(fitted["fit_data_digest"]) == 64
    scaler.fit(logits, [1, 0, 0, 0])
    scaler.export(path)
    assert json.loads(path.read_text())["fit_data_digest"] != fitted["fit_data_digest"]
    scaler.temperature = 1.0
    scaler.export(path)
    assert json.loads(path.read_text())["calibrated"] is False


@pytest.mark.parametrize("field", ["temperature", "calibrated", "fit_data_digest", "fit_sample_count", "schema_version"])
def test_metadata_cannot_replace_evidence(tmp_path: Path, field: str) -> None:
    path = tmp_path / "parameters.json"
    with pytest.raises(ValueError, match="cannot override"):
        TemperatureScaler().export(path, extra_metadata={field: "invented"})
    assert not path.exists()


@pytest.mark.parametrize("temperature", [float("nan"), float("inf"), 0.0, -1.0])
def test_invalid_temperature_rejected(temperature: float) -> None:
    with pytest.raises(ValueError, match="finite and positive"):
        TemperatureScaler(temperature)


@pytest.mark.parametrize("logits, labels", [
    (np.empty((0, 2)), np.empty(0, dtype=int)),
    (np.array([[float("nan"), 0.0]]), np.array([0])),
    (np.array([[0.0, 1.0]]), np.array([-1])),
    (np.array([[0.0, 1.0]]), np.array([2])),
    (np.array([[0.0, 1.0]]), np.array([0.5])),
])
def test_invalid_fit_data_rejected(logits: np.ndarray, labels: np.ndarray) -> None:
    with pytest.raises(ValueError):
        TemperatureScaler().fit(logits, labels)
