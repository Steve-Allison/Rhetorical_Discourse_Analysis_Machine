"""The public ingest result must retain evidence from its own model invocation."""

import math
import json
from pathlib import Path

import pytest

from rdam.ingest import ProductionIngestor, SourceArtifact
from rdam.ingest.contracts.analysis import AnalysedOutcome
from rdam.ingest.contracts.inference_storage import StoredPrimaryInferenceEvidence
from rdam.rst.annotation_rst import DiscourseUnit
from rdam.rst.inference_evidence import NetworkStructureDecision
from rdam.rst.parser import Parser


@pytest.mark.slow
@pytest.mark.parametrize("release_id", ("gumrrg-eb1d5745f3a1", "unirst-9407970f1d9d"))
def test_public_primary_scores_match_same_forward_pass(
    release_id: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parser = Parser.from_model_release(
        Path.home() / ".cache/isanlp_rst/model-releases",
        release_id,
        device="cpu",
    )
    captured: list[NetworkStructureDecision] = []
    validate = parser.predictor._validate_structure_decisions

    def retain(unit: DiscourseUnit, decisions: tuple[NetworkStructureDecision, ...]) -> None:
        validate(unit, decisions)
        captured.extend(decisions)

    monkeypatch.setattr(parser.predictor, "_validate_structure_decisions", retain)
    outcome = ProductionIngestor(parser=parser).analyse(
        SourceArtifact.from_text(
            "It rained. The match stopped. The crowd left.",
            source_name="joint-score-fidelity",
        )
    )
    assert isinstance(outcome, AnalysedOutcome), outcome.model_dump_json()
    primary = outcome.semantic.primary_inference
    assert primary is not None and captured
    assert len(primary.structure_decisions) == len(captured)
    stored = json.loads(outcome.model_dump_json())["semantic"]["parser_result"]["semantic"]["primary_inference"]
    assert len(captured) > 1
    assert len(stored["joint_class_inventories"]) == 1
    assert stored["joint_class_inventories"][0] == list(captured[0].joint_labels)
    assert all("labels" not in decision["joint"] for decision in stored["structure_decisions"])
    restored = AnalysedOutcome.model_validate_json(outcome.model_dump_json())
    assert restored.semantic.primary_inference == primary
    for damage in ("absent", "duplicate", "unused", "wrong_selection"):
        damaged = json.loads(json.dumps(stored))
        match damage:
            case "absent":
                damaged["structure_decisions"][0]["joint"]["class_inventory"] = len(damaged["joint_class_inventories"])
            case "duplicate":
                damaged["joint_class_inventories"].append(damaged["joint_class_inventories"][0])
            case "unused":
                damaged["structure_decisions"] = []
            case "wrong_selection":
                damaged["structure_decisions"][0]["joint"]["selected_class"] = len(damaged["joint_class_inventories"][0])
        with pytest.raises(ValueError, match="inventor|selection"):
            StoredPrimaryInferenceEvidence.model_validate_json(json.dumps(damaged))
    for exported, actual in zip(primary.structure_decisions, captured, strict=True):
        assert exported.joint is not None and exported.confidence is not None
        assert exported.joint.labels == actual.joint_labels
        assert exported.joint.selected_class == actual.selected_class
        assert exported.joint.log_probabilities == tuple(
            value if math.isfinite(value) else None for value in actual.joint_log_probabilities
        )
        assert exported.confidence.value == math.exp(actual.joint_log_probabilities[actual.selected_class])
        assert exported.confidence.calibration_identity is None
        assert exported.confidence_basis == "joint_relation_nuclearity_given_selected_split"
        assert exported.selected_split == actual.split
        relation, _, nuclearity = actual.joint_labels[actual.selected_class].rpartition("_")
        assert exported.relation.raw_label == relation
        assert exported.nuclearity == nuclearity.upper()
        corrupted = exported.model_dump()
        corrupted["confidence"] = {**exported.confidence.model_dump(), "value": 0.0}
        with pytest.raises(ValueError, match="confidence contradicts"):
            type(exported).model_validate(corrupted)
