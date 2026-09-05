"""Pin stored contract names directly, independently of analytical comparison."""

from importlib.resources import files
import json

from rdam.ingest.contracts.base import PRODUCTION_CONTRACT, WRITE_CONTRACT_VERSION
from rdam.rst.parser import Parser
from rdam.serialization import schema_models


def test_persisted_production_contract_and_schema_ids_are_unchanged() -> None:
    assert (PRODUCTION_CONTRACT, WRITE_CONTRACT_VERSION) == ("isanlp_rst.production", "2.0.0")
    recorded = {
        "analysed-outcome.schema.json",
        "capabilities.schema.json",
        "diagnostic-production-failure.schema.json",
        "empty-primary-analysis-outcome.schema.json",
        "parser-analysis-result.schema.json",
        "preparation-outcome.schema.json",
        "production-analysis-outcome.schema.json",
        "safe-production-failure.schema.json",
    }
    schemas = files("rdam.ingest").joinpath("schemas")
    actual = {
        path.name: json.loads(path.read_bytes())["$id"]
        for path in schemas.iterdir() if path.name.endswith(".json")
    }
    assert {name: actual[name] for name in recorded} == {
        name: f"https://schemas.isanlp-rst.local/production/2.0.0/{name}" for name in recorded
    }
    assert set(actual) == recorded | {
        f"machine-{name}.{mode}.schema.json"
        for name in schema_models() for mode in ("validation", "serialization")
    }


def test_production_parser_runtime_names_are_unchanged() -> None:
    recorded = {"isanlp_rst.parser/dmrst-v1": "dmrst", "isanlp_rst.parser/unirst-v1": "unirst"}
    assert set(Parser.AVAILABLE_FAMILIES) == set(recorded.values())
    for contract, family in recorded.items():
        assert Parser.family_for_runtime_contract(contract) == family
