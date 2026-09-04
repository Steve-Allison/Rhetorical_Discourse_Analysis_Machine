"""Declarative source requests bind exact bytes without preparing content."""

from hashlib import sha256
from pathlib import Path
import subprocess
import sys

import pytest
from pydantic import ValidationError

from rdam import AggregateRequest, Technique
from rdam.ingest.contracts.source import SourceForm


def test_file_and_bytes_bind_exact_payload(tmp_path: Path) -> None:
    payload = b"# Evidence\n\nThe result follows.\n"
    path = tmp_path / "evidence.md"
    path.write_bytes(payload)
    requests = (
        AggregateRequest.for_source(path, (Technique.TOULMIN,)),
        AggregateRequest.for_bytes(payload, SourceForm.MARKDOWN, "evidence.md", (Technique.TOULMIN,)),
    )
    for request in requests:
        assert request.source.source_id.hex_digest == sha256(payload).hexdigest()
        assert request.text is None
        assert request.source_artifact is not None
        assert request.source_artifact.artifact.raw_bytes == payload
        assert AggregateRequest.model_validate_json(request.model_dump_json()) == request
    path.write_bytes(b"changed after constructing")
    assert requests[0].source_artifact is not None
    assert requests[0].source_artifact.artifact.raw_bytes == payload
    assert requests[0].source.source_id.hex_digest == sha256(payload).hexdigest()


def test_request_rejects_two_sources_and_wrong_byte_identity() -> None:
    request = AggregateRequest.for_bytes(b"same", SourceForm.TEXT, "source.txt", (Technique.RST,))
    with pytest.raises(ValidationError, match="exactly one"):
        AggregateRequest.model_validate({**request.model_dump(), "text": "same"})
    values = request.model_dump()
    values["source"] = AggregateRequest.for_text("different", (Technique.RST,)).source
    with pytest.raises(ValidationError, match="identity"):
        AggregateRequest.model_validate(values)


def test_constructing_source_request_imports_no_harvest_or_model() -> None:
    completed = subprocess.run(
        [sys.executable, "-c", "\n".join((
            "import sys",
            "from rdam import AggregateRequest, Technique",
            "from rdam.ingest.contracts.source import SourceForm",
            "AggregateRequest.for_bytes(b'hello', SourceForm.TEXT, 'a.txt', (Technique.RST,))",
            "assert 'rdam.ingest.prepare' not in sys.modules",
            "assert 'rdam.ingest._harvest' not in sys.modules",
            "assert 'torch' not in sys.modules",
        ))], capture_output=True, text=True, check=False,
    )
    assert completed.returncode == 0, completed.stderr
