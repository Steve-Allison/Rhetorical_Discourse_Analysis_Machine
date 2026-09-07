"""Adversarial persisted SDRT and Walton output validation."""

import json
from typing import Any

import pytest

from rdam.sdrt.output import SdrtOutput
from rdam.walton.output import WaltonOutput
from rdam.walton.schemes import SCHEMES, CriticalQuestion, CriticalQuestionStatus, SchemeId, SchemeInstance, WaltonAnalysis


def extraction() -> dict[str, Any]:
    return {"model": "fixture", "output_attempts": 1, "transport_attempts": 1,
            "instructions_digest": "b" * 64}


@pytest.mark.parametrize("mutation", ("count", "dangling", "disconnected"))
def test_sdrt_rejects_false_graph_validation_claim(mutation: str) -> None:
    payload: dict[str, Any] = {
        "edus": [{"unit_id": "a", "text": "A", "start": 0, "end": 1},
                 {"unit_id": "b", "text": "B", "start": 2, "end": 3}],
        "cdus": [], "relations": [{"relation_id": "r", "source_id": "a", "target_id": "b",
                                    "label": "Narration", "structural_type": "coordinating"}],
        "edu_count": 2, "cdu_count": 0, "relation_count": 1,
        "right_frontier_validated": True, "extraction": extraction(),
    }
    SdrtOutput.model_validate_json(json.dumps(payload))
    if mutation == "count":
        payload["edu_count"] = 3
        reason = "counts must reproduce"
    elif mutation == "dangling":
        payload["relations"][0]["target_id"] = "missing"
        reason = "unknown discourse unit"
    else:
        payload["relations"] = []
        payload["relation_count"] = 0
        reason = "disconnected"
    with pytest.raises(ValueError, match=reason):
        SdrtOutput.model_validate_json(json.dumps(payload))


@pytest.mark.parametrize("mutation", ("count", "question", "premise", "assessment", "catalogue"))
def test_walton_rejects_false_catalogue_and_summary_claims(mutation: str) -> None:
    scheme = SCHEMES[SchemeId.SIGN]
    instance = SchemeInstance(
        scheme_id=scheme.scheme_id, conclusion="Rain is approaching.",
        premises={role: f"Source evidence for {role}." for role in scheme.premise_roles},
        critical_questions=[CriticalQuestion(index=index, status=CriticalQuestionStatus.OPEN)
                            for index in range(len(scheme.critical_questions))],
    )
    payload: dict[str, Any] = {**WaltonAnalysis(instances=[instance]).to_payload(), "extraction": extraction()}
    WaltonOutput.model_validate_json(json.dumps(payload))
    if mutation == "count":
        payload["question_count"] += 1
        reason = "totals must reproduce"
    elif mutation == "question":
        payload["instances"][0]["critical_questions"][0]["question"] = "A different question?"
        reason = "catalogue and derived fields"
    elif mutation == "premise":
        payload["instances"][0]["premises"].clear()
        reason = "requires premise roles"
    elif mutation == "assessment":
        payload["instances"][0]["critical_questions"][0]["status"] = "addressed"
        reason = "marked addressed must say how"
    else:
        payload["scheme_set"] = "unknown-catalogue"
        reason = "unsupported scheme set"
    with pytest.raises(ValueError, match=reason):
        WaltonOutput.model_validate_json(json.dumps(payload))
