"""Real CLI acquisition and canonical Python operations preserve identical source data."""

import json
from pathlib import Path
import subprocess
import sys

import pytest

from rdam.composition import production_machine
from rdam.contracts import AggregateRequest, PreparationRequest, StructuredInput
from rdam.frameworks import Technique
from rdam.ingest.contracts.source import SourceForm
from rdam.serialization import serialize, serialize_request
from tests.ingest.test_inventory_completeness import source_case
from tests.interfaces.test_cli import diagnostic, json_array, json_object, record, run_cli


def test_cli_canonical_json_is_byte_identical_and_runs_one_inference() -> None:
    request = AggregateRequest.for_structured((StructuredInput(technique=Technique.DUNG,
        payload={"arguments": ["a", "b"], "attacks": [["a", "b"]]}),))
    expected = production_machine().analyse(request)
    # Observe the real provider, rather than replacing the engine with a recorder.
    script = """
import sys
from rdam.cli import main
calls = 0
def profile(frame, event, argument):
    global calls
    if event == 'call' and frame.f_globals.get('__name__') == 'rdam.dung.provider' and frame.f_code.co_name == 'analyse':
        calls += 1
sys.setprofile(profile)
import threading
threading.setprofile(profile)
status = main(['analyse', '--request', '-'])
sys.setprofile(None)
threading.setprofile(None)
assert calls == 1, calls
raise SystemExit(status)
"""
    result = subprocess.run([sys.executable, "-c", script], input=serialize_request(request), capture_output=True,
                            check=False, timeout=30)
    assert result.returncode == 0, result.stderr
    assert result.stdout == serialize(expected) + b"\n"
    assert result.stderr == b""


@pytest.mark.parametrize(("filename", "source_form"), (
    ("source.txt", SourceForm.TEXT), ("source.md", SourceForm.MARKDOWN),
    ("source.docling.json", SourceForm.DOCLING_JSON), ("source.dclg", SourceForm.DOCLANG_XML),
    ("source.dclx", SourceForm.DOCLANG_ARCHIVE),
))
def test_cli_routes_path_source_forms_through_source_artifact(filename: str, source_form: SourceForm, tmp_path: Path) -> None:
    artifact, expected_inventory = source_case(source_form)
    assert artifact.raw_bytes is not None
    path = tmp_path / filename
    path.write_bytes(artifact.raw_bytes)
    request = PreparationRequest.for_source(path)
    expected = production_machine().prepare(request)
    result = run_cli("prepare", str(path))
    payload = record(result)
    assert result.stdout == serialize(expected) + b"\n"
    preparation = json_object(payload["preparation"])
    assert {json_object(item)["item_id"] for item in json_array(preparation["inventory"])} == expected_inventory
    assert json_object(preparation["source"])["source_form"] == source_form.value


def test_cli_routes_presegmented_edus_without_flattening() -> None:
    edus = ("First.", "Second.")
    request = PreparationRequest.for_edus(edus, source_name="cli-edus")
    expected = production_machine().prepare(request)
    result = run_cli("prepare", "--edus", json.dumps(edus))
    assert result.returncode == 0, result.stderr
    assert result.stdout == serialize(expected) + b"\n"
    assert len(expected.preparation.inventory) == len(edus)
    assert tuple(item.text for item in expected.preparation.inventory) == edus


def test_cli_malformed_input_is_a_canonical_safe_failure() -> None:
    diagnostic(run_cli("prepare", "--edus", "not-json"))
