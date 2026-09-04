from io import BytesIO
from pathlib import Path
import stat
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

import pytest

from rdam.rst.doclang import loader
from rdam.rst.doclang.errors import InvalidDoclangError, UnsafeDoclangArchiveError
from rdam.ingest import SourceArtifact, SourceForm
from rdam.ingest.contracts import ContentClass
from rdam.ingest.prepare import inventory_source


FIXTURE = Path("tests/fixtures/doclang/ok_no_namespace.dclg")
CONTENT_TYPES = b"""<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="bin" ContentType="application/octet-stream"/>
  <Override PartName="/document.xml" ContentType="application/vnd.doclang.document+xml"/>
</Types>"""
RELATIONSHIPS = b"""<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://doclang.ai/ns/package/2026/relationships/document" Target="document.xml"/>
</Relationships>"""


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


def _raw_archive(entries: tuple[tuple[str | ZipInfo, bytes], ...]) -> bytes:
    payload = BytesIO()
    with ZipFile(payload, "w", compression=ZIP_DEFLATED) as archive:
        for name, data in entries:
            archive.writestr(name, data)
    return payload.getvalue()


def test_doclang_archive_validates_document_and_retains_asset_identity() -> None:
    data = _archive()
    loaded = loader.load_doclang_archive(data)
    assert loaded.document_bytes == FIXTURE.read_bytes()
    assert loaded.members[3].name == "assets/image.bin"
    artifact = SourceArtifact.from_bytes(
        data,
        source_form=SourceForm.DOCLANG_ARCHIVE,
        source_name="valid.dclx",
        media_type="application/vnd.doclang.archive+zip",
    )
    inventory, _ = inventory_source(artifact)
    assert any(item.classification is ContentClass.ASSET for item in inventory)


@pytest.mark.parametrize("name", ("../escape", "/absolute", "assets\\windows"))
def test_doclang_archive_rejects_unsafe_member_paths(name: str) -> None:
    with pytest.raises(UnsafeDoclangArchiveError, match="member path"):
        loader.load_doclang_archive(_archive(extra_name=name))


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
        loader.load_doclang_archive(payload.getvalue())


def test_doclang_archive_rejects_legacy_bare_zip() -> None:
    payload = BytesIO()
    with ZipFile(payload, "w") as archive:
        archive.writestr("document.xml", FIXTURE.read_bytes())
    with pytest.raises(InvalidDoclangError, match="missing required part"):
        loader.load_doclang_archive(payload.getvalue())


@pytest.mark.parametrize(
    ("content_types", "message"),
    [
        (CONTENT_TYPES.replace(b"application/vnd.doclang.document+xml", b"application/xml"), "document.xml"),
        (CONTENT_TYPES.replace(b'Extension="rels"', b'Extension="rels2"'), "rels content type"),
    ],
)
def test_doclang_archive_rejects_invalid_content_types(content_types: bytes, message: str) -> None:
    with pytest.raises(InvalidDoclangError, match=message):
        loader.load_doclang_archive(_archive(content_types=content_types))


@pytest.mark.parametrize(
    "relationships",
    [
        RELATIONSHIPS.replace(b"document.xml", b"other.xml"),
        RELATIONSHIPS.replace(b"relationships/document", b"relationships/legacy-document"),
        RELATIONSHIPS.replace(b'Target="document.xml"', b'Target="document.xml" TargetMode="External"'),
    ],
)
def test_doclang_archive_rejects_invalid_document_relationship(relationships: bytes) -> None:
    with pytest.raises(InvalidDoclangError, match="main-document relationship"):
        loader.load_doclang_archive(_archive(relationships=relationships))


def test_doclang_archive_requires_referenced_assets() -> None:
    document = b'<doclang><picture><src uri="assets/missing.bin"/></picture></doclang>'
    with pytest.raises(InvalidDoclangError, match="missing asset"):
        loader.load_doclang_archive(_archive(document=document))


def test_doclang_archive_rejects_page_image_beyond_markup_page_count() -> None:
    content_types = CONTENT_TYPES.replace(
        b'<Default Extension="bin" ContentType="application/octet-stream"/>',
        b'<Default Extension="png" ContentType="image/png"/>',
    )
    with pytest.raises(InvalidDoclangError, match="exceeds the document page count"):
        loader.load_doclang_archive(_archive(extra_name="pages/2.png", content_types=content_types))


def test_doclang_archive_rejects_non_zip_bytes() -> None:
    with pytest.raises(InvalidDoclangError, match="not a valid ZIP"):
        loader.load_doclang_archive(b"not a zip archive")


def test_doclang_archive_rejects_duplicate_member_names() -> None:
    entries = (
        ("[Content_Types].xml", CONTENT_TYPES),
        ("_rels/.rels", RELATIONSHIPS),
        ("document.xml", FIXTURE.read_bytes()),
        ("document.xml", FIXTURE.read_bytes()),
    )
    with pytest.warns(UserWarning, match="Duplicate name"):
        data = _raw_archive(entries)
    with pytest.raises(UnsafeDoclangArchiveError, match="duplicate"):
        loader.load_doclang_archive(data)


def test_doclang_archive_enforces_member_count_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(loader, "_MAX_ARCHIVE_MEMBERS", 3)
    with pytest.raises(UnsafeDoclangArchiveError, match="member-count"):
        loader.load_doclang_archive(_archive())


def test_doclang_archive_enforces_member_size_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(loader, "_MAX_MEMBER_BYTES", 3)
    with pytest.raises(UnsafeDoclangArchiveError, match="size limit"):
        loader.load_doclang_archive(_archive())


