"""Persisted records reject damaged identities and ambiguous JSON before use."""

import base64
import json
from pathlib import Path
from typing import cast

import pytest

from rdam._strict import JsonValue
from rdam.contracts import AggregateRequest
from rdam.frameworks import Technique
from rdam.ingest.contracts.source import SourceForm
from rdam.serialization import UnsupportedRecordError, load, load_request, serialize, serialize_request

FIXTURES = Path(__file__).parent / "fixtures" / "historical"


def _saved(name: str = "walton-omitted-v1") -> bytes:
    return (FIXTURES / f"{name}.json").read_bytes().removesuffix(b"\n")


def _fields(name: str = "walton-omitted-v1") -> dict[str, JsonValue]:
    return cast(dict[str, JsonValue], json.loads(_saved(name)))


@pytest.mark.parametrize("as_text", (False, True))
def test_valid_saved_record_round_trips_exactly(as_text: bool) -> None:
    raw = _saved()
    record = load(raw.decode("utf-8") if as_text else raw)
    assert serialize(record) == raw


@pytest.mark.parametrize("field", ("semantic_digest", "artifact_digest"))
@pytest.mark.parametrize("damage", ("missing", "null", "mismatched"))
def test_saved_native_digest_is_required_and_never_repaired(field: str, damage: str) -> None:
    saved = _fields()
    if damage == "missing":
        del saved[field]
    elif damage == "null":
        saved[field] = None
    else:
        saved[field] = {"algorithm": "sha256", "hex_digest": "0" * 64}
    with pytest.raises(ValueError, match="digest"):
        load(json.dumps(saved))


@pytest.mark.parametrize("damage", ("missing", "null", "mismatched"))
def test_saved_aggregate_digest_is_required_and_never_repaired(damage: str) -> None:
    saved = _fields("aggregate-v1")
    if damage == "missing":
        del saved["semantic_digest"]
    elif damage == "null":
        saved["semantic_digest"] = None
    else:
        saved["semantic_digest"] = {"algorithm": "sha256", "hex_digest": "0" * 64}
    with pytest.raises(ValueError, match="digest"):
        load(json.dumps(saved))


@pytest.mark.parametrize("field", ("semantic_digest", "artifact_digest"))
@pytest.mark.parametrize("damage", ("missing", "null", "mismatched"))
def test_nested_native_digests_are_checked_inside_saved_aggregates(field: str, damage: str) -> None:
    saved = _fields("aggregate-v1")
    outcomes = saved["outcomes"]
    assert isinstance(outcomes, list)
    outcome = outcomes[0]
    assert isinstance(outcome, dict)
    native = outcome["result"]
    assert isinstance(native, dict)
    if damage == "missing":
        del native[field]
    elif damage == "null":
        native[field] = None
    else:
        native[field] = {"algorithm": "sha256", "hex_digest": "0" * 64}
    with pytest.raises(ValueError, match="digest"):
        load(json.dumps(saved))


def test_changed_native_payload_cannot_keep_saved_identity() -> None:
    saved = _fields()
    payload = saved["payload"]
    assert isinstance(payload, dict)
    payload["instance_count"] = 99
    with pytest.raises(ValueError, match="digest mismatch"):
        load(json.dumps(saved))


@pytest.mark.parametrize("nested", (False, True))
def test_duplicate_json_keys_are_rejected_even_when_values_agree(nested: bool) -> None:
    raw = _saved()
    if nested:
        raw = raw.replace(b'"algorithm":"sha256"', b'"algorithm":"sha256","algorithm":"sha256"', 1)
    else:
        raw = raw[:-1] + b',"contract":"rdam.native_result"}'
    with pytest.raises(ValueError, match="duplicate JSON object key"):
        load(raw)


@pytest.mark.parametrize("token", (b"NaN", b"Infinity", b"-Infinity", b"1e999"))
def test_nonfinite_json_numbers_are_rejected(token: bytes) -> None:
    raw = _saved().replace(b'"output_attempts":1', b'"output_attempts":' + token, 1)
    with pytest.raises(ValueError):
        load(raw)


