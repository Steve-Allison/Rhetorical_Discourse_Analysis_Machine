"""Current normative Docling, DocLang, and DocLang-archive conformance."""

from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import doclang
from docling_core.types.doc import ContentLayer, DoclingDocument
from lxml import etree
import pytest

from rdam.rst.doclang.errors import InvalidDoclangError
from rdam.rst.ingest import SourceArtifact, SourceForm
from rdam.rst.ingest.contracts import ContentClass
from rdam.rst.ingest.prepare import inventory_source


DOCLANG_FIXTURES = Path("tests/fixtures/doclang")
DOCLING_FIXTURES = Path("tests/fixtures/docling")
DOCLANG_MANIFEST = json.loads((DOCLANG_FIXTURES / "upstream-manifest.json").read_text(encoding="utf-8"))
VALID_DOCLANG_FIXTURES = tuple(sorted(DOCLANG_FIXTURES.glob("*.dclg")))
INVALID_DOCLANG_FIXTURES = tuple(sorted((DOCLANG_FIXTURES / "invalid").glob("*.dclg")))


def test_current_upstream_doclang_fixture_corpora_are_complete() -> None:
    assert len(VALID_DOCLANG_FIXTURES) == 42
    assert len(INVALID_DOCLANG_FIXTURES) == 59
    assert {path.name for path in VALID_DOCLANG_FIXTURES} == DOCLANG_MANIFEST["files"].keys()
    assert {path.name for path in INVALID_DOCLANG_FIXTURES} == DOCLANG_MANIFEST["invalid_files"].keys()


@pytest.mark.parametrize("fixture", VALID_DOCLANG_FIXTURES, ids=lambda path: path.name)
def test_current_upstream_valid_doclang_specimen_is_unmodified_and_accepted(fixture: Path) -> None:
    assert sha256(fixture.read_bytes()).hexdigest() == DOCLANG_MANIFEST["files"][fixture.name]
    root_tag = etree.parse(fixture).getroot().tag
    namespaced = isinstance(root_tag, str) and root_tag.startswith("{")
    doclang.validate(fixture, allow_empty_namespace=not namespaced)
    inventory, _contract = inventory_source(
        SourceArtifact.from_path(fixture, source_form=SourceForm.DOCLANG_XML)
    )
    assert inventory


@pytest.mark.parametrize("fixture", INVALID_DOCLANG_FIXTURES, ids=lambda path: path.name)
def test_current_upstream_invalid_doclang_specimen_is_unmodified_and_rejected(fixture: Path) -> None:
    assert sha256(fixture.read_bytes()).hexdigest() == DOCLANG_MANIFEST["invalid_files"][fixture.name]
    with pytest.raises(doclang.ValidationError):
        doclang.validate(fixture, allow_empty_namespace=True)
    with pytest.raises(InvalidDoclangError, match="failed current validation"):
        inventory_source(SourceArtifact.from_path(fixture, source_form=SourceForm.DOCLANG_XML))


def test_every_docling_specimen_loads_and_traverses_the_current_complete_api() -> None:
    fixtures = tuple(sorted(DOCLING_FIXTURES.glob("*.docling.json")))
    assert {path.name for path in fixtures} == {
        "markdown.docling.json",
        "pdf.docling.json",
        "pptx.docling.json",
        "vtt.docling.json",
    }
    for fixture in fixtures:
        document = DoclingDocument.load_from_json(fixture)
        items = tuple(
            document.iterate_items(
                with_groups=True,
                traverse_pictures=True,
                included_content_layers=set(ContentLayer),
            )
        )
        assert items
        assert str(document.version) == "1.10.0"


def test_current_doclang_opc_specimen_validates_and_retains_only_payload_as_asset() -> None:
    document = (
        b'<doclang><text>First page.</text><page_break/><picture><src uri="assets/chart.svg"/></picture></doclang>'
    )
    content_types = b"""<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="svg" ContentType="image/svg+xml"/>
  <Default Extension="png" ContentType="image/png"/>
  <Override PartName="/document.xml" ContentType="application/vnd.doclang.document+xml"/>
</Types>"""
    relationships = b"""<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://doclang.ai/ns/package/2026/relationships/document" Target="document.xml"/>
</Relationships>"""
    payload = BytesIO()
    with ZipFile(payload, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", relationships)
        archive.writestr("document.xml", document)
        archive.writestr("assets/chart.svg", b'<svg xmlns="http://www.w3.org/2000/svg"/>')
        archive.writestr("pages/2.png", b"not-decoded-by-ingest")
    artifact = SourceArtifact.from_bytes(
        payload.getvalue(),
        source_form=SourceForm.DOCLANG_ARCHIVE,
        source_name="normative.dclx",
        media_type="application/vnd.doclang.archive+zip",
    )
    inventory, contract = inventory_source(artifact)
    archive_assets = {item.item_id for item in inventory if item.classification is ContentClass.ASSET}
    assert archive_assets == {"archive:assets/chart.svg", "archive:pages/2.png"}
    assert contract.upstream_version == "0.7.3"
