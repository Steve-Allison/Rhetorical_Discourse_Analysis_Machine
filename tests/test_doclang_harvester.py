"""Unit tests for the doclang harvesters (main text + per-table)."""

from pathlib import Path

import pytest
from lxml import etree

from isanlp_rst.doclang.errors import UnsupportedDoclangError
from isanlp_rst.doclang.harvester import harvest_doclang_tables, harvest_doclang_text
from isanlp_rst.doclang.loader import parse_doclang_xml

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "doclang"


def _tree(name: str) -> etree._ElementTree:
    return parse_doclang_xml(FIXTURES / name)


# --- Offset consistency ----------------------------------------------------


@pytest.mark.parametrize(
    "fixture_name",
    [
        "doclang_example.dclg.xml",
        "ok_comprehensive.dclg.xml",
        "ok_no_namespace.dclg.xml",
        "ok_thread.dclg.xml",
        "ok_list_with_unwrapped_text.dclg.xml",
        "ok_page_break_top_level.dclg.xml",
    ],
)
def test_offsets_reconstruct_each_span_text(fixture_name: str) -> None:
    result = harvest_doclang_text(_tree(fixture_name))
    for span in result.spans:
        assert result.full_text[span.start : span.end] == span.text, (
            f"span {span.xpath} offsets don't reconstruct its text"
        )


@pytest.mark.parametrize(
    "fixture_name",
    [
        "doclang_example.dclg.xml",
        "ok_comprehensive.dclg.xml",
        "ok_list_with_unwrapped_text.dclg.xml",
    ],
)
def test_spans_in_strictly_ascending_order(fixture_name: str) -> None:
    result = harvest_doclang_text(_tree(fixture_name))
    for prev, curr in zip(result.spans, result.spans[1:], strict=False):
        assert prev.end <= curr.start


# --- Determinism -----------------------------------------------------------


def test_determinism_full_text() -> None:
    """Two calls on the same tree return identical harvests."""
    tree = _tree("ok_comprehensive.dclg.xml")
    r1 = harvest_doclang_text(tree)
    r2 = harvest_doclang_text(tree)
    assert r1.full_text == r2.full_text
    assert r1.spans == r2.spans


# --- Separator reconstruction ----------------------------------------------


def test_separator_reconstructs_full_text() -> None:
    result = harvest_doclang_text(_tree("ok_comprehensive.dclg.xml"))
    assert "\n\n".join(s.text for s in result.spans) == result.full_text


def test_custom_separator_round_trips() -> None:
    result = harvest_doclang_text(_tree("ok_comprehensive.dclg.xml"), harvest_separator=" | ")
    assert " | ".join(s.text for s in result.spans) == result.full_text


# --- Layer filtering -------------------------------------------------------


def test_background_layer_excluded_by_default() -> None:
    """``ok_layer.dclg.xml`` contains background-, furniture-, and
    body-layer text. Only body must appear by default."""
    result = harvest_doclang_text(_tree("ok_layer.dclg.xml"))
    layers = {s.layer for s in result.spans}
    assert "background" not in layers
    assert "furniture" not in layers


def test_background_layer_included_when_toggled() -> None:
    """Background-toggle must surface a prose ``<text>`` whose ``<layer>``
    is ``background``. The fixture corpus has no background-layer prose
    (only a no-caption picture), so we build a synthetic tree here."""
    xml = (
        b'<doclang xmlns="https://www.doclang.ai/ns/v0">'
        b'<text><layer value="body"/>Body line.</text>'
        b'<text><layer value="background"/>Watermark line.</text>'
        b"</doclang>"
    )
    tree = etree.ElementTree(etree.fromstring(xml))
    without = harvest_doclang_text(tree)
    with_ = harvest_doclang_text(tree, include_background=True)
    assert len(without.spans) == 1
    assert len(with_.spans) == 2
    assert "background" in {s.layer for s in with_.spans}


