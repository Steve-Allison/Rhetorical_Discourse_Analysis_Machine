"""Shared score metadata never merges distinct provenance or alters native values."""

import json

import pytest

from rdam.ingest.contracts.base import Sha256Identity
from rdam.ingest.contracts.inference import (
    ConfidenceKind, LabelledScore, NormalizedDistribution, PrimaryInferenceEvidence,
    ScoreValue, SegmentationDecisionEvidence,
)
from rdam.ingest.contracts.inference_storage import StoredPrimaryInferenceEvidence
from rdam.ingest.identity import semantic_sha256


def native_evidence() -> PrimaryInferenceEvidence:
    producer = Sha256Identity(hex_digest=semantic_sha256({"synthetic_test_component": "segmenter"}))
    calibrated = Sha256Identity(hex_digest=semantic_sha256({"synthetic_test_calibration": "distinct metadata"}))
    decisions: list[SegmentationDecisionEvidence] = []
    for index, calibration in enumerate((None, None, calibrated)):
        selected = ScoreValue(
            value=0.75, confidence_kind=ConfidenceKind.PROBABILITY, minimum=0.0, maximum=1.0,
            calibration_identity=calibration, producing_component_identity=producer,
        )
        other = ScoreValue(**{**selected.model_dump(), "value": 0.25})
        decisions.append(SegmentationDecisionEvidence(
            decision_id=f"synthetic:{index}", boundary_id=f"synthetic-boundary:{index}",
            selected_boundary=True, decision_basis="model", confidence=selected,
            distribution=NormalizedDistribution(entries=(
                LabelledScore(label="boundary", score=selected), LabelledScore(label="no_boundary", score=other),
            )), token_ids=(f"token:{index}",), resulting_edu_ids=(f"edu:{index}",),
            producing_component_identity=producer,
        ))
    return PrimaryInferenceEvidence(segmentation_decisions=tuple(decisions), structure_decisions=(), refinements=())


def test_shared_metadata_preserves_scores_distributions_and_distinct_calibration() -> None:
    native = native_evidence()
    stored = StoredPrimaryInferenceEvidence.capture(native)
    assert len(stored.score_contexts) == 2
    assert stored.score_contexts[0].calibration_identity is None
    assert stored.score_contexts[1].calibration_identity is not None
    assert stored.resolve() == native
    assert StoredPrimaryInferenceEvidence.model_validate_json(stored.model_dump_json()).resolve() == native
    saved = json.loads(stored.model_dump_json())
    assert saved["segmentation_decisions"][0]["confidence"] == {"value": 0.75, "context": 0}
    assert saved["segmentation_decisions"][2]["confidence"]["context"] == 1
    assert len(stored.model_dump_json()) < len(native.model_dump_json())


@pytest.mark.parametrize("damage", ("missing", "duplicate", "unused", "reordered", "range", "nonfinite"))
def test_invalid_context_tables_and_scores_are_rejected(damage: str) -> None:
    saved = json.loads(StoredPrimaryInferenceEvidence.capture(native_evidence()).model_dump_json())
    match damage:
        case "missing":
            saved["score_contexts"].pop()
        case "duplicate":
            saved["score_contexts"].append(saved["score_contexts"][0])
        case "unused":
            saved["score_contexts"].append({**saved["score_contexts"][0], "maximum": 2.0})
        case "reordered":
            saved["segmentation_decisions"].reverse()
        case "range":
            saved["segmentation_decisions"][0]["confidence"]["value"] = 2.0
        case "nonfinite":
            saved["score_contexts"][0]["maximum"] = float("inf")
    with pytest.raises(ValueError):
        StoredPrimaryInferenceEvidence.model_validate_json(json.dumps(saved))


def test_empty_evidence_has_no_invented_context() -> None:
    native = PrimaryInferenceEvidence(segmentation_decisions=(), structure_decisions=(), refinements=())
    stored = StoredPrimaryInferenceEvidence.capture(native)
    assert stored.score_contexts == ()
    assert stored.resolve() == native
