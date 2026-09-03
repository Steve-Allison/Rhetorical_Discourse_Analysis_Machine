"""Private DocLang addressing and bounded archive loading for ingest.

The ``doclang`` PyPI package (``doclang-project/doclang``) is
validator-only — it exposes ``validate(path)`` and ``ValidationError``
and has no DOM. We parse the XML ourselves with ``lxml`` and provide
the canonical addressing helper ``local_path`` (verified Phase 1 to
round-trip against the pinned upstream fixture manifest).

``lxml.etree.ElementTree.getpath()`` is NOT used: on default-namespaced
documents it emits ``/*/*[N]`` wildcards (`spec.md:219-241` recommends a
default namespace, so this is the common case). The local-name path
``/doclang[1]/heading[2]`` is namespace-agnostic and human-readable.

"""

from dataclasses import dataclass
from collections import defaultdict
import hashlib
from io import BytesIO
from pathlib import PurePosixPath
import re
import stat
from urllib.parse import unquote, urlsplit
from zipfile import BadZipFile, ZipFile, ZipInfo
from collections.abc import Iterator, Mapping
from typing import Protocol, TypeVar, cast, overload

from lxml import etree

from .errors import InvalidDoclangError, UnsafeDoclangArchiveError

_MAX_ARCHIVE_MEMBERS = 10_000
_MAX_MEMBER_BYTES = 128 * 1024 * 1024
_MAX_TOTAL_BYTES = 512 * 1024 * 1024
_MAX_COMPRESSION_RATIO = 200
_CONTENT_TYPES_PART = "[Content_Types].xml"
_RELATIONSHIPS_PART = "_rels/.rels"
_DOCUMENT_PART = "document.xml"
_CONTENT_TYPES_NAMESPACE = "http://schemas.openxmlformats.org/package/2006/content-types"
_RELATIONSHIPS_NAMESPACE = "http://schemas.openxmlformats.org/package/2006/relationships"
_DOCUMENT_CONTENT_TYPE = "application/vnd.doclang.document+xml"
_RELATIONSHIPS_CONTENT_TYPE = "application/vnd.openxmlformats-package.relationships+xml"
_DOCUMENT_RELATIONSHIP_TYPE = "http://doclang.ai/ns/package/2026/relationships/document"
_PAGE_IMAGE = re.compile(r"pages/([1-9][0-9]*)\.(png|jpg|jpeg|webp)", re.IGNORECASE)
_DefaultT = TypeVar("_DefaultT")


class XmlElement(Protocol):
    """Public structural type for the private lxml element implementation."""

    @property
    def tag(self) -> object: ...

    @property
    def text(self) -> str | None: ...

    @property
    def tail(self) -> str | None: ...

    @property
    def attrib(self) -> Mapping[str, str]: ...

    def __iter__(self) -> Iterator[XmlElement]: ...

    def getparent(self) -> XmlElement | None: ...

    @overload
    def get(self, key: str) -> str | None: ...

    @overload
    def get(self, key: str, default: _DefaultT) -> str | _DefaultT: ...

    def iter(self) -> Iterator[XmlElement]: ...


@dataclass(frozen=True, slots=True)
class DoclangArchiveMember:
    """Identity of one bounded archive member, without extracted content."""

    name: str
    sha256: str
    size_bytes: int
    compressed_size_bytes: int


@dataclass(frozen=True, slots=True)
class DoclangArchive:
    """Validated archive container material required by production inventory."""

    document_bytes: bytes
    members: tuple[DoclangArchiveMember, ...]


def local_name(element: XmlElement) -> str:
    """Return the element's tag with any XML namespace stripped."""
    tag = element.tag
    if isinstance(tag, str) and tag.startswith("{"):
        return tag.split("}", 1)[1]
    return tag if isinstance(tag, str) else ""


def local_path(element: XmlElement) -> str:
    """Return a local-name canonical XPath for ``element``.

    Each step is ``local_name[i]`` where ``i`` is the 1-based position
    among siblings sharing the same local name (case-sensitive). The
    output is identical regardless of whether the source declares an
    XML namespace; verified against the pinned upstream valid-fixture manifest.

    Example output: ``"/doclang[1]/heading[2]/text[1]"``.
    """
    parts: list[str] = []
    cur = element
    while isinstance(cur.tag, str):
        parent = cur.getparent()
        my_local = local_name(cur)
        if parent is None:
            parts.append(f"/{my_local}[1]")
            break
        same = [c for c in parent if isinstance(c.tag, str) and local_name(c) == my_local]
        pos = same.index(cur) + 1
        parts.append(f"/{my_local}[{pos}]")
        cur = parent
    return "".join(reversed(parts))


def local_path_index(root: XmlElement) -> dict[XmlElement, str]:
    """Index canonical local-name paths for an element tree in one pass."""

    if not isinstance(root.tag, str):
        return {}
    result = {root: f"/{local_name(root)}[1]"}
    stack = [root]
    while stack:
        parent = stack.pop()
        positions: defaultdict[str, int] = defaultdict(int)
        children: list[XmlElement] = []
        for child in parent:
            if not isinstance(child.tag, str):
                continue
            name = local_name(child)
            positions[name] += 1
            result[child] = f"{result[parent]}/{name}[{positions[name]}]"
            children.append(child)
        stack.extend(reversed(children))
    return result


def load_doclang_archive(data: bytes) -> DoclangArchive:
    """Validate and read a bounded current-contract DocLang OPC package."""

    try:
        archive = ZipFile(BytesIO(data))
    except BadZipFile as exc:
        raise InvalidDoclangError("DocLang archive is not a valid ZIP container") from exc
    with archive:
        entries = archive.infolist()
        if len(entries) > _MAX_ARCHIVE_MEMBERS:
            raise UnsafeDoclangArchiveError("DocLang archive exceeds the member-count limit")
        seen: set[str] = set()
        total_bytes = 0
        identities: list[DoclangArchiveMember] = []
        package_parts: dict[str, bytes] = {}
        for entry in entries:
            _validate_archive_member(entry, seen)
            total_bytes += entry.file_size
            if total_bytes > _MAX_TOTAL_BYTES:
                raise UnsafeDoclangArchiveError("DocLang archive exceeds the total uncompressed-size limit")
            with archive.open(entry, "r") as stream:
                member_data = stream.read(_MAX_MEMBER_BYTES + 1)
            if len(member_data) != entry.file_size or len(member_data) > _MAX_MEMBER_BYTES:
                raise UnsafeDoclangArchiveError(f"DocLang archive member {entry.filename!r} exceeds its declared limit")
            identities.append(
                DoclangArchiveMember(
                    name=entry.filename,
                    sha256=hashlib.sha256(member_data).hexdigest(),
                    size_bytes=len(member_data),
                    compressed_size_bytes=entry.compress_size,
                )
            )
            if entry.filename in {_CONTENT_TYPES_PART, _RELATIONSHIPS_PART, _DOCUMENT_PART}:
                package_parts[entry.filename] = member_data
        missing = {_CONTENT_TYPES_PART, _RELATIONSHIPS_PART, _DOCUMENT_PART} - package_parts.keys()
        if missing:
            raise InvalidDoclangError(f"DocLang OPC package is missing required part(s): {', '.join(sorted(missing))}")
        document_root = _parse_control_xml(package_parts[_DOCUMENT_PART], part_name=_DOCUMENT_PART)
        member_names = frozenset(entry.filename for entry in entries if not entry.is_dir())
        _validate_content_types(package_parts[_CONTENT_TYPES_PART], member_names)
        _validate_root_relationships(package_parts[_RELATIONSHIPS_PART])
        _validate_document_references(document_root, member_names)
        _validate_page_images(document_root, member_names)
        return DoclangArchive(document_bytes=package_parts[_DOCUMENT_PART], members=tuple(identities))


def _parse_control_xml(data: bytes, *, part_name: str) -> XmlElement:
    parser = etree.XMLParser(
        resolve_entities=False,
        no_network=True,
        load_dtd=False,
        recover=False,
        huge_tree=False,
    )
    try:
        return cast(XmlElement, etree.fromstring(data, parser=parser))
    except etree.XMLSyntaxError as exc:
        raise InvalidDoclangError(f"DocLang OPC part {part_name!r} is not well-formed XML") from exc


def _validate_content_types(data: bytes, member_names: frozenset[str]) -> None:
    root = _parse_control_xml(data, part_name=_CONTENT_TYPES_PART)
    if root.tag != f"{{{_CONTENT_TYPES_NAMESPACE}}}Types":
        raise InvalidDoclangError("DocLang OPC content-types part has the wrong root element")
    defaults: dict[str, str] = {}
    overrides: dict[str, str] = {}
    for child in root:
        if child.tag == f"{{{_CONTENT_TYPES_NAMESPACE}}}Default":
            extension = (child.get("Extension") or "").lower()
            content_type = child.get("ContentType") or ""
            if not extension or not content_type or extension in defaults:
                raise InvalidDoclangError("DocLang OPC content-types part has an invalid or duplicate Default")
            defaults[extension] = content_type
        elif child.tag == f"{{{_CONTENT_TYPES_NAMESPACE}}}Override":
            part_name = child.get("PartName") or ""
            content_type = child.get("ContentType") or ""
            if not part_name.startswith("/") or not content_type or part_name in overrides:
                raise InvalidDoclangError("DocLang OPC content-types part has an invalid or duplicate Override")
            overrides[part_name] = content_type
        else:
            raise InvalidDoclangError("DocLang OPC content-types part contains an unsupported element")
    if overrides.get(f"/{_DOCUMENT_PART}") != _DOCUMENT_CONTENT_TYPE:
        raise InvalidDoclangError(
            f"DocLang OPC content-types part must declare /document.xml as {_DOCUMENT_CONTENT_TYPE}"
        )
    if defaults.get("rels") != _RELATIONSHIPS_CONTENT_TYPE:
        raise InvalidDoclangError("DocLang OPC content-types part must declare the .rels content type")
    for member_name in member_names - {_CONTENT_TYPES_PART}:
        extension = (
            "rels" if member_name.endswith(".rels") else PurePosixPath(member_name).suffix.removeprefix(".").lower()
        )
        if f"/{member_name}" not in overrides and (not extension or extension not in defaults):
            raise InvalidDoclangError(f"DocLang OPC part has no declared content type: {member_name!r}")


def _validate_root_relationships(data: bytes) -> None:
    root = _parse_control_xml(data, part_name=_RELATIONSHIPS_PART)
    if root.tag != f"{{{_RELATIONSHIPS_NAMESPACE}}}Relationships":
        raise InvalidDoclangError("DocLang OPC root relationships part has the wrong root element")
    document_relationships: list[XmlElement] = []
    relationship_ids: set[str] = set()
    for child in root:
        if child.tag != f"{{{_RELATIONSHIPS_NAMESPACE}}}Relationship":
            raise InvalidDoclangError("DocLang OPC root relationships part contains an unsupported element")
        relationship_id = child.get("Id") or ""
        if not relationship_id or relationship_id in relationship_ids:
            raise InvalidDoclangError("DocLang OPC root relationships have a missing or duplicate Id")
        relationship_ids.add(relationship_id)
        if child.get("Type") == _DOCUMENT_RELATIONSHIP_TYPE:
            document_relationships.append(child)
    if len(document_relationships) != 1:
        raise InvalidDoclangError("DocLang OPC package must have exactly one main-document relationship")
    relationship = document_relationships[0]
    if relationship.get("Target") != _DOCUMENT_PART or relationship.get("TargetMode") not in {None, "Internal"}:
        raise InvalidDoclangError("DocLang OPC main-document relationship must target internal document.xml")


def _validate_document_references(root: XmlElement, member_names: frozenset[str]) -> None:
    for element in root.iter():
        if not isinstance(element.tag, str) or local_name(element) != "src":
            continue
        uri = element.get("uri")
        if not uri:
            continue
        parsed = urlsplit(uri)
        if parsed.scheme or parsed.netloc or not parsed.path:
            continue
        decoded_path = unquote(parsed.path)
        path = PurePosixPath(decoded_path)
        if decoded_path.startswith("/") or "\\" in decoded_path or ".." in path.parts:
            raise UnsafeDoclangArchiveError(f"unsafe DocLang archive asset URI: {uri!r}")
        if decoded_path not in member_names:
            raise InvalidDoclangError(f"DocLang archive references a missing asset part: {decoded_path!r}")


def _validate_page_images(root: XmlElement, member_names: frozenset[str]) -> None:
    page_count = 1 + sum(1 for child in root if isinstance(child.tag, str) and local_name(child) == "page_break")
    for member_name in member_names:
        if not member_name.startswith("pages/"):
            continue
        match = _PAGE_IMAGE.fullmatch(member_name)
        if match is None:
            raise InvalidDoclangError(f"DocLang page image has a non-conforming part name: {member_name!r}")
        if int(match.group(1)) > page_count:
            raise InvalidDoclangError(
                f"DocLang page image {member_name!r} exceeds the document page count {page_count}"
            )


def _validate_archive_member(entry: ZipInfo, seen: set[str]) -> None:
    name = entry.filename
    path = PurePosixPath(name)
    if not name or name.startswith("/") or "\\" in name or ".." in path.parts or path.is_absolute():
        raise UnsafeDoclangArchiveError(f"unsafe DocLang archive member path: {name!r}")
    if name in seen:
        raise UnsafeDoclangArchiveError(f"duplicate DocLang archive member path: {name!r}")
    seen.add(name)
    unix_mode = entry.external_attr >> 16
    if stat.S_ISLNK(unix_mode):
        raise UnsafeDoclangArchiveError(f"DocLang archive member is a symbolic link: {name!r}")
    if entry.flag_bits & 0x1:
        raise UnsafeDoclangArchiveError(f"encrypted DocLang archive member is unsupported: {name!r}")
    if entry.is_dir():
        return
    if entry.file_size > _MAX_MEMBER_BYTES:
        raise UnsafeDoclangArchiveError(f"DocLang archive member exceeds the size limit: {name!r}")
    if entry.compress_size == 0 and entry.file_size > 0:
        raise UnsafeDoclangArchiveError(f"DocLang archive member has contradictory compressed size: {name!r}")
    if entry.compress_size and entry.file_size / entry.compress_size > _MAX_COMPRESSION_RATIO:
        raise UnsafeDoclangArchiveError(f"DocLang archive member exceeds the compression-ratio limit: {name!r}")


__all__ = [
    "DoclangArchive",
    "DoclangArchiveMember",
    "XmlElement",
    "load_doclang_archive",
    "local_name",
    "local_path",
    "local_path_index",
]