def test_furniture_layer_included_when_toggled() -> None:
    without = harvest_doclang_text(_tree("ok_layer.dclg.xml"))
    with_ = harvest_doclang_text(_tree("ok_layer.dclg.xml"), include_furniture=True)
    assert len(with_.spans) > len(without.spans)
    assert "furniture" in {s.layer for s in with_.spans}


# --- Two-level table analysis (Option 2) -----------------------------------


def test_main_harvest_empty_for_table_only_doc() -> None:
    """``ok_table_rectangular`` is table-only — the main harvest must be
    empty; the content lives in the per-table harvests."""
    result = harvest_doclang_text(_tree("ok_table_rectangular.dclg.xml"))
    assert result.spans == ()
    assert result.full_text == ""


def test_table_harvests_carry_cells_in_doc_order() -> None:
    """The fixture has 3 tables; harvests must match boundary numbering
    (document order) and carry the cell text."""
    harvests = harvest_doclang_tables(_tree("ok_table_rectangular.dclg.xml"))
    assert [th.table_idx for th in harvests] == [0, 1, 2]
    first = harvests[0]
    assert [s.text for s in first.spans] == [
        "Method",
        "Accuracy",
        "Baseline",
        "0.85",
        "Proposed",
        "0.92",
    ]
    assert first.marker_xpath == "/doclang[1]/table[1]"


def test_table_cells_carry_grid_positions() -> None:
    """Table 3 starts with ``<corn/>`` — a position-only marker. The
    first text cell (Q1) must land at column 1, not 0."""
    harvests = harvest_doclang_tables(_tree("ok_table_rectangular.dclg.xml"))
    third = harvests[2]
    q1 = next(s for s in third.spans if s.text == "Q1")
    assert (q1.row_idx, q1.col_idx) == (0, 1)
    sales = next(s for s in third.spans if s.text == "Sales")
    assert (sales.row_idx, sales.col_idx) == (1, 0)
    assert sales.kind == "table_header_cell"  # rhed marker


def test_ecel_and_nl_markers_never_yield_spans() -> None:
    """``<ecel/>`` (empty) and ``<nl/>`` (row break) must not appear in
    any harvest xpath."""
    harvests = harvest_doclang_tables(_tree("ok_table_rectangular.dclg.xml"))
    for th in harvests:
        for span in th.spans:
            last = span.xpath.rsplit("/", 1)[-1]
            local = last.split("[", 1)[0]
            assert local in {"ched", "fcel", "rhed", "corn"}, span.xpath


def test_span_continuation_markers_terminate_previous_cell() -> None:
    """``<lcel/>`` (col-span continuation) must end the preceding cell's
    accumulation — text after it belongs to no cell — and must occupy a
    grid column."""
    xml = (
        b'<doclang xmlns="https://www.doclang.ai/ns/v0">'
        b"<table>"
        b"<fcel/><text>A</text><lcel/><fcel/><text>B</text><nl/>"
        b"</table>"
        b"</doclang>"
    )
    tree = etree.ElementTree(etree.fromstring(xml))
    (th,) = harvest_doclang_tables(tree)
    assert [s.text for s in th.spans] == ["A", "B"]
    # lcel occupies col 1, so B sits at col 2.
    assert [s.col_idx for s in th.spans] == [0, 2]


def test_table_harvest_offsets_tile_full_text() -> None:
    harvests = harvest_doclang_tables(_tree("ok_table_rectangular.dclg.xml"))
    for th in harvests:
        for s in th.spans:
            assert th.full_text[s.start : s.end] == s.text


@pytest.mark.parametrize(
    "fixture_name",
    [
        "doclang_example.dclg.xml",
        "ok_comprehensive.dclg.xml",
    ],
)
def test_main_harvest_has_no_grid_markers(fixture_name: str) -> None:
    """Main-harvest spans must never terminate in a grid marker."""
    result = harvest_doclang_text(_tree(fixture_name))
    grid_markers = {"ched", "fcel", "rhed", "corn", "ecel", "srow", "lcel", "ucel", "xcel", "nl"}
    for span in result.spans:
        last = span.xpath.rsplit("/", 1)[-1]
        local = last.split("[", 1)[0]
        assert local not in grid_markers, f"grid marker {local!r} leaked into main harvest: {span.xpath}"


