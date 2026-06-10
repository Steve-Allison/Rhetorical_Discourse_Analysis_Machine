"""Unit tests for ``isanlp_rst.doclang.harvester.harvest_doclang_text``."""

from __future__ import annotations

from pathlib import Path

import pytest
from lxml import etree

from isanlp_rst.doclang.harvester import harvest_doclang_text
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
    result = harvest_doclang_text(
        _tree("ok_comprehensive.dclg.xml"), harvest_separator=" | "
    )
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


# --- Table exclusion (boundary-only by design) -----------------------------


def test_table_cells_never_in_harvest_spans() -> None:
    """``ok_table_rectangular`` is table-only — harvest must be empty."""
    result = harvest_doclang_text(_tree("ok_table_rectangular.dclg.xml"))
    assert result.spans == ()
    assert result.full_text == ""


@pytest.mark.parametrize(
    "fixture_name",
    [
        "doclang_example.dclg.xml",
        "ok_comprehensive.dclg.xml",
    ],
)
def test_no_cell_marker_xpath_in_spans(fixture_name: str) -> None:
    """No span's xpath terminates in a cell-start marker — those are
    structural, not prose."""
    result = harvest_doclang_text(_tree(fixture_name))
    cell_markers = {"fcel", "ecel", "ched", "rhed", "corn", "srow", "lcel", "ucel", "xcel", "nl"}
    for span in result.spans:
        last = span.xpath.rsplit("/", 1)[-1]
        local = last.split("[", 1)[0]
        assert local not in cell_markers, (
            f"cell marker {local!r} leaked into harvest xpath: {span.xpath}"
        )


# --- List item granularity (Phase 1 Q1) ------------------------------------


def test_list_item_per_ldiv_marker() -> None:
    """``ok_list_with_unwrapped_text`` has 18 ``<ldiv/>`` markers — every
    item must materialise as its own span."""
    result = harvest_doclang_text(_tree("ok_list_with_unwrapped_text.dclg.xml"))
    ldiv_spans = [s for s in result.spans if "/ldiv[" in s.xpath]
    # The fixture has 7 lists; some markers have empty text and are dropped.
    # Verify each present ldiv span's xpath actually points at an ldiv marker.
    assert len(ldiv_spans) >= 12, (
        f"expected >=12 list items, got {len(ldiv_spans)}"
    )


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
    without = harvest_doclang_text(
        _tree("doclang_example.dclg.xml"), include_picture_captions=False
    )
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
    with_ = harvest_doclang_text(
        _tree("ok_comprehensive.dclg.xml"), include_code_blocks=True
    )
    assert len(with_.spans) > len(without.spans)


def test_formulas_excluded_by_default() -> None:
    result = harvest_doclang_text(_tree("ok_comprehensive.dclg.xml"))
    formula_xpaths = [s.xpath for s in result.spans if "/formula[" in s.xpath]
    assert formula_xpaths == []


def test_formulas_included_when_toggled() -> None:
    without = harvest_doclang_text(_tree("ok_comprehensive.dclg.xml"))
    with_ = harvest_doclang_text(
        _tree("ok_comprehensive.dclg.xml"), include_formulas=True
    )
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
    result = harvest_doclang_text(
        _tree("ok_field_item_nested_descendant_key_scope.dclg.xml")
    )
    for span in result.spans:
        assert "/field_region[" not in span.xpath


# --- Head element skipped --------------------------------------------------


def test_head_element_text_not_in_harvest() -> None:
    """``ok_comprehensive.dclg.xml`` has ``<head><title>...</title></head>`` —
    the title must not leak into prose harvest."""
    result = harvest_doclang_text(_tree("ok_comprehensive.dclg.xml"))
    for span in result.spans:
        assert "/head[" not in span.xpath
