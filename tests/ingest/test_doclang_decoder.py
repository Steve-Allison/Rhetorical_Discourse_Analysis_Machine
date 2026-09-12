"""Normative mixed-content and merge regressions through real preparation."""

from pathlib import Path
import sys
from types import FrameType

import pytest

from rdam.ingest import ProductionIngestor, SourceArtifact, SourceForm, ProductionIngestError
from rdam.ingest.contracts.source import TableRepresentation
from rdam.ingest.prepare import inventory_source
from rdam.ingest.doclang.document import DoclangDocument
from rdam.ingest.doclang.decoder import decode_document
from rdam.ingest.doclang.errors import InvalidDoclangError
from tests.ingest.production_ingest.test_doclang_complex import build_doclang_archive


def artifact(body: str) -> SourceArtifact:
    return SourceArtifact.from_bytes(
        f"<doclang>{body}</doclang>".encode(), source_form=SourceForm.DOCLANG_XML, source_name="specimen.dclg"
    )


def test_metadata_tails_inline_content_and_comments_are_emitted_once() -> None:
    source = artifact(
        "<text><description>Derived</description> α<bold>β</bold> γ<!-- comment --> δ<?target value?> ε</text>"
    )
    result = ProductionIngestor().prepare(source)
    assert result.semantic.prepared_document.text == "αβ γ δ ε"
    doc = DoclangDocument.load(source.raw_bytes or b"")
    text = next(item for item in decode_document(doc) if item.tag == "text")
    assert text.surface is not None
    assert len({fragment.selector for fragment in text.surface.fragments}) == len(text.surface.fragments)
    for fragment in text.surface.fragments:
        assert doc.resolve_fragment(fragment.selector) == fragment.text
    for span in text.surface.ranges:
        assert (
            text.surface.text[span.surface_start : span.surface_end]
            == span.fragment.text[span.fragment_start : span.fragment_end]
        )
    encoded = result.model_dump_json()
    assert "element_slot" not in encoded and "non_element_tail" not in encoded


@pytest.mark.parametrize(
    "body",
    (
        '<list><ldiv/><location value="1"/><location value="2"/><location value="3"/><location value="4"/>First<ldiv/><content>Second</content></list>',
        "<list><ldiv/><text>First</text><ldiv/><text>Second</text></list>",
    ),
)
def test_raw_and_wrapped_lists_prepare_each_item_once(body: str) -> None:
    result = ProductionIngestor().prepare(artifact(body))
    assert result.semantic.prepared_document.text == "First\n\nSecond"


def test_table_metadata_is_excluded_and_wrapper_tail_is_not_duplicated() -> None:
    source = artifact(
        "<table><fcel/><text><description>Derived</description>A<bold>B</bold></text>C<fcel/>D<nl/></table>"
    )
    inventory, _ = inventory_source(source)
    table = next(item.representation for item in inventory if isinstance(item.representation, TableRepresentation))
    assert [(cell.row, cell.column, cell.text) for cell in table.cells] == [(0, 0, "ABC"), (0, 1, "D")]
    assert table.cells[0].linked_item_ids == ("/doclang[1]/table[1]/text[1]",)


def test_rectangular_merge_has_one_owner_and_exact_spans() -> None:
    source = artifact("<table><ched/>A<lcel/><fcel/>B<nl/><ucel/><xcel/><fcel/>C<nl/></table>")
    inventory, _ = inventory_source(source)
    table = next(item.representation for item in inventory if isinstance(item.representation, TableRepresentation))
    assert [
        (cell.row, cell.column, cell.row_span, cell.column_span, cell.header, cell.text) for cell in table.cells
    ] == [(0, 0, 2, 2, True, "A"), (0, 2, 1, 1, False, "B"), (1, 2, 1, 1, False, "C")]


@pytest.mark.parametrize(
    "cells",
    (
        "<lcel/><nl/>",
        "<ucel/><nl/>",
        "<xcel/><nl/>",
        "<fcel/>A<fcel/>B<nl/><fcel/>C<xcel/><nl/>",
        "<fcel/>A<lcel/><nl/><ucel/><fcel/>B<nl/>",
        "<fcel/>A<lcel/>Bad<nl/>",
    ),
)
def test_invalid_merge_geometry_fails_at_public_classification(cells: str) -> None:
    source = artifact(f"<table>{cells}</table>")
    with pytest.raises(InvalidDoclangError):
        inventory_source(source)
    with pytest.raises(ProductionIngestError) as raised:
        ProductionIngestor().prepare(source)
    assert raised.value.failure.failed_stage.value == "classification"
    assert raised.value.failure.category.value == "malformed_input"


