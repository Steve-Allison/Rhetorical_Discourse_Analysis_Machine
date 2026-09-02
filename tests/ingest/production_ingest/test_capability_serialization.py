"""Canonical capability persistence and semantic identity."""

from rdam.rst.ingest import ProductionCapabilities, describe_capabilities, load_contract, serialize_contract


def test_capabilities_round_trip_canonically_without_execution_identity() -> None:
    first = describe_capabilities()
    second = describe_capabilities()
    assert first.execution != second.execution
    assert first.semantic_digest == second.semantic_digest
    encoded = serialize_contract(first)
    loaded = load_contract(encoded)
    assert isinstance(loaded, ProductionCapabilities)
    assert serialize_contract(loaded) == encoded