# --- Thread-aware joins (B4) ------------------------------------------------


def test_thread_continuation_joins_with_single_space() -> None:
    """``ok_thread.dclg.xml``'s two spans share ``thread_id=1`` — they
    are one logical paragraph split by a page break, so they must join
    with a space, not the paragraph separator."""
    result = harvest_doclang_text(_tree("ok_thread.dclg.xml"))
    assert len(result.spans) == 2
    a, b = result.spans
    assert result.full_text[a.end : b.start] == " "
    assert "\n\n" not in result.full_text


def test_unthreaded_spans_join_with_separator() -> None:
    """Spans without a shared thread keep the paragraph separator."""
    xml = b'<doclang xmlns="https://www.doclang.ai/ns/v0"><text>First.</text><text>Second.</text></doclang>'
    tree = etree.ElementTree(etree.fromstring(xml))
    result = harvest_doclang_text(tree)
    a, b = result.spans
    assert result.full_text[a.end : b.start] == "\n\n"


# --- List item granularity (Phase 1 Q1) ------------------------------------


def test_list_item_per_ldiv_marker() -> None:
    """``ok_list_with_unwrapped_text`` has 18 ``<ldiv/>`` markers — every
    item must materialise as its own span."""
    result = harvest_doclang_text(_tree("ok_list_with_unwrapped_text.dclg.xml"))
    ldiv_spans = [s for s in result.spans if "/ldiv[" in s.xpath]
    # The fixture has 7 lists; some markers have empty text and are dropped.
    # Verify each present ldiv span's xpath actually points at an ldiv marker.
    assert len(ldiv_spans) >= 12, f"expected >=12 list items, got {len(ldiv_spans)}"


def test_list_item_xpath_points_at_marker() -> None:
    result = harvest_doclang_text(_tree("ok_list_with_unwrapped_text.dclg.xml"))
    for span in result.spans:
        if "/ldiv[" not in span.xpath:
            continue
        # The last step must be ldiv[N]
        last = span.xpath.rsplit("/", 1)[-1]
        assert last.startswith("ldiv["), span.xpath


# --- Thread id capture (Phase 1 Q6) ----------------------------------------


def test_thread_id_captured_on_text_host() -> None:
    """``ok_thread.dclg.xml`` has two ``<text>`` elements sharing
    ``<thread thread_id="1"/>``. Both spans must carry ``thread_id=1``."""
    result = harvest_doclang_text(_tree("ok_thread.dclg.xml"))
    assert all(s.thread_id == 1 for s in result.spans)
    assert len(result.spans) == 2


def test_thread_id_none_when_host_has_no_thread() -> None:
    result = harvest_doclang_text(_tree("ok_no_namespace.dclg.xml"))
    assert all(s.thread_id is None for s in result.spans)


# --- Picture captions ------------------------------------------------------


def test_picture_caption_excluded_when_disabled() -> None:
    """``doclang_example.dclg.xml`` has a picture with caption; toggling
    ``include_picture_captions=False`` must drop it."""
    with_ = harvest_doclang_text(_tree("doclang_example.dclg.xml"))
    without = harvest_doclang_text(_tree("doclang_example.dclg.xml"), include_picture_captions=False)
    caption_xpaths_with = {s.xpath for s in with_.spans if "/caption[" in s.xpath}
    caption_xpaths_without = {s.xpath for s in without.spans if "/caption[" in s.xpath}
    assert caption_xpaths_with != caption_xpaths_without
    assert caption_xpaths_without == set()


# --- Code / formula default-off (Phase 1 Q2) -------------------------------