def test_nested_tables_own_their_coordinates() -> None:
    source = artifact("<table><fcel/><text>A</text><table><fcel/>B<fcel/>C<nl/></table><fcel/>D<nl/></table>")
    inventory, _ = inventory_source(source)
    tables = [item.representation for item in inventory if isinstance(item.representation, TableRepresentation)]
    assert [[(cell.row, cell.column, cell.text) for cell in table.cells] for table in tables] == [
        [(0, 0, "ABC"), (0, 1, "D")],
        [(0, 0, "B"), (0, 1, "C")],
    ]


def test_archive_uses_one_rdam_document_parse_and_no_legacy_conversion() -> None:
    source = SourceArtifact.from_bytes(
        build_doclang_archive(document=b"<doclang><text>Body</text></doclang>"),
        source_form=SourceForm.DOCLANG_ARCHIVE,
        source_name="specimen.dclx",
    )
    calls: list[tuple[str, str]] = []

    def observe(frame: FrameType, event: str, _argument: object) -> None:
        if event == "call":
            calls.append((frame.f_code.co_filename, frame.f_code.co_name))

    previous = sys.getprofile()
    try:
        sys.setprofile(observe)
        ProductionIngestor().prepare(source)
    finally:
        sys.setprofile(previous)
    assert sum(name == "parse_control_xml" and Path(file).name == "loader.py" for file, name in calls) == 3
    assert not any(name in {"_legacy_artifact", "_translate_item", "_translate_anchor"} for _, name in calls)


def test_empty_and_whitespace_surfaces_have_no_fabricated_ranges() -> None:
    doc = DoclangDocument.load(b"<doclang><text>   </text><text/></doclang>")
    for item in decode_document(doc):
        if item.surface is not None:
            assert item.text is None
            assert item.surface.ranges == ()


def test_nested_primary_components_are_not_repeated_in_prepared_text() -> None:
    source = artifact("<list><ldiv/><text>A<list><ldiv/><text>B</text></list>C</text></list>")
    result = ProductionIngestor().prepare(source)
    assert result.semantic.prepared_document.text == "ABC"
    assert len(result.semantic.inventory) == 7


def test_nested_table_does_not_leak_into_primary_prose() -> None:
    source = artifact("<text>A<table><fcel/>Private cell<nl/></table>B</text>")
    result = ProductionIngestor().prepare(source)
    assert result.semantic.prepared_document.text == "AB"
    table = next(
        item.representation
        for item in result.semantic.inventory
        if isinstance(item.representation, TableRepresentation)
    )
    assert table.cells[0].text == "Private cell"


def test_mixed_raw_wrapped_list_keeps_tail_after_its_wrapper() -> None:
    result = ProductionIngestor().prepare(artifact("<list><ldiv/>A<text>B</text>C<ldiv/>D</list>"))
    assert result.semantic.prepared_document.text == "A\n\nBC\n\nD"


def test_nested_list_tail_follows_the_last_nested_component() -> None:
    result = ProductionIngestor().prepare(artifact("<list><ldiv/>A<list><ldiv/>B</list>C<ldiv/>D</list>"))
    assert result.semantic.prepared_document.text == "A\n\nBC\n\nD"


def test_shared_front_and_back_matter_policy_is_preserved() -> None:
    source = artifact(
        "<heading>Title</heading><text>Author</text><heading>Abstract</heading><text>Body</text><heading>References</heading><list><ldiv/>Citation</list>"
    )
    result = ProductionIngestor().prepare(source)
    assert result.semantic.prepared_document.text == "Title\n\nAbstract\n\nBody"
    by_id = {item.item_id: item for item in result.semantic.inventory}
    assert by_id["/doclang[1]/text[1]"].classification.value == "metadata"
    assert by_id["/doclang[1]/list[1]/ldiv[1]"].classification.value == "navigation"


def test_cdata_and_normalization_keep_decoded_character_positions() -> None:
    source = artifact("<text><![CDATA[ e\u0301 <literal> ]]><bold>β</bold> Ω</text>")
    result = ProductionIngestor().prepare(source)
    assert result.semantic.prepared_document.text == "e\u0301 <literal> β Ω"
    doc = DoclangDocument.load(source.raw_bytes or b"")
    surface = next(item.surface for item in decode_document(doc) if item.tag == "text")
    assert surface is not None
    for span in surface.ranges:
        assert (
            surface.text[span.surface_start : span.surface_end]
            == doc.resolve_fragment(span.fragment.selector)[span.fragment_start : span.fragment_end]
        )
