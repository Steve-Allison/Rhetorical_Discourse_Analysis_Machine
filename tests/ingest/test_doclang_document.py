"""Validated private document ownership and exact fragment lookup."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from rdam.ingest.doclang.document import DoclangDocument, ElementTextSlot, NonElementTailSlot
from rdam.ingest.doclang.errors import InvalidDoclangError
from tests.ingest.production_ingest.test_doclang_complex import build_doclang_archive


def test_archive_retains_original_document_bytes_and_tree_paths() -> None:
    xml = Path("tests/fixtures/doclang/ok_no_namespace.dclg").read_bytes()
    doc = DoclangDocument.load(build_doclang_archive(document=xml), archive=True)
    assert doc.xml_bytes == xml
    assert doc.element("/doclang[1]") is doc.root
    assert doc.members
    for node, path in doc.paths.items():
        assert doc.element(path) is node


def test_fragment_resolution_preserves_unicode_whitespace_and_non_element_tails() -> None:
    xml = "<doclang><text> α<!-- comment --> β<?target value?> γ</text></doclang>".encode()
    doc = DoclangDocument.load(xml)
    path = "/doclang[1]/text[1]"
    assert doc.resolve_fragment(ElementTextSlot(path, "text")) == " α"
    assert doc.resolve_fragment(NonElementTailSlot(path, 0, "comment")) == " β"
    assert doc.resolve_fragment(NonElementTailSlot(path, 1, "processing_instruction")) == " γ"
    for selector in (
        ElementTextSlot(path, "tail"),
        NonElementTailSlot(path, 9, "comment"),
        NonElementTailSlot(path, 0, "processing_instruction"),
    ):
        with pytest.raises(LookupError):
            doc.resolve_fragment(selector)
    with pytest.raises(LookupError):
        doc.element("/missing[1]")
    with pytest.raises(ValueError):
        NonElementTailSlot(path, -1, "comment")


@pytest.mark.parametrize(
    "xml", (b"<", b"<doclang><unknown/></doclang>", b'<doclang><heading level="0">Bad</heading></doclang>')
)
def test_failed_validation_never_returns_partial_document(xml: bytes) -> None:
    good = DoclangDocument.load(b"<doclang><text>Good</text></doclang>")
    with pytest.raises(InvalidDoclangError, match="failed current validation"):
        DoclangDocument.load(xml)
    assert good.resolve_fragment(ElementTextSlot("/doclang[1]/text[1]", "text")) == "Good"


def test_independent_requests_have_distinct_trees_and_equal_paths() -> None:
    xml = b"<doclang><text>Content</text></doclang>"
    with ThreadPoolExecutor(max_workers=2) as pool:
        docs = list(pool.map(DoclangDocument.load, (xml, xml)))
    assert docs[0].root is not docs[1].root
    assert tuple(docs[0].elements) == tuple(docs[1].elements)
