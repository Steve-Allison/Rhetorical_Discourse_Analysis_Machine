"""Persisted deliberation summaries cannot contradict their native structure."""

import json

import pytest
from pydantic import ValidationError

from rdam.ibis.output import IbisOutput


def isolated_issue() -> IbisOutput:
    return IbisOutput.model_validate_json(json.dumps({
        "structure": {"nodes": [{"id": "q", "kind": "issue", "text": "What should we do?"}], "links": []},
        "input_origin": "supplied",
        "extraction": None,
        "grammar": "gibis-v1",
        "map": {
            "issues": [{"id": "q", "positions": [], "raised_by": [], "questions": [],
                        "generalizes": [], "specializes": [], "replaces": []}],
            "issues_without_positions": ["q"],
            "positions_without_arguments": [],
            "isolated_nodes": ["q"],
        },
    }))


@pytest.mark.parametrize("field", ["issues", "issues_without_positions", "isolated_nodes"])
def test_omitted_issue_evidence_rejected(field: str) -> None:
    payload = isolated_issue().model_dump(mode="json")
    payload["map"][field] = []
    with pytest.raises(ValidationError, match="map must reproduce"):
        IbisOutput.model_validate_json(json.dumps(payload))


def test_invented_position_rejected() -> None:
    payload = isolated_issue().model_dump(mode="json")
    payload["map"]["positions_without_arguments"] = ["missing"]
    with pytest.raises(ValidationError, match="map must reproduce"):
        IbisOutput.model_validate_json(json.dumps(payload))


def test_derivation_requires_reference() -> None:
    payload = isolated_issue().model_dump(mode="json")
    payload["input_origin"] = "explicitly_derived"
    with pytest.raises(ValidationError, match="input origin"):
        IbisOutput.model_validate_json(json.dumps(payload))


def test_supplied_input_cannot_claim_derivation() -> None:
    payload = isolated_issue().model_dump(mode="json")
    payload["derived_from"] = {"technique": "toulmin", "result_identity": "a" * 64}
    with pytest.raises(ValidationError, match="input origin"):
        IbisOutput.model_validate_json(json.dumps(payload))


def test_native_round_trip() -> None:
    result = isolated_issue()
    assert IbisOutput.model_validate_json(result.model_dump_json()) == result
