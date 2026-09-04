"""Canonical production-contract serialization and dispatch tests."""

import json

import pytest

from rdam.ingest.contracts.capabilities import ProductionCapabilities
from rdam.ingest.serialization import (
    UnsupportedContractVersionError,
    canonical_json_bytes,
    load_contract,
    serialize_contract,
)


def test_rfc8785_canonical_bytes_are_stable() -> None:
    assert canonical_json_bytes({"z": 0, "a": "é"}) == b'{"a":"\xc3\xa9","z":0}'


def test_duplicate_json_keys_are_rejected_before_model_validation() -> None:
    payload = b'{"contract":"isanlp_rst.production","contract":"other"}'
    with pytest.raises(ValueError, match="duplicate JSON object key"):
        load_contract(payload)


def test_execution_changes_do_not_change_semantic_identity() -> None:
    first = ProductionCapabilities.discover(execution_id="first")
    second = ProductionCapabilities.discover(execution_id="second")
    assert first.semantic == second.semantic
    assert first.execution != second.execution
    assert first.semantic_digest == second.semantic_digest


def test_future_contract_versions_fail_before_payload_dispatch() -> None:
    value = ProductionCapabilities.discover(execution_id="version-test")
    payload = json.loads(serialize_contract(value))
    payload["contract_version"] = "99.0.0"
    with pytest.raises(UnsupportedContractVersionError, match="99.0.0"):
        load_contract(json.dumps(payload).encode("utf-8"))


def test_serialize_load_serialize_is_byte_identical() -> None:
    encoded = serialize_contract(ProductionCapabilities.discover(execution_id="round-trip"))
    assert serialize_contract(load_contract(encoded)) == encoded
