"""One request produces byte-identical results over Python, CLI and real HTTP."""

import json
from pathlib import Path
import subprocess
import sys

from rdam import Machine
from rdam.concepts import ConceptIndex, ConceptLinkRequest, execute_request
from rdam.concepts.serialization import MentionExport, export_jsonl, serialize
from rdam.ingest.contracts.source import SourceArtifact
from tests.interfaces.test_http import running_server


def test_python_cli_http_and_jsonl_parity(tmp_path: Path) -> None:
    request = ConceptLinkRequest(source=SourceArtifact.from_text("Adobe Analytics and scaffolding.", source_name="test"))
    expected = execute_request(request, ConceptIndex.load())
    path = tmp_path / "request.json"
    path.write_bytes(serialize(request))
    command = [sys.executable, "-m", "rdam", "concepts", "link", "--request", str(path)]
    cli = subprocess.run(command, capture_output=True, check=True)
    assert cli.stdout == serialize(expected) + b"\n"
    with running_server(Machine(())) as server:
        response = server.post("/v1/concepts/link", serialize(request))
        assert response.status == 200, response.body
        assert response.body == serialize(expected)
        invalid = json.loads(serialize(request))
        invalid["ontology_index"] = "/arbitrary/server/path"
        rejected = server.post("/v1/concepts/link", json.dumps(invalid).encode())
        assert rejected.status == 400
        assert json.loads(rejected.body)["operation"] == "concepts"
    exported = subprocess.run([*command, "--format", "jsonl"], capture_output=True, check=True)
    assert exported.stdout == export_jsonl(expected) + b"\n"
    records = [MentionExport.model_validate_json(line) for line in exported.stdout.splitlines()]
    assert len(records) == len(expected.mentions)
    assert all(record.source == expected.source and record.ontology == expected.ontology for record in records)


def test_invalid_request_preserves_existing_output(tmp_path: Path) -> None:
    source, output = tmp_path / "request.json", tmp_path / "output.json"
    source.write_text('{"inventory":null,"source":null}')
    output.write_text("preserve me")
    result = subprocess.run([sys.executable, "-m", "rdam", "concepts", "link", "--request", str(source),
                             "--output", str(output), "--force"], capture_output=True)
    assert result.returncode == 2
    assert output.read_text() == "preserve me"
