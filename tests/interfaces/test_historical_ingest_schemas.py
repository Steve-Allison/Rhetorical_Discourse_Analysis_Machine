"""Retained v2 schemas describe the actual saved Feature 017 records.

The baseline layout uses schemas recovered from commit 6a647b6cbad581199eecec70d87d81f78ddd601d.
The later v2 layout is separately preserved from 0409816ae4cd768a4fe796b89f4a6b0103043ed1.
Historical schema validity does not endorse the old analytical claims.
"""

from importlib import resources
import json
from pathlib import Path
from typing import cast

from jsonschema import Draft202012Validator
from jsonschema.protocols import Validator
import pytest

from rdam.ingest.historical import load_historical_contract


BASELINE = Path("specs/017-universal-source-pipeline/evidence/baseline-dmrst-current")
RECORDS = tuple(path for path in sorted(BASELINE.glob("*.json")) if path.name != "digests.json")
BASELINE_SCHEMA_REVISION = "6a647b6cbad581199eecec70d87d81f78ddd601d"


@pytest.mark.parametrize("path", RECORDS, ids=lambda path: path.name)
def test_saved_ingest_record_matches_retained_schema(path: Path) -> None:
    raw = path.read_bytes()
    record = load_historical_contract(raw)
    payload = record.payload
    filename = str(payload["kind"]).replace("_", "-") + ".schema.json"
    resource = resources.files("rdam.ingest").joinpath(
        "schemas", "historical", "2.0.0", BASELINE_SCHEMA_REVISION, filename,
    )
    schema = json.loads(resource.read_bytes())
    Draft202012Validator.check_schema(schema)
    validator = cast(Validator, Draft202012Validator(schema))
    validator.validate(payload)
    assert not validator.is_valid({**payload, "contract_version": "3.0.0"})
    assert not validator.is_valid({**payload, "semantic": None})
    assert path.read_bytes() == raw


def test_retained_schema_definitions_are_valid_draft_2020_12() -> None:
    root = resources.files("rdam.ingest").joinpath("schemas", "historical", "2.0.0")
    schemas = tuple(path for revision in root.iterdir() for path in revision.iterdir()
                    if path.name.endswith(".schema.json"))
    assert schemas
    for path in schemas:
        document = json.loads(path.read_bytes())
        Draft202012Validator.check_schema(document)
        assert document["$id"].endswith(f"/2.0.0/{path.name}")
