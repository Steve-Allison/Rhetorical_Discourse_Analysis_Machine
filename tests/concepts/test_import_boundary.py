"""Shared linking executes without importing inference or opening the network."""

import subprocess
import sys


def test_linking_does_not_import_models_or_open_network() -> None:
    result = subprocess.run(
        [sys.executable, "-c", '''
import sys

def reject_network(event, args):
    if event in {"socket.connect", "socket.getaddrinfo"}:
        raise RuntimeError("linking attempted network access")

sys.addaudithook(reject_network)
from rdam.concepts import ConceptIndex, link_source
from rdam.ingest import SourceArtifact, SourceForm
index = ConceptIndex.load()
for form, content in ((SourceForm.TEXT, "Adobe Analytics"), (SourceForm.MARKDOWN, "# Adobe Analytics")):
    source = SourceArtifact.from_bytes(content.encode(), source_name="example", source_form=form)
    result = link_source(source, index)
    assert any(mention.quote == "Adobe Analytics" for mention in result.mentions)
assert "torch" not in sys.modules
assert "transformers" not in sys.modules
'''],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr
