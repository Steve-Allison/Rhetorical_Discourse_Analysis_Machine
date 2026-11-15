"""Private plain-text and presegmented-EDU harvesters backed by native dclq/DocLang."""

from importlib.metadata import version
from pathlib import Path

from lxml import etree

from rdam._version import PACKAGE_NAME
from rdam.ingest.contracts.legacy import (
    AnchorKind,
    AuthorshipRole,
    ContentClass,
    ContentInventoryItem,
    NativeAnchor,
    PreparedRange,
    SourceArtifact,
    SourceContractIdentity,
    SourceForm,
)
from rdam.ingest.identity import semantic_sha256, sha256_file

_DOCLANG_NS = "https://www.doclang.ai/ns/v0"
_XML_STRIP_TABLE = dict.fromkeys(
    [*(code for code in range(0x20) if code not in (0x09, 0x0A, 0x0D)), 0xFFFE, 0xFFFF],
    None,
)


def _xml_safe_text(text: str) -> str:
    return text.translate(_XML_STRIP_TABLE)


def _synthesize_doclang_text_xpath(text: str) -> str:
    from dclq.document import LoadedDocument

    root = etree.Element(f"{{{_DOCLANG_NS}}}doclang", nsmap={None: _DOCLANG_NS}, version="0.9")
    node = etree.SubElement(root, f"{{{_DOCLANG_NS}}}text")
    node.text = _xml_safe_text(text)
    xml_bytes = etree.tostring(root, encoding="utf-8", xml_declaration=True)
    loaded = LoadedDocument.load("-", stdin_bytes=xml_bytes, validate=False)
    return loaded.units[0].xpath if loaded.units else "/d:doclang/d:text[1]"


def inventory_source(
    artifact: SourceArtifact,
) -> tuple[tuple[ContentInventoryItem, ...], SourceContractIdentity]:
    """Validate current source contract and inventory every semantic item."""

    match artifact.source_form:
        case SourceForm.TEXT:
            return _inventory_text(artifact)
        case SourceForm.EDUS:
            return _inventory_edus(artifact)
        case SourceForm.DOCLANG_XML | SourceForm.DOCLANG_ARCHIVE:
            raise ValueError("DocLang requires the current inventory adapter")


def _inventory_text(
    artifact: SourceArtifact,
) -> tuple[tuple[ContentInventoryItem, ...], SourceContractIdentity]:
    text = (artifact.raw_bytes or b"").decode("utf-8")
    items: tuple[ContentInventoryItem, ...]
    if text.strip():
        dclq_xpath = _synthesize_doclang_text_xpath(text)
        items = (
            ContentInventoryItem(
                item_id="text:document",
                parent_id=None,
                content_class=ContentClass.PARAGRAPH,
                authorship_role=AuthorshipRole.AUTHORED,
                text=text,
                native_anchors=(
                    NativeAnchor(
                        artifact_id=artifact.source_id,
                        item_id="text:document",
                        kind=AnchorKind.CHARACTER,
                        selector=f"char=0,{len(text)}",
                        range=PreparedRange(start=0, end=len(text)),
                        quote=text,
                    ),
                ),
                attributes=(("dclq_xpath", dclq_xpath),),
                inventory_adapter="isanlp_rst.ingest.text/v1",
            ),
        )
    else:
        items = ()
    return items, _builtin_contract("plain_text", "isanlp_rst.ingest.text/v1")


def _inventory_edus(
    artifact: SourceArtifact,
) -> tuple[tuple[ContentInventoryItem, ...], SourceContractIdentity]:
    items = tuple(
        ContentInventoryItem(
            item_id=f"edu:{index}",
            parent_id=None,
            content_class=ContentClass.PARAGRAPH,
            authorship_role=AuthorshipRole.AUTHORED,
            text=text,
            native_anchors=(
                NativeAnchor(
                    artifact_id=artifact.source_id,
                    item_id=f"edu:{index}",
                    kind=AnchorKind.ITEM,
                    selector=f"edu={index}",
                    quote=text,
                ),
            ),
            inventory_adapter="isanlp_rst.ingest.edus/v1",
        )
        for index, text in enumerate(artifact.edus or ())
    )
    return items, _builtin_contract("presegmented_edus", "isanlp_rst.ingest.edus/v1")


def _builtin_contract(family: str, adapter: str) -> SourceContractIdentity:
    return SourceContractIdentity(
        family=family,
        validator_distribution=PACKAGE_NAME,
        validator_version=version(PACKAGE_NAME),
        validator_digest=semantic_sha256({"adapter": adapter, "file": _adapter_digest(Path(__file__))}),
    )


def _adapter_digest(*paths: Path) -> str:
    return semantic_sha256(tuple((path.name, sha256_file(path)) for path in paths))


__all__ = ["inventory_source"]
