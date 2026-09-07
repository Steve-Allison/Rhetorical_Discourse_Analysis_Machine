"""Historical integrity does not upgrade saved analytical claims."""

from typing import Any

import pytest

from rdam._canonical import canonical_json_bytes, semantic_sha256
from rdam.ingest.historical import HistoricalProductionRecord, load_historical_contract
from rdam.ingest.serialization import load_contract, serialize_contract
from rdam.ingest.contracts.capabilities import ProductionCapabilities


def historical_parser() -> dict[str, Any]:
    semantic = {
        "analysis": {"timing": {"total": 12}, "provenance": {"timestamp": "saved"}},
        "primary_inference": {"confidence": 0.88, "calibrated": True},
        "recombination": {"unit_durations_ms": [2, 3], "unit_identities": ["a", "b"]},
    }
    projected = {
        "analysis": {"timing": None, "provenance": {"timestamp": None}},
        "primary_inference": semantic["primary_inference"],
        "recombination": {"unit_identities": ["a", "b"]},
    }
    envelope = {"contract": "isanlp_rst.production", "contract_version": "2.0.0",
                "kind": "parser_analysis_result"}
    return {**envelope, "semantic": semantic, "execution": {"device": "cpu"},
            "semantic_digest": {"algorithm": "sha256", "hex_digest": semantic_sha256(
                {**envelope, "semantic": projected}
            )}}


def test_historical_values_are_preserved_without_becoming_current_evidence() -> None:
    saved = historical_parser()
    record = load_historical_contract(canonical_json_bytes(saved))
    assert record.evidence_status == "historical_unverified_analysis"
    assert record.payload == saved
    detached = record.payload
    detached["semantic"]["primary_inference"]["confidence"] = 1.0
    assert record.payload == saved
    assert load_historical_contract(record.canonical_bytes).canonical_bytes == record.canonical_bytes


def test_historical_projection_preserves_v2_execution_exclusions() -> None:
    saved = historical_parser()
    saved["execution"]["device"] = "mps"
    saved["semantic"]["analysis"]["timing"] = {"total": 99}
    saved["semantic"]["analysis"]["provenance"]["timestamp"] = "later"
    saved["semantic"]["recombination"]["unit_durations_ms"] = [4, 5]
    assert load_historical_contract(canonical_json_bytes(saved)).payload == saved


def test_changed_historical_scores_fail_digest_verification() -> None:
    saved = historical_parser()
    saved["semantic"]["primary_inference"]["confidence"] = 1.0
    with pytest.raises(ValueError, match="semantic digest mismatch"):
        load_historical_contract(canonical_json_bytes(saved))


@pytest.mark.parametrize("payload", (
    b'{"contract":1,"contract":2}', b'[]',
    b'{"x":NaN}', b'{"x":"\\ud800"}',
))
def test_historical_reading_rejects_non_interoperable_json(payload: bytes) -> None:
    with pytest.raises(ValueError):
        load_historical_contract(payload)


def test_historical_reader_rejects_current_or_unknown_contracts() -> None:
    saved = historical_parser()
    saved["contract_version"] = "3.0.0"
    with pytest.raises(ValueError, match="requires isanlp_rst.production 2.0.0"):
        load_historical_contract(canonical_json_bytes(saved))


def test_public_dispatch_keeps_historical_and_current_records_distinct() -> None:
    saved = canonical_json_bytes(historical_parser())
    historical = load_contract(saved)
    assert isinstance(historical, HistoricalProductionRecord)
    assert serialize_contract(historical) == saved
    current = ProductionCapabilities.discover(execution_id="version-dispatch")
    assert current.contract_version == "3.0.0"
    assert tuple(str(version) for version in current.semantic.readable_contract_versions) == ("3.0.0", "2.0.0")
    restored = load_contract(serialize_contract(current))
    assert isinstance(restored, ProductionCapabilities)
    assert restored == current