def test_doclang_archive_enforces_total_size_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(loader, "_MAX_TOTAL_BYTES", 1)
    with pytest.raises(UnsafeDoclangArchiveError, match="total uncompressed-size"):
        loader.load_doclang_archive(_archive())


def test_doclang_archive_enforces_compression_ratio_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(loader, "_MAX_COMPRESSION_RATIO", 2)
    with pytest.raises(UnsafeDoclangArchiveError, match="compression-ratio"):
        loader.load_doclang_archive(_archive(extra_data=b"0" * 10_000))


@pytest.mark.parametrize(
    ("flag_bits", "file_size", "compress_size", "message"),
    [
        (0x1, 0, 0, "encrypted"),
        (0, 1, 0, "contradictory compressed size"),
    ],
)
def test_doclang_archive_rejects_unsafe_zip_metadata(
    flag_bits: int,
    file_size: int,
    compress_size: int,
    message: str,
) -> None:
    entry = ZipInfo("assets/data.bin")
    entry.flag_bits = flag_bits
    entry.file_size = file_size
    entry.compress_size = compress_size
    with pytest.raises(UnsafeDoclangArchiveError, match=message):
        loader._validate_archive_member(entry, set())


@pytest.mark.parametrize(
    ("content_types", "message"),
    [
        (b"<", "not well-formed XML"),
        (CONTENT_TYPES.replace(b"Types", b"Wrong"), "wrong root element"),
        (CONTENT_TYPES.replace(b'Extension="bin"', b'Extension=""'), "invalid or duplicate Default"),
        (
            CONTENT_TYPES.replace(
                b'<Default Extension="bin" ContentType="application/octet-stream"/>',
                b'<Default Extension="rels" ContentType="application/octet-stream"/>',
            ),
            "invalid or duplicate Default",
        ),
        (CONTENT_TYPES.replace(b'PartName="/document.xml"', b'PartName="document.xml"'), "invalid or duplicate Override"),
        (
            CONTENT_TYPES.replace(
                b"</Types>",
                b'<Override PartName="/document.xml" ContentType="application/vnd.doclang.document+xml"/></Types>',
            ),
            "invalid or duplicate Override",
        ),
        (CONTENT_TYPES.replace(b"</Types>", b"<Unsupported/></Types>"), "unsupported element"),
        (
            CONTENT_TYPES.replace(b'<Default Extension="bin" ContentType="application/octet-stream"/>', b""),
            "no declared content type",
        ),
    ],
)
def test_doclang_archive_rejects_malformed_content_type_contracts(
    content_types: bytes,
    message: str,
) -> None:
    with pytest.raises(InvalidDoclangError, match=message):
        loader.load_doclang_archive(_archive(content_types=content_types))


@pytest.mark.parametrize(
    ("relationships", "message"),
    [
        (b"<", "not well-formed XML"),
        (RELATIONSHIPS.replace(b"Relationships", b"Wrong"), "wrong root element"),
        (
            RELATIONSHIPS.replace(b"</Relationships>", b"<Unsupported/></Relationships>"),
            "unsupported element",
        ),
        (RELATIONSHIPS.replace(b'Id="rId1"', b'Id=""'), "missing or duplicate Id"),
        (
            RELATIONSHIPS.replace(
                b"</Relationships>",
                b'<Relationship Id="rId1" Type="other" Target="asset.bin"/></Relationships>',
            ),
            "missing or duplicate Id",
        ),
        (
            RELATIONSHIPS.replace(
                b"</Relationships>",
                b'<Relationship Id="rId2" Type="http://doclang.ai/ns/package/2026/relationships/document" Target="document.xml"/></Relationships>',
            ),
            "exactly one main-document relationship",
        ),
    ],
)
def test_doclang_archive_rejects_malformed_relationship_contracts(
    relationships: bytes,
    message: str,
) -> None:
    with pytest.raises(InvalidDoclangError, match=message):
        loader.load_doclang_archive(_archive(relationships=relationships))


@pytest.mark.parametrize("uri", ("/assets/x.bin", "assets\\x.bin", "../x.bin", "assets/%2e%2e/x.bin"))
def test_doclang_archive_rejects_unsafe_document_asset_uris(uri: str) -> None:
    document = f'<doclang><picture><src uri="{uri}"/></picture></doclang>'.encode()
    with pytest.raises(UnsafeDoclangArchiveError, match="unsafe DocLang archive asset URI"):
        loader.load_doclang_archive(_archive(document=document))


def test_doclang_archive_allows_external_document_asset_uris() -> None:
    document = b'<doclang><picture><src uri="https://example.com/image.png"/></picture></doclang>'
    loaded = loader.load_doclang_archive(_archive(document=document))
    assert loaded.document_bytes == document


def test_doclang_archive_allows_source_without_uri_and_directory_members() -> None:
    document = b"<doclang><picture><src/></picture></doclang>"
    loaded = loader.load_doclang_archive(_archive(document=document, extra_name="assets/", extra_data=b""))
    assert loaded.document_bytes == document
    assert loaded.members[-1].name == "assets/"


@pytest.mark.parametrize("name", ("pages/0.png", "pages/01.png", "pages/one.png", "pages/1.gif"))
def test_doclang_archive_rejects_non_conforming_page_image_names(name: str) -> None:
    content_types = CONTENT_TYPES.replace(
        b'<Default Extension="bin" ContentType="application/octet-stream"/>',
        b'<Default Extension="png" ContentType="image/png"/><Default Extension="gif" ContentType="image/gif"/>',
    )
    with pytest.raises(InvalidDoclangError, match="non-conforming part name"):
        loader.load_doclang_archive(_archive(extra_name=name, content_types=content_types))