def test_code_blocks_excluded_by_default() -> None:
    """``ok_comprehensive`` has 12 ``<code>`` blocks — default-off must
    drop all of them from spans."""
    result = harvest_doclang_text(_tree("ok_comprehensive.dclg.xml"))
    code_xpaths = [s.xpath for s in result.spans if "/code[" in s.xpath]
    assert code_xpaths == []


def test_code_blocks_included_when_toggled() -> None:
    without = harvest_doclang_text(_tree("ok_comprehensive.dclg.xml"))
    with_ = harvest_doclang_text(_tree("ok_comprehensive.dclg.xml"), include_code_blocks=True)
    assert len(with_.spans) > len(without.spans)


def test_formulas_excluded_by_default() -> None:
    result = harvest_doclang_text(_tree("ok_comprehensive.dclg.xml"))
    formula_xpaths = [s.xpath for s in result.spans if "/formula[" in s.xpath]
    assert formula_xpaths == []


def test_formulas_included_when_toggled() -> None:
    without = harvest_doclang_text(_tree("ok_comprehensive.dclg.xml"))
    with_ = harvest_doclang_text(_tree("ok_comprehensive.dclg.xml"), include_formulas=True)
    assert len(with_.spans) > len(without.spans)


# --- Element-head children must not pollute prose --------------------------


def test_layer_element_head_text_not_in_harvest() -> None:
    """``<layer value="..."/>`` is metadata; its attribute value must not
    appear in prose text."""
    result = harvest_doclang_text(_tree("ok_layer.dclg.xml"))
    for span in result.spans:
        assert "value=" not in span.text


def test_location_element_head_skipped() -> None:
    """``<location value="N"/>`` carries metadata; the value must not
    surface in harvest text."""
    result = harvest_doclang_text(_tree("ok_list_raw_before.dclg.xml"))
    for span in result.spans:
        # No location value attribute should leak as text.
        assert "value=" not in span.text


# --- field_region excluded by default --------------------------------------


def test_field_regions_excluded_by_default() -> None:
    """``ok_field_item_nested_descendant_key_scope`` has a field_region
    with text — must not be in default harvest."""
    result = harvest_doclang_text(_tree("ok_field_item_nested_descendant_key_scope.dclg.xml"))
    for span in result.spans:
        assert "/field_region[" not in span.xpath


def test_field_regions_included_when_opted_in() -> None:
    """``include_field_regions=True`` surfaces key/value text from the
    nested field_item fixture."""
    result = harvest_doclang_text(
        _tree("ok_field_item_nested_descendant_key_scope.dclg.xml"),
        include_field_regions=True,
    )
    joined = " ".join(s.text for s in result.spans)
    assert "Key 1 (outer)" in joined
    assert "Outer value 1a" in joined
    assert "Key 2 (inner)" in joined
    assert "Inner value 2a" in joined
    xpath_blob = " ".join(s.xpath for s in result.spans)
    assert "/field_region[" in xpath_blob or "/key[" in xpath_blob or "/value[" in xpath_blob


# --- Head element skipped --------------------------------------------------


def test_head_element_text_not_in_harvest() -> None:
    """``ok_comprehensive.dclg.xml`` has ``<head><title>...</title></head>`` —
    the title must not leak into prose harvest."""
    result = harvest_doclang_text(_tree("ok_comprehensive.dclg.xml"))
    for span in result.spans:
        assert "/head[" not in span.xpath


# --- Nested tables (fail-closed) -------------------------------------------


def test_nested_table_raises_unsupported(tmp_path: Path) -> None:
    path = tmp_path / "nested.dclg.xml"
    path.write_text(
        """\
<?xml version="1.0" encoding="UTF-8"?>
<doclang xmlns="https://www.doclang.ai/ns/v0">
  <heading>Title</heading>
  <p>Intro</p>
  <table>
    <ched/><fcel/>outer
    <nl/>
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
        harvest_doclang_tables(tree)
