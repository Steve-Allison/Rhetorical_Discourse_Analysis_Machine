"""Recomputed digests cannot turn false native results into public views."""

import json
from pathlib import Path
import subprocess
import sys

from starlette.testclient import TestClient

from rdam.contracts import AggregateAnalysis, AggregateRequest, StructuredInput
from rdam.dung import DungProvider
from rdam.frameworks import Technique
from rdam.http import create_app
from rdam.interpretation import ViewRequest
from rdam.machine import Machine
from rdam.serialization import serialize, serialize_view_request


def _false_analysis() -> AggregateAnalysis:
    result = Machine((DungProvider(),)).analyse(AggregateRequest.for_structured((
        StructuredInput(technique=Technique.DUNG, payload={"arguments": ["a"], "attacks": [["a", "a"]]}),
    )))
    data = result.model_dump(exclude={"semantic_digest"})
    native = data["outcomes"][0]["result"]
    native.pop("semantic_digest")
    native.pop("artifact_digest")
    native["payload"]["extensions"]["stable"] = [[]]
    return AggregateAnalysis.model_validate(data)


def test_http_view_rejects_false_native_content_as_invalid_input() -> None:
    payload = serialize_view_request(ViewRequest(analysis=_false_analysis(), techniques=(Technique.DUNG,)))
    with TestClient(create_app(Machine(())), base_url="http://127.0.0.1:8765") as client:
        response = client.post("/v1/view", content=payload, headers={"Content-Type": "application/json"})
    assert response.status_code == 400
    assert response.json()["category"] == "invalid_request"


def test_cli_view_rejects_false_native_content_without_output(tmp_path: Path) -> None:
    source = tmp_path / "analysis.json"
    source.write_bytes(serialize(_false_analysis()))
    process = subprocess.run(
        [sys.executable, "-m", "rdam", "view", str(source), "--techniques", "dung"],
        capture_output=True, check=False,
    )
    assert process.returncode == 2
    assert process.stdout == b""
    assert json.loads(process.stderr)["category"] == "invalid_request"