@pytest.mark.parametrize("raw", (b"\xff", b'{"invalid":"\\ud800"}', b'{"invalid":"\\udfff"}'))
def test_invalid_utf8_and_unpaired_surrogates_are_rejected(raw: bytes) -> None:
    with pytest.raises(ValueError):
        load(raw)


@pytest.mark.parametrize(("field", "value"), (("contract", "rdam.unknown"), ("contract_version", "999.0.0")))
def test_unknown_contracts_and_versions_are_not_guessed(field: str, value: str) -> None:
    saved = _fields()
    saved[field] = value
    with pytest.raises(UnsupportedRecordError):
        load(json.dumps(saved))


def test_unknown_fields_are_not_silently_discarded() -> None:
    saved = _fields()
    saved["unexpected"] = "ignored would be wrong"
    with pytest.raises(ValueError, match="extra_forbidden"):
        load(json.dumps(saved))


def test_trailing_json_document_is_rejected() -> None:
    with pytest.raises(ValueError):
        load(_saved() + b"\n{}")


def test_text_request_round_trip_preserves_unicode_and_identity() -> None:
    request = AggregateRequest.for_text("Éva says: 🙂", (Technique.TOULMIN,), source_name="text-example")
    encoded = serialize_request(request)
    decoded = load_request(encoded)
    assert decoded == request
    assert decoded.text == "Éva says: 🙂"
    assert serialize_request(decoded) == encoded


def test_edu_request_round_trip_preserves_boundaries_and_order() -> None:
    edus = ("First claim.", "Éva gives evidence.", "🙂 Therefore conclude.")
    request = AggregateRequest.for_edus(edus, (Technique.TOULMIN,), source_name="edu-example")
    encoded = serialize_request(request)
    decoded = load_request(encoded.decode("utf-8"))
    assert decoded == request
    assert decoded.source_artifact is not None
    assert decoded.source_artifact.artifact.edus == edus
    assert serialize_request(decoded) == encoded


def test_binary_request_round_trip_uses_standard_padded_base64() -> None:
    # A byte-codec check, not an assertion that these bytes form a valid archive.
    payload = b"\x00\xff\xfe\xfb\x80\x00\x01"
    request = AggregateRequest.for_bytes(payload, SourceForm.DOCLANG_ARCHIVE, "binary-example", (Technique.TOULMIN,))
    encoded = serialize_request(request)
    fields = json.loads(encoded)
    assert fields["source_artifact"]["artifact"]["raw_bytes"] == base64.b64encode(payload).decode("ascii")
    decoded = load_request(encoded)
    assert decoded == request
    assert decoded.source_artifact is not None
    assert decoded.source_artifact.artifact.raw_bytes == payload
    assert serialize_request(decoded) == encoded


@pytest.mark.parametrize("encoded_bytes", ("/w", "/w=", "/w===", "_w==", "/w==\n", "/x==", "%%%", 255, None))
def test_request_rejects_invalid_or_noncanonical_base64(encoded_bytes: object) -> None:
    request = AggregateRequest.for_bytes(b"\xff", SourceForm.DOCLANG_ARCHIVE, "binary-example", (Technique.TOULMIN,))
    saved = json.loads(serialize_request(request))
    saved["source_artifact"]["artifact"]["raw_bytes"] = encoded_bytes
    with pytest.raises(ValueError):
        load_request(json.dumps(saved))


@pytest.mark.parametrize("field", ("contract", "contract_version"))
@pytest.mark.parametrize("damage", ("missing", "null", "unknown"))
def test_request_requires_supported_explicit_contract_and_version(field: str, damage: str) -> None:
    saved = json.loads(serialize_request(AggregateRequest.for_text("Evidence.", (Technique.TOULMIN,))))
    if damage == "missing":
        del saved[field]
    else:
        saved[field] = None if damage == "null" else "unknown"
    with pytest.raises(UnsupportedRecordError):
        load_request(json.dumps(saved))
