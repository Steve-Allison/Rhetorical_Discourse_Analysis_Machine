"""Unit tests for ``isanlp_rst.doclang.boundaries.detect_boundaries``."""

from __future__ import annotations

from pathlib import Path

import pytest
from lxml import etree

from isanlp_rst.doclang.boundaries import detect_boundaries
from isanlp_rst.doclang.loader import parse_doclang_xml

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "doclang"


def _tree(name: str) -> etree._ElementTree:
    return parse_doclang_xml(FIXTURES / name)


# --- Heading boundaries ----------------------------------------------------


def test_heading_boundary_per_heading_in_doc_order() -> None:
    """``ok_comprehensive.dclg.xml`` has 7 ``<heading>`` elements at
    various levels (verified Phase 1)."""
    result = detect_boundaries(_tree("ok_comprehensive.dclg.xml"))
    headings = [b for b in result if b.kind == "heading"]
    assert len(headings) == 7
    assert {b.id for b in headings} == {f"heading-{i}" for i in range(7)}


def test_heading_level_preserved() -> None:
    result = detect_boundaries(_tree("ok_comprehensive.dclg.xml"))
    headings = [b for b in result if b.kind == "heading"]
    levels = {b.level for b in headings}
    assert levels == {1, 2, 3}


def test_heading_includes_following_prose_xpaths() -> None:
    """Each heading owns itself plus following harvest-eligible xpaths
    until the next heading (markdown-style section bucketing)."""
    xml = (
        b'<doclang xmlns="https://www.doclang.ai/ns/v0">'
        b"<heading level=\"1\">First</heading>"
        b"<text>Prose under first.</text>"
        b"<heading level=\"1\">Second</heading>"
        b"<text>Prose under second.</text>"
        b"</doclang>"
    )
    tree = etree.ElementTree(etree.fromstring(xml))
    result = detect_boundaries(tree)
    heading_0 = next(b for b in result if b.id == "heading-0")
    heading_1 = next(b for b in result if b.id == "heading-1")
    assert "/doclang[1]/heading[1]" in heading_0.xpaths
    assert "/doclang[1]/text[1]" in heading_0.xpaths
    assert "/doclang[1]/heading[2]" in heading_1.xpaths
    assert "/doclang[1]/text[2]" in heading_1.xpaths
    assert "/doclang[1]/text[2]" not in heading_0.xpaths
    assert "/doclang[1]/text[1]" not in heading_1.xpaths


def test_heading_label_is_heading_text() -> None:
    """The fixture's first heading is ``Introduction``."""
    result = detect_boundaries(_tree("ok_comprehensive.dclg.xml"))
    heading_0 = next(b for b in result if b.id == "heading-0")
    assert heading_0.label == "Introduction"


def test_heading_non_integer_level_raises() -> None:
    """A malformed ``level`` attribute must raise — silent acceptance
    would hide a producer bug."""
    xml = b'<doclang><heading level="bogus">x</heading></doclang>'
    tree = etree.ElementTree(etree.fromstring(xml))
    with pytest.raises(ValueError, match="level=.bogus."):
        detect_boundaries(tree)


# --- Page boundaries -------------------------------------------------------


def test_page_break_partitions_body() -> None:
    """``ok_page_break_top_level`` has one ``<page_break/>`` between two
    ``<text>`` elements — must produce 2 page boundaries."""
    result = detect_boundaries(_tree("ok_page_break_top_level.dclg.xml"))
    pages = [b for b in result if b.kind == "page"]
    assert len(pages) == 2
    assert pages[0].id == "page-0"
    assert pages[1].id == "page-1"
    assert pages[0].page_no == 0
    assert pages[1].page_no == 1


def test_page_xpaths_are_per_page_partition() -> None:
    result = detect_boundaries(_tree("ok_page_break_top_level.dclg.xml"))
    pages = [b for b in result if b.kind == "page"]
    # Each page contains exactly one text element.
    assert pages[0].xpaths == ("/doclang[1]/text[1]",)
    assert pages[1].xpaths == ("/doclang[1]/text[2]",)


def test_no_page_break_no_page_boundaries() -> None:
    result = detect_boundaries(_tree("ok_no_namespace.dclg.xml"))
    pages = [b for b in result if b.kind == "page"]
    assert pages == []


# --- Group boundaries ------------------------------------------------------


def test_group_emitted_for_top_level_group() -> None:
    """``ok_comprehensive.dclg.xml`` has top-level groups."""
    result = detect_boundaries(_tree("ok_comprehensive.dclg.xml"))
    groups = [b for b in result if b.kind == "group"]
    assert len(groups) >= 1


def test_nested_group_gets_hierarchical_id() -> None:
    """When a top-level group contains a nested group, the inner gets
    ``group-N-M``."""
    xml = (
        b'<doclang xmlns="https://www.doclang.ai/ns/v0">'
        b"<group><text>outer body</text>"
        b"<group><text>inner body</text></group>"
        b"</group>"
        b"</doclang>"
    )
    tree = etree.ElementTree(etree.fromstring(xml))
    result = detect_boundaries(tree)
    groups = [b for b in result if b.kind == "group"]
    assert {b.id for b in groups} == {"group-0", "group-0-0"}


# --- Table boundaries ------------------------------------------------------


def test_table_boundary_per_table_doc_order() -> None:
    """``ok_table_rectangular`` has 3 ``<table>`` elements (per the
    Phase 1 census)."""
    result = detect_boundaries(_tree("ok_table_rectangular.dclg.xml"))
    tables = [b for b in result if b.kind == "table"]
    assert len(tables) == 3
    assert [b.id for b in tables] == [f"table-{i}" for i in range(3)]


