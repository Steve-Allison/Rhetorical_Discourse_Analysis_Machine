"""Unit tests for ``isanlp_rst.doclang.boundaries.detect_boundaries``."""

from pathlib import Path

import pytest
from lxml import etree

from isanlp_rst.doclang.boundaries import _harvest_eligible_xpaths, detect_boundaries
from isanlp_rst.doclang.eligibility import DoclangEligibility
from isanlp_rst.doclang.errors import UnsupportedDoclangError
from isanlp_rst.doclang.harvester import harvest_doclang_text
from isanlp_rst.doclang.loader import parse_doclang_xml

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "doclang"


def _tree(name: str) -> etree._ElementTree:
    return parse_doclang_xml(FIXTURES / name)


# --- Heading boundaries ----------------------------------------------------


def test_heading_boundary_per_heading_in_doc_order() -> None:
    """``ok_comprehensive.dclg`` has 7 ``<heading>`` elements at
    various levels (verified Phase 1)."""
    result = detect_boundaries(_tree("ok_comprehensive.dclg"))
    headings = [b for b in result if b.kind == "heading"]
    assert len(headings) == 7
    assert {b.id for b in headings} == {f"heading-{i}" for i in range(7)}


def test_heading_level_preserved() -> None:
    result = detect_boundaries(_tree("ok_comprehensive.dclg"))
    headings = [b for b in result if b.kind == "heading"]
    levels = {b.level for b in headings}
    assert levels == {1, 2, 3}


def test_heading_includes_following_prose_xpaths() -> None:
    """Each heading owns itself plus following harvest-eligible xpaths
    until the next heading (markdown-style section bucketing)."""
    xml = (
        b'<doclang xmlns="https://www.doclang.ai/ns/v0">'
        b'<heading level="1">First</heading>'
        b"<text>Prose under first.</text>"
        b'<heading level="1">Second</heading>'
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
    result = detect_boundaries(_tree("ok_comprehensive.dclg"))
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
    result = detect_boundaries(_tree("ok_page_break_top_level.dclg"))
    pages = [b for b in result if b.kind == "page"]
    assert len(pages) == 2
    assert pages[0].id == "page-0"
    assert pages[1].id == "page-1"
    assert pages[0].page_no == 0
    assert pages[1].page_no == 1


def test_page_xpaths_are_per_page_partition() -> None:
    result = detect_boundaries(_tree("ok_page_break_top_level.dclg"))
    pages = [b for b in result if b.kind == "page"]
    # Each page contains exactly one text element.
    assert pages[0].xpaths == ("/doclang[1]/text[1]",)
    assert pages[1].xpaths == ("/doclang[1]/text[2]",)


def test_no_page_break_no_page_boundaries() -> None:
    result = detect_boundaries(_tree("ok_no_namespace.dclg"))
    pages = [b for b in result if b.kind == "page"]
    assert pages == []


# --- Group boundaries ------------------------------------------------------


def test_group_emitted_for_top_level_group() -> None:
    """``ok_comprehensive.dclg`` has top-level groups."""
    result = detect_boundaries(_tree("ok_comprehensive.dclg"))
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
    result = detect_boundaries(_tree("ok_table_rectangular.dclg"))
    tables = [b for b in result if b.kind == "table"]
    assert len(tables) == 3
    assert [b.id for b in tables] == [f"table-{i}" for i in range(3)]


def test_table_boundary_first_xpath_points_at_table_element() -> None:
    """Phase 9: each table boundary starts with the synthetic table xpath
    (boundary marker, no harvest span) followed by per-cell xpaths."""
    result = detect_boundaries(_tree("ok_table_rectangular.dclg"))
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
    result = detect_boundaries(_tree("ok_table_rectangular.dclg"))
    tables = [b for b in result if b.kind == "table"]
    for t in tables:
        for xp in t.xpaths:
            tail = xp.rsplit("/", 1)[-1]
            local = tail.split("[", 1)[0]
            assert local not in {"ecel", "nl"}, f"forbidden marker in boundary: {xp}"


# --- Field-region boundaries ----------------------------------------------


def test_field_region_boundary_emitted() -> None:
    result = detect_boundaries(_tree("ok_field_item_nested_descendant_key_scope.dclg"))
    field_regions = [b for b in result if b.kind == "field_region"]
    assert len(field_regions) >= 1


def test_field_region_xpaths_cover_harvested_key_value_spans() -> None:
    """Boundary xpaths must intersect harvester key/value paths (not only the region)."""
    tree = _tree("ok_field_item_nested_descendant_key_scope.dclg")
    field_regions = [
        b for b in detect_boundaries(tree, include_field_regions=True) if b.kind == "field_region"
    ]
    assert field_regions
    harvest = harvest_doclang_text(tree, include_field_regions=True)
    harvest_xpaths = {s.xpath for s in harvest.spans}
    assert harvest_xpaths, "fixture must harvest key/value spans"
    covered = set()
    for boundary in field_regions:
        covered |= set(boundary.xpaths) & harvest_xpaths
    assert covered == harvest_xpaths


def test_code_formula_eligible_when_knobs_on() -> None:
    """Opt-in code/formula must join document/heading eligibility."""
    tree = _tree("ok_comprehensive.dclg")
    root = tree.getroot()
    default = set(_harvest_eligible_xpaths(root))
    widened = set(_harvest_eligible_xpaths(root, include_code_blocks=True, include_formulas=True))
    assert widened >= default
    assert any("/code[" in xp for xp in widened - default) or any("/formula[" in xp for xp in widened - default)


# --- Document fallback -----------------------------------------------------


def test_document_fallback_when_no_structural_boundary() -> None:
    """``ok_thread.dclg`` has no headings / page_breaks / groups —
    a single ``document`` boundary must cover the harvest-eligible
    xpaths."""
    result = detect_boundaries(_tree("ok_thread.dclg"))
    documents = [b for b in result if b.kind == "document"]
    assert len(documents) == 1
    assert documents[0].id == "document"
    assert len(documents[0].xpaths) == 2


def test_no_document_fallback_when_headings_present() -> None:
    """``ok_comprehensive`` has headings and no pre-heading prose — a
    full-document fallback must not fire. (A leading ``document`` bucket
    is only for content that precedes the first heading.)"""
    result = detect_boundaries(_tree("ok_comprehensive.dclg"))
    documents = [b for b in result if b.kind == "document"]
    assert documents == []


def test_pre_heading_content_gets_document_bucket() -> None:
    """Prose before the first heading lands in a leading ``document``
    boundary (same pattern as markdown)."""
    xml = (
        b'<doclang xmlns="https://www.doclang.ai/ns/v0">'
        b"<text>Lead-in before any heading.</text>"
        b'<heading level="1">Title</heading>'
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
        "ok_comprehensive.dclg",
        "ok_no_namespace.dclg",
        "ok_thread.dclg",
        "ok_page_break_top_level.dclg",
        "ok_table_rectangular.dclg",
        "ok_list_with_unwrapped_text.dclg",
    ],
)
def test_all_boundary_ids_unique(fixture_name: str) -> None:
    result = detect_boundaries(_tree(fixture_name))
    ids = [b.id for b in result]
    assert len(ids) == len(set(ids)), f"duplicate boundary ids: {ids}"


