"""Preparation storage preserves source evidence and independently loadable natives."""

import json
from pathlib import Path

from pydantic import ValidationError
import pytest

from rdam._strict import canonical_json_bytes
from rdam.contracts import (
    AggregateAnalysis, AggregateRequest, HistoricalMachinePreparation, MachinePreparation,
    NativeTechniqueResult, ResultOutcome, StructuredInput,
)
from rdam.dung import DungProvider
from rdam.frameworks import Technique
from rdam.machine import Machine
from rdam.serialization import load, schema, serialize


FIXTURE = Path(__file__).parent / "fixtures" / "preparation-v1.json"


def preparation() -> MachinePreparation:
    old = load(FIXTURE.read_bytes())
    assert isinstance(old, HistoricalMachinePreparation)
    return MachinePreparation.model_validate(old.model_dump(exclude={"contract_version", "semantic_digest", "projections"}))


def aggregate_with_shared_object() -> AggregateAnalysis:
    """Use real formal analysis, adding explicit synthetic opaque storage-test data."""
    prepared = preparation()
    aggregate = Machine((DungProvider(),)).analyse(AggregateRequest.for_structured((
        StructuredInput(technique=Technique.DUNG, payload={"arguments": ["a"], "attacks": []}),
    ), source=prepared.source))
    outcome = aggregate.outcomes[0]
    assert isinstance(outcome, ResultOutcome)
    native = outcome.result.model_dump(exclude={"semantic_digest", "artifact_digest"})
    native["payload"]["synthetic/storage~test"] = {
        "preparation": {
            **prepared.preparation.model_dump(mode="json"),
            "analysis_plan": prepared.projections[0].analysis_plan.model_dump(mode="json"),
        },
        "$ref": "/literal-native-data-never-resolved",
    }
    result = NativeTechniqueResult.model_validate(native)
    data = aggregate.model_dump(exclude={"semantic_digest"})
    data["outcomes"] = (ResultOutcome(technique=Technique.DUNG, result=result),)
    data["preparation"] = prepared
    return AggregateAnalysis.model_validate(data)


def test_historical_preparation_preserves_every_byte() -> None:
    payload = FIXTURE.read_bytes()
    old = load(payload)
    assert isinstance(old, HistoricalMachinePreparation)
    assert serialize(old) == payload
    damaged = json.loads(payload)
    del damaged["projections"]
    with pytest.raises(ValidationError, match="requires projections"):
        load(canonical_json_bytes(damaged))


def test_current_preparation_derives_identical_projection_without_storing_it() -> None:
    prepared = preparation()
    serialized = serialize(prepared)
    assert "projections" not in json.loads(serialized)
    restored = load(serialized)
    assert isinstance(restored, MachinePreparation)
    assert restored == prepared
    assert restored.projections
    old = load(FIXTURE.read_bytes())
    assert isinstance(old, HistoricalMachinePreparation)
    assert restored.projections == old.projections
    assert len(serialized) < len(FIXTURE.read_bytes())


def test_shared_evidence_stored_once_with_native_payload_unchanged() -> None:
    aggregate = aggregate_with_shared_object()
    native = aggregate.outcomes[0]
    assert isinstance(native, ResultOutcome)
    native_bytes = serialize(native.result)
    payload = serialize(aggregate)
    saved = json.loads(payload)
    assert saved["preparation"]["kind"] == "native_preparation_reference"
    assert saved["preparation"]["preparation_pointer"] == "/synthetic~1storage~0test/preparation"
    assert saved["preparation"]["analysis_plan"] != saved["outcomes"][0]["result"]["payload"]["synthetic/storage~test"]["preparation"]["analysis_plan"]
    assert saved["outcomes"][0]["result"] == json.loads(native_bytes)
    assert payload.count(b'"prepared_document"') == 1
    restored = load(payload)
    assert restored == aggregate
    assert serialize(restored) == payload
    assert isinstance(restored, AggregateAnalysis)
    result = restored.outcomes[0]
    assert isinstance(result, ResultOutcome)
    assert serialize(result.result) == native_bytes
    assert serialize(load(native_bytes)) == native_bytes


@pytest.mark.parametrize(("field", "replacement"), (
    ("native_result_pointer", "/outcomes/0"),
    ("preparation_pointer", "/missing"),
    ("preparation_pointer", "/synthetic~1storage~0test/$ref"),
    ("semantic_digest", {"algorithm": "sha256", "hex_digest": "0" * 64}),
))
def test_dangling_or_corrupt_shared_preparation_is_rejected(field: str, replacement: object) -> None:
    saved = json.loads(serialize(aggregate_with_shared_object()))
    saved["preparation"][field] = replacement
    with pytest.raises(ValidationError):
        load(canonical_json_bytes(saved))


def test_shared_and_standalone_preparation_match_both_public_schemas() -> None:
    from jsonschema import Draft202012Validator

    for record, name in ((preparation(), "preparation"), (aggregate_with_shared_object(), "aggregate")):
        saved = json.loads(serialize(record))
        for mode in ("validation", "serialization"):
            Draft202012Validator(schema(name, mode=mode)).validate(saved)


def test_nonidentical_evidence_keeps_standalone_preparation() -> None:
    aggregate = aggregate_with_shared_object()
    native = aggregate.outcomes[0]
    assert isinstance(native, ResultOutcome)
    data = native.result.model_dump(exclude={"semantic_digest", "artifact_digest"})
    data["payload"]["synthetic/storage~test"]["preparation"]["additional_evidence"] = "distinct"
    changed = NativeTechniqueResult.model_validate(data)
    record = aggregate.model_dump(exclude={"semantic_digest", "preparation"})
    record["preparation"] = aggregate.preparation
    record["outcomes"] = (ResultOutcome(technique=Technique.DUNG, result=changed),)
    updated = AggregateAnalysis.model_validate(record)
    saved = json.loads(serialize(updated))
    assert saved["preparation"]["contract_version"] == "2.0.0"
    assert "preparation" in saved["preparation"]
    assert "projections" not in saved["preparation"]
    assert load(serialize(updated)) == updated


def test_stored_binding_identity_cannot_be_omitted_or_forged() -> None:
    saved = json.loads(serialize(preparation()))
    for identity in (None, {"algorithm": "sha256", "hex_digest": "0" * 64}):
        damaged = json.loads(json.dumps(saved))
        if identity is None:
            del damaged["bindings"][0]["projection_identity"]
        else:
            damaged["bindings"][0]["projection_identity"] = identity
        with pytest.raises(ValidationError):
            load(canonical_json_bytes(damaged))
