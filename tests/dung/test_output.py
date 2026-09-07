"""Saved extensions must be complete and correct, not merely well-shaped."""

import json

from pydantic import ValidationError
import pytest

from rdam.dung.output import DungOutput


def mutual_attack() -> DungOutput:
    return DungOutput.model_validate_json(json.dumps({
        "framework": {"arguments": ["a", "b"], "attacks": [["a", "b"], ["b", "a"]]},
        "input_origin": "supplied",
        "extensions": {"grounded": [], "complete": [[], ["a"], ["b"]],
                       "preferred": [["a"], ["b"]], "stable": [["a"], ["b"]]},
        "algorithm": {"name": "exhaustive-subset", "version": "1", "capacity": 2},
    }))


@pytest.mark.parametrize("semantics", ["complete", "preferred", "stable"])
def test_missing_valid_extension_rejected(semantics: str) -> None:
    payload = mutual_attack().model_dump(mode="json")
    payload["extensions"][semantics].pop()
    with pytest.raises(ValidationError, match="extensions must reproduce"):
        DungOutput.model_validate_json(json.dumps(payload))


@pytest.mark.parametrize("members", [["missing"], ["a", "b"], ["a", "a"]])
def test_invalid_grounded_extension_rejected(members: list[str]) -> None:
    payload = mutual_attack().model_dump(mode="json")
    payload["extensions"]["grounded"] = members
    with pytest.raises(ValidationError, match="extensions must reproduce"):
        DungOutput.model_validate_json(json.dumps(payload))


def test_duplicate_extension_rejected() -> None:
    payload = mutual_attack().model_dump(mode="json")
    payload["extensions"]["preferred"].append(["a"])
    with pytest.raises(ValidationError, match="extensions must reproduce"):
        DungOutput.model_validate_json(json.dumps(payload))


def test_reported_capacity_must_cover_framework() -> None:
    payload = mutual_attack().model_dump(mode="json")
    payload["algorithm"]["capacity"] = 1
    with pytest.raises(ValidationError, match="capacity is 1"):
        DungOutput.model_validate_json(json.dumps(payload))


def test_derivation_requires_reference() -> None:
    payload = mutual_attack().model_dump(mode="json")
    payload["input_origin"] = "explicitly_derived"
    with pytest.raises(ValidationError, match="input origin"):
        DungOutput.model_validate_json(json.dumps(payload))


def test_native_round_trip() -> None:
    result = mutual_attack()
    assert DungOutput.model_validate_json(result.model_dump_json()) == result
