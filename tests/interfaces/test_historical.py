"""Saved v1 records retain their exact canonical identity after current changes."""

from pathlib import Path

import pytest

from rdam.historical import HistoricalAggregateAnalysis, HistoricalNativeTechniqueResult
from rdam.serialization import load, serialize

FIXTURES = Path(__file__).parent / "fixtures" / "historical"


@pytest.mark.parametrize("name", ["walton-omitted-v1", "walton-partial-v1", "toulmin-v1", "aggregate-v1"])
def test_v1_records_remain_historical_and_byte_exact(name: str) -> None:
    payload = (FIXTURES / f"{name}.json").read_bytes().removesuffix(b"\n")
    record = load(payload)
    assert isinstance(record, (HistoricalAggregateAnalysis, HistoricalNativeTechniqueResult))
    assert record.contract_version == "1.0.0"
    assert serialize(record) == payload