def test_table_boundary_first_xpath_points_at_table_element() -> None:
    """Phase 9: each table boundary starts with the synthetic table xpath
    (boundary marker, no harvest span) followed by per-cell xpaths."""
    result = detect_boundaries(_tree("ok_table_rectangular.dclg.xml"))
    tables = [b for b in result if b.kind == "table"]
    for t in tables:
        # First xpath is the table element itself.
        last = t.xpaths[0].rsplit("/", 1)[-1]
        assert last.startswith("table[")
        # Subsequent xpaths are cell markers under the same table.
        cell_markers = {"ched", "fcel", "rhed", "corn"}
        for xp in t.xpaths[1:]:
            tail = xp.rsplit("/", 1)[-1]
            local = tail.split("[", 1)[0]
            assert local in cell_markers, f"unexpected cell marker: {xp}"
            # And each cell xpath sits under this same table.
            assert xp.startswith(t.xpaths[0] + "/"), f"cell {xp} not under {t.xpaths[0]}"


def test_table_boundary_excludes_ecel_and_nl() -> None:
    """``<ecel/>`` cells and ``<nl/>`` row breaks must not appear among
    boundary xpaths — they have no harvest spans, so listing them would
    be dead weight."""
    result = detect_boundaries(_tree("ok_table_rectangular.dclg.xml"))
    tables = [b for b in result if b.kind == "table"]
    for t in tables:
        for xp in t.xpaths:
            tail = xp.rsplit("/", 1)[-1]
            local = tail.split("[", 1)[0]
            assert local not in {"ecel", "nl"}, f"forbidden marker in boundary: {xp}"


# --- Field-region boundaries ----------------------------------------------


def test_field_region_boundary_emitted() -> None:
    result = detect_boundaries(
        _tree("ok_field_item_nested_descendant_key_scope.dclg.xml")
    )
    field_regions = [b for b in result if b.kind == "field_region"]
    assert len(field_regions) >= 1


# --- Document fallback -----------------------------------------------------


def test_document_fallback_when_no_structural_boundary() -> None:
    """``ok_thread.dclg.xml`` has no headings / page_breaks / groups —
    a single ``document`` boundary must cover the harvest-eligible
    xpaths."""
    result = detect_boundaries(_tree("ok_thread.dclg.xml"))
    documents = [b for b in result if b.kind == "document"]
    assert len(documents) == 1
    assert documents[0].id == "document"
    assert len(documents[0].xpaths) == 2


def test_no_document_fallback_when_headings_present() -> None:
    """``ok_comprehensive`` has headings and no pre-heading prose — a
    full-document fallback must not fire. (A leading ``document`` bucket
    is only for content that precedes the first heading.)"""
    result = detect_boundaries(_tree("ok_comprehensive.dclg.xml"))
    documents = [b for b in result if b.kind == "document"]
    assert documents == []


def test_pre_heading_content_gets_document_bucket() -> None:
    """Prose before the first heading lands in a leading ``document``
    boundary (same pattern as markdown)."""
    xml = (
        b'<doclang xmlns="https://www.doclang.ai/ns/v0">'
        b"<text>Lead-in before any heading.</text>"
        b"<heading level=\"1\">Title</heading>"
        b"<text>Under the title.</text>"
        b"</doclang>"
    )
    tree = etree.ElementTree(etree.fromstring(xml))
    result = detect_boundaries(tree)
    documents = [b for b in result if b.kind == "document"]
    assert len(documents) == 1
    assert "/doclang[1]/text[1]" in documents[0].xpaths
    heading_0 = next(b for b in result if b.id == "heading-0")
    assert "/doclang[1]/text[2]" in heading_0.xpaths
    assert "/doclang[1]/text[1]" not in heading_0.xpaths


# --- Global invariants -----------------------------------------------------


@pytest.mark.parametrize(
    "fixture_name",
    [
        "ok_comprehensive.dclg.xml",
        "ok_no_namespace.dclg.xml",
        "ok_thread.dclg.xml",
        "ok_page_break_top_level.dclg.xml",
        "ok_table_rectangular.dclg.xml",
        "ok_list_with_unwrapped_text.dclg.xml",
    ],
)
def test_all_boundary_ids_unique(fixture_name: str) -> None:
    result = detect_boundaries(_tree(fixture_name))
    ids = [b.id for b in result]
    assert len(ids) == len(set(ids)), f"duplicate boundary ids: {ids}"


@pytest.mark.parametrize(
    "fixture_name",
    [
        "ok_comprehensive.dclg.xml",
        "ok_no_namespace.dclg.xml",
        "ok_thread.dclg.xml",
        "ok_page_break_top_level.dclg.xml",
    ],
)
def test_xpaths_within_boundary_are_unique(fixture_name: str) -> None:
    result = detect_boundaries(_tree(fixture_name))
    for b in result:
        assert len(set(b.xpaths)) == len(b.xpaths), (
            f"duplicate xpaths in boundary {b.id}"
        )


def test_no_slide_or_turn_boundary_kinds() -> None:
    """DocLang does not model slides or speaker turns (Phase 0 verified).
    Boundary detection must never emit those kinds."""
    result = detect_boundaries(_tree("ok_comprehensive.dclg.xml"))
    kinds = {b.kind for b in result}
    assert "slide" not in kinds
    assert "slide-notes" not in kinds
    assert "turn" not in kinds
