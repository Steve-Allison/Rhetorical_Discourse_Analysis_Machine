"""Real shared preparation for every public source form."""
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

from docling_core.types.doc import DoclingDocument, DocItemLabel
import pytest

from rdam.concepts import link_inventory, link_source, validate_result
from rdam.ingest.contracts.preparation import ContentInventory
from rdam.ingest.contracts.source import SourceArtifact, SourceForm
from rdam.ingest.prepare import prepare_source
from tests.concepts.test_linking import make_index


def _source(form: SourceForm) -> SourceArtifact:
    if form is SourceForm.TEXT:
        return SourceArtifact.from_text("Known. Known.", source_name="text")
    if form is SourceForm.EDUS:
        return SourceArtifact.from_edus(("Known.", "Known."), source_name="edus")
    if form is SourceForm.MARKDOWN:
        return SourceArtifact.from_bytes(b"# Known\n\n- Known\n\n| Known | Missing |\n|---|---|\n| Known | Missing |\n", source_form=form, source_name="plate.md")
    if form is SourceForm.DOCLING_JSON:
        doc = DoclingDocument(name="test")
        doc.add_text(label=DocItemLabel.TEXT, text="Known.")
        doc.add_text(label=DocItemLabel.TEXT, text="Known.")
        return SourceArtifact.from_bytes(doc.model_dump_json().encode(), source_form=form, source_name="plate.docling.json")
    payload = Path("tests/fixtures/production_api/retained_content/archive-document.dclg").read_bytes()
    if form is SourceForm.DOCLANG_XML:
        return SourceArtifact.from_bytes(payload, source_form=form, source_name="plate.dclg")
    stream = BytesIO()
    with ZipFile(stream, "w") as archive:
        archive.writestr("[Content_Types].xml", '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="txt" ContentType="text/plain"/><Override PartName="/document.xml" ContentType="application/vnd.doclang.document+xml"/></Types>')
        archive.writestr("_rels/.rels", '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://doclang.ai/ns/package/2026/relationships/document" Target="document.xml"/></Relationships>')
        archive.writestr("document.xml", payload)
        archive.writestr("media/figure.txt", "Known")
    return SourceArtifact.from_bytes(stream.getvalue(), source_form=form, source_name="plate.zip")


@pytest.mark.parametrize("form", tuple(SourceForm))
def test_all_forms_exact_evidence_and_prepare_reuse(form: SourceForm) -> None:
    source = _source(form)
    index = make_index("Known", "document", "Known Missing")
    inventory = ContentInventory.from_preparation(prepare_source(source))
    result = link_source(source, index)
    assert result == link_inventory(inventory, index)
    validate_result(result, inventory, index)
    assert result.mentions
    assert all(mention.quote != "Known Missing" for mention in result.mentions)
    for mention in result.mentions:
        surface = next(s for s in result.surfaces if (s.item_id, s.field_pointer) == (mention.item_id, mention.field_pointer))
        assert surface.text[mention.start:mention.end] == mention.quote
    assert {surface.item_id for surface in result.surfaces} | {surface.item_id for surface in result.exclusions} == {item.item_id for item in inventory.items}
    if form in {SourceForm.TEXT, SourceForm.EDUS, SourceForm.DOCLING_JSON}:
        assert len(result.mentions) == 2
        assert len({mention.occurrence_id for mention in result.mentions}) == 2
