from io import BytesIO
from pathlib import Path
import stat
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

import pytest

from isanlp_rst.doclang.errors import UnsafeDoclangArchiveError
from isanlp_rst.doclang.errors import InvalidDoclangError
from isanlp_rst.doclang.loader import load_doclang_archive
from isanlp_rst.ingest import SourceArtifact, SourceForm
from isanlp_rst.ingest.contracts import ContentClass
from isanlp_rst.ingest.prepare import inventory_source


FIXTURE = Path("tests/fixtures/doclang/ok_no_namespace.dclg")
CONTENT_TYPES = b'''<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="bin" ContentType="application/octet-stream"/>
  <Override PartName="/document.xml" ContentType="application/vnd.doclang.document+xml"/>
</Types>'''
RELATIONSHIPS = b'''<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://doclang.ai/ns/package/2026/relationships/document" Target="document.xml"/>
</Relationships>'''


def _archive(
    *,
    extra_name: str = "assets/image.bin",
    extra_data: bytes = b"asset",
    content_types: bytes = CONTENT_TYPES,
    relationships: bytes = RELATIONSHIPS,
    document: bytes | None = None,
) -> bytes:
    payload = BytesIO()
    with ZipFile(payload, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", relationships)
        archive.writestr("document.xml", document or FIXTURE.read_bytes())
        archive.writestr(extra_name, extra_data)
    return payload.getvalue()


def test_doclang_archive_validates_document_and_retains_asset_identity() -> None:
    data = _archive()
    loaded = load_doclang_archive(data)
    assert loaded.document_bytes == FIXTURE.read_bytes()
    assert loaded.members[3].name == "assets/image.bin"
    artifact = SourceArtifact.from_bytes(
        data,
        source_form=SourceForm.DOCLANG_ARCHIVE,
        source_name="valid.dclx",
        media_type="application/vnd.doclang.archive+zip",
    )
    inventory, _ = inventory_source(artifact)
    assert any(item.content_class is ContentClass.ASSET for item in inventory)


@pytest.mark.parametrize("name", ("../escape", "/absolute", "assets\\windows"))
def test_doclang_archive_rejects_unsafe_member_paths(name: str) -> None:
    with pytest.raises(UnsafeDoclangArchiveError, match="member path"):
        load_doclang_archive(_archive(extra_name=name))


def test_doclang_archive_rejects_symlink_members() -> None:
    payload = BytesIO()
    link = ZipInfo("assets/link")
    link.external_attr = (stat.S_IFLNK | 0o777) << 16
    with ZipFile(payload, "w") as archive:
        archive.writestr("[Content_Types].xml", CONTENT_TYPES)
        archive.writestr("_rels/.rels", RELATIONSHIPS)
        archive.writestr("document.xml", FIXTURE.read_bytes())
        archive.writestr(link, "target")
    with pytest.raises(UnsafeDoclangArchiveError, match="symbolic link"):
        load_doclang_archive(payload.getvalue())


def test_doclang_archive_rejects_legacy_bare_zip() -> None:
    payload = BytesIO()
    with ZipFile(payload, "w") as archive:
        archive.writestr("document.xml", FIXTURE.read_bytes())
    with pytest.raises(InvalidDoclangError, match="missing required part"):
        load_doclang_archive(payload.getvalue())


@pytest.mark.parametrize(
    ("content_types", "message"),
    [
        (CONTENT_TYPES.replace(b"application/vnd.doclang.document+xml", b"application/xml"), "document.xml"),
        (CONTENT_TYPES.replace(b"Extension=\"rels\"", b"Extension=\"rels2\""), "rels content type"),
    ],
)
def test_doclang_archive_rejects_invalid_content_types(content_types: bytes, message: str) -> None:
    with pytest.raises(InvalidDoclangError, match=message):
        load_doclang_archive(_archive(content_types=content_types))


@pytest.mark.parametrize(
    "relationships",
    [
        RELATIONSHIPS.replace(b"document.xml", b"other.xml"),
        RELATIONSHIPS.replace(b"relationships/document", b"relationships/legacy-document"),
        RELATIONSHIPS.replace(b"Target=\"document.xml\"", b"Target=\"document.xml\" TargetMode=\"External\""),
    ],
)
def test_doclang_archive_rejects_invalid_document_relationship(relationships: bytes) -> None:
    with pytest.raises(InvalidDoclangError, match="main-document relationship"):
        load_doclang_archive(_archive(relationships=relationships))


def test_doclang_archive_requires_referenced_assets() -> None:
    document = b"<doclang><picture><src uri=\"assets/missing.bin\"/></picture></doclang>"
    with pytest.raises(InvalidDoclangError, match="missing asset"):
        load_doclang_archive(_archive(document=document))


def test_doclang_archive_rejects_page_image_beyond_markup_page_count() -> None:
    content_types = CONTENT_TYPES.replace(
        b'<Default Extension="bin" ContentType="application/octet-stream"/>',
        b'<Default Extension="png" ContentType="image/png"/>',
    )
    with pytest.raises(InvalidDoclangError, match="exceeds the document page count"):
        load_doclang_archive(
            _archive(extra_name="pages/2.png", content_types=content_types)
        )