@pytest.mark.parametrize(
    "fixture_name",
    [
        "ok_comprehensive.dclg",
        "ok_no_namespace.dclg",
        "ok_thread.dclg",
        "ok_page_break_top_level.dclg",
    ],
)
def test_xpaths_within_boundary_are_unique(fixture_name: str) -> None:
    result = detect_boundaries(_tree(fixture_name))
    for b in result:
        assert len(set(b.xpaths)) == len(b.xpaths), f"duplicate xpaths in boundary {b.id}"


def test_no_slide_or_turn_boundary_kinds() -> None:
    """DocLang does not model slides or speaker turns (Phase 0 verified).
    Boundary detection must never emit those kinds."""
    result = detect_boundaries(_tree("ok_comprehensive.dclg"))
    kinds = {b.kind for b in result}
    assert "slide" not in kinds
    assert "slide-notes" not in kinds
    assert "turn" not in kinds


def test_nested_table_raises_unsupported(tmp_path: Path) -> None:
    path = tmp_path / "nested.dclg"
    path.write_text(
        """\
<?xml version="1.0" encoding="UTF-8"?>
<doclang xmlns="https://www.doclang.ai/ns/v0">
  <p>Intro</p>
  <table>
    <ched/><fcel/>outer
    <fcel/>
    <table>
      <ched/><fcel/>inner
    </table>
  </table>
</doclang>
""",
        encoding="utf-8",
    )
    tree = parse_doclang_xml(path)
    with pytest.raises(UnsupportedDoclangError, match="Nested <table>"):
        detect_boundaries(tree)


@pytest.mark.parametrize(
    "policy",
    [
        DoclangEligibility(),
        DoclangEligibility(
            include_picture_captions=False,
            include_lists=False,
            include_code_blocks=True,
            include_formulas=True,
            include_background=True,
            include_furniture=True,
            include_field_regions=True,
        ),
        DoclangEligibility(
            include_heading_boundaries=False,
            include_page_boundaries=False,
            include_group_boundaries=False,
        ),
    ],
)
def test_primary_boundary_membership_exactly_matches_harvest(policy: DoclangEligibility) -> None:
    xml = b"""<doclang>
      <heading><description>metadata</description>Heading</heading>
      <group><text>Body</text><text><layer value="background"/>Background</text>
        <picture><caption>Caption</caption></picture>
        <list><ldiv/>Item</list><code>Code</code><formula>Formula</formula>
        <page_header>Furniture</page_header>
        <field_region><field_item><key>Key</key><value>Value</value></field_item></field_region>
      </group>
      <page_break/><text>Second page</text>
    </doclang>"""
    tree = etree.ElementTree(etree.fromstring(xml))
    harvest = harvest_doclang_text(tree, eligibility=policy)
    boundaries = detect_boundaries(tree, eligibility=policy)
    primary_xpaths = {
        xpath
        for boundary in boundaries
        if boundary.kind in {"document", "heading", "page", "group"}
        for xpath in boundary.xpaths
    }
    assert primary_xpaths == {span.xpath for span in harvest.spans}


def test_heading_label_uses_metadata_aware_text() -> None:
    tree = etree.ElementTree(
        etree.fromstring(b"<doclang><heading><description>Derived</description>Visible</heading></doclang>")
    )
    (heading,) = [boundary for boundary in detect_boundaries(tree) if boundary.kind == "heading"]
    assert heading.label == "Visible"
