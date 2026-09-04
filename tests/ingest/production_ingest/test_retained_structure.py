"""Cross-format retained hierarchy, table, annotation, media, and anchor fidelity."""

from io import BytesIO
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from rdam.ingest import ProductionIngestor, SourceArtifact, SourceForm
from rdam.ingest.contracts.source import (
    AnnotationRepresentation,
    ArchiveMemberAnchor,
    ContentInventoryItem,
    CrossReferenceRepresentation,
    ListRepresentation,
    MediaReferenceRepresentation,
    MetadataRepresentation,
    TableRepresentation,
)

FIXTURES = Path("tests/fixtures/production_api/retained_content")
CONTENT_TYPES = b'''<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="txt" ContentType="text/plain"/>
  <Override PartName="/document.xml" ContentType="application/vnd.doclang.document+xml"/>
</Types>'''
RELATIONSHIPS = b'''<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://doclang.ai/ns/package/2026/relationships/document" Target="document.xml"/>
</Relationships>'''


def test_plain_text_and_presegmented_edu_fixtures_preserve_exact_primary_content() -> None:
    text_source = SourceArtifact.from_path(
        FIXTURES / "mixed.txt",
        source_form=SourceForm.TEXT,
    )
    text_outcome = ProductionIngestor().prepare(text_source)
    assert text_outcome.semantic.prepared_document.text == (FIXTURES / "mixed.txt").read_text(
        encoding="utf-8"
    )

    edus = tuple(json.loads((FIXTURES / "mixed.edus.json").read_text(encoding="utf-8")))
    edu_outcome = ProductionIngestor().prepare(
        SourceArtifact.from_edus(edus, source_name="mixed.edus.json")
    )
    assert edu_outcome.semantic.prepared_document.text == " ".join(edus)


def test_gfm_preserves_front_matter_lists_tables_hierarchy_and_spans() -> None:
    outcome = ProductionIngestor().prepare(SourceArtifact.from_path(FIXTURES / "mixed.md"))
    inventory = outcome.semantic.inventory
    assert any(isinstance(item.representation, MetadataRepresentation) for item in inventory)
    assert any(isinstance(item.representation, ListRepresentation) for item in inventory)
    assert any(
        isinstance(item.representation, CrossReferenceRepresentation) or item.relationships
        for item in inventory
    )
    assert any(isinstance(item.representation, TableRepresentation) for item in inventory)
    assert all(item.anchors for item in inventory)
    _assert_hierarchy_reconciles(inventory)


def test_docling_preserves_media_hierarchy_and_page_anchors() -> None:
    outcome = ProductionIngestor().prepare(
        SourceArtifact.from_path(FIXTURES / "mixed.docling.json")
    )
    inventory = outcome.semantic.inventory
    assert any(isinstance(item.representation, MediaReferenceRepresentation) for item in inventory)
    assert any(anchor.kind == "page_box" for item in inventory for anchor in item.anchors)
    _assert_hierarchy_reconciles(inventory)


def test_doclang_preserves_tables_headers_spans_annotations_metadata_and_lists() -> None:
    outcome = ProductionIngestor().prepare(SourceArtifact.from_path(FIXTURES / "mixed.dclg"))
    inventory = outcome.semantic.inventory
    tables = [item.representation for item in inventory if isinstance(item.representation, TableRepresentation)]
    assert tables
    assert any(cell.header for table in tables for cell in table.cells)
    assert any(cell.row_span > 1 or cell.column_span > 1 for table in tables for cell in table.cells)
    assert any(isinstance(item.representation, AnnotationRepresentation) for item in inventory)
    assert any(isinstance(item.representation, MetadataRepresentation) for item in inventory)
    assert any(isinstance(item.representation, ListRepresentation) for item in inventory)
    _assert_hierarchy_reconciles(inventory)


def test_doclang_archive_retains_member_identity_and_accessible_asset() -> None:
    data = _archive_fixture()
    source = SourceArtifact.from_bytes(
        data,
        source_form=SourceForm.DOCLANG_ARCHIVE,
        source_name="mixed.dclx",
        media_type="application/vnd.doclang.archive+zip",
    )
    outcome = ProductionIngestor().prepare(source)
    assets = [item for item in outcome.semantic.inventory if item.classification.value == "asset"]
    assert assets
    assert any(
        isinstance(anchor, ArchiveMemberAnchor)
        for item in assets
        for anchor in item.anchors
    )
    assert all(item.disposition.retained for item in assets)


def _assert_hierarchy_reconciles(inventory: tuple[ContentInventoryItem, ...]) -> None:
    by_id = {item.item_id: item for item in inventory}
    for item in inventory:
        if item.parent_id is not None:
            assert item.parent_id in by_id
            assert item.item_id in by_id[item.parent_id].child_ids
        assert set(item.child_ids) <= by_id.keys()


def _archive_fixture() -> bytes:
    members = json.loads((FIXTURES / "archive-members.json").read_text(encoding="utf-8"))
    payload = BytesIO()
    with ZipFile(payload, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", CONTENT_TYPES)
        archive.writestr("_rels/.rels", RELATIONSHIPS)
        archive.writestr("document.xml", (FIXTURES / "archive-document.dclg").read_bytes())
        for member in members["members"]:
            archive.writestr(member["path"], member["content"].encode("utf-8"))
    return payload.getvalue()
