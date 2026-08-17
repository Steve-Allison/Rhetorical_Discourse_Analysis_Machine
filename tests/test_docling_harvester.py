"""Unit tests for the docling harvesters (main text + per-table)."""

from pathlib import Path

import pytest
from docling_core.types.doc.document import DoclingDocument

from isanlp_rst.docling.harvester import harvest_docling_tables, harvest_docling_text

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "docling"


@pytest.fixture(scope="module")
def pptx_doc() -> DoclingDocument:
    return DoclingDocument.load_from_json(FIXTURES / "pptx.docling.json")


@pytest.fixture(scope="module")
def pdf_doc() -> DoclingDocument:
    return DoclingDocument.load_from_json(FIXTURES / "pdf.docling.json")


@pytest.fixture(scope="module")
def vtt_doc() -> DoclingDocument:
    return DoclingDocument.load_from_json(FIXTURES / "vtt.docling.json")


@pytest.fixture(scope="module")
def markdown_doc() -> DoclingDocument:
    return DoclingDocument.load_from_json(FIXTURES / "markdown.docling.json")


# --- Offset consistency ----------------------------------------------------


@pytest.mark.parametrize(
    "doc_fixture",
    ["pptx_doc", "pdf_doc", "vtt_doc", "markdown_doc"],
)
def test_offsets_match_full_text(doc_fixture: str, request: pytest.FixtureRequest) -> None:
    doc = request.getfixturevalue(doc_fixture)
    result = harvest_docling_text(doc)
    for span in result.spans:
        assert result.full_text[span.start : span.end] == span.text, (
            f"span {span.self_ref} offsets don't reconstruct its text"
        )


# --- Determinism -----------------------------------------------------------


def test_determinism_pptx(pptx_doc: DoclingDocument) -> None:
    r1 = harvest_docling_text(pptx_doc)
    r2 = harvest_docling_text(pptx_doc)
    assert r1.full_text == r2.full_text
    assert r1.spans == r2.spans


def test_determinism_pdf(pdf_doc: DoclingDocument) -> None:
    r1 = harvest_docling_text(pdf_doc)
    r2 = harvest_docling_text(pdf_doc)
    assert r1.full_text == r2.full_text
    assert r1.spans == r2.spans


# --- Separator reconstruction ----------------------------------------------


def test_separator_reconstructs_full_text(pptx_doc: DoclingDocument) -> None:
    result = harvest_docling_text(pptx_doc, harvest_separator="\n\n")
    assert "\n\n".join(s.text for s in result.spans) == result.full_text


def test_custom_separator(pptx_doc: DoclingDocument) -> None:
    result = harvest_docling_text(pptx_doc, harvest_separator=" | ")
    assert " | ".join(s.text for s in result.spans) == result.full_text


# --- Two-level table analysis (Option 2) -----------------------------------


@pytest.mark.parametrize(
    "doc_fixture",
    ["pptx_doc", "pdf_doc", "vtt_doc", "markdown_doc"],
)
def test_main_harvest_never_contains_table_refs(doc_fixture: str, request: pytest.FixtureRequest) -> None:
    """Two-level invariant: tables live in their own harvests; the main
    document harvest must never carry a ``#/tables/...`` ref."""
    doc = request.getfixturevalue(doc_fixture)
    result = harvest_docling_text(doc)
    for span in result.spans:
        assert not span.self_ref.startswith("#/tables/"), (
            f"table ref {span.self_ref!r} leaked into main harvest"
        )


def test_table_harvest_refs_are_real_json_pointers(pdf_doc: DoclingDocument) -> None:
    """Cell refs must resolve mechanically against the Docling JSON —
    the path component is ``data/table_cells``, not an invented one."""
    (th,) = harvest_docling_tables(pdf_doc)
    assert th.marker_ref == "#/tables/0"
    for s in th.spans:
        assert s.self_ref.startswith("#/tables/0/data/table_cells/")


def test_table_harvest_carries_grid_metadata(pdf_doc: DoclingDocument) -> None:
    """Each cell span must carry kind + row/col from TableCell."""
    (th,) = harvest_docling_tables(pdf_doc)
    for s in th.spans:
        assert s.kind in ("table_cell", "table_header_cell")
        assert s.row_idx is not None and s.col_idx is not None
    # The pdf fixture's table is 6x2: first two cells are row 0, cols 0/1.
    assert (th.spans[0].row_idx, th.spans[0].col_idx) == (0, 0)
    assert (th.spans[1].row_idx, th.spans[1].col_idx) == (0, 1)


def test_table_harvest_offsets_tile_full_text(pdf_doc: DoclingDocument) -> None:
    (th,) = harvest_docling_tables(pdf_doc)
    for s in th.spans:
        assert th.full_text[s.start : s.end] == s.text


def test_tableless_doc_yields_no_table_harvests(vtt_doc: DoclingDocument) -> None:
    assert harvest_docling_tables(vtt_doc) == ()


def test_main_spans_carry_item_label_as_kind(pdf_doc: DoclingDocument) -> None:
    """Span ``kind`` mirrors the Docling item label so consumers can
    distinguish section headers from body text without re-opening the
    source."""
    result = harvest_docling_text(pdf_doc)
    kinds = {s.kind for s in result.spans}
    assert "section_header" in kinds
    assert "text" in kinds
    assert "" not in kinds


# --- Picture descriptions (VLM) --------------------------------------------


def test_picture_descriptions_included_by_default_pptx(pptx_doc: DoclingDocument) -> None:
    """All 5 PPTX pictures with meta.description.text appear in the harvest."""
    result = harvest_docling_text(pptx_doc)
    pic_refs = [s.self_ref for s in result.spans if s.self_ref.startswith("#/pictures/")]
    assert sorted(pic_refs) == [f"#/pictures/{i}" for i in range(5)]


def test_picture_descriptions_excluded_when_disabled_pptx(
    pptx_doc: DoclingDocument,
) -> None:
    result = harvest_docling_text(pptx_doc, include_picture_descriptions=False)
    pic_refs = [s.self_ref for s in result.spans if s.self_ref.startswith("#/pictures/")]
    assert pic_refs == []


def test_pdf_pictures_have_no_descriptions(pdf_doc: DoclingDocument) -> None:
    """PDF fixture: 48 pictures, 0 with meta.description.text — none in harvest."""
    result = harvest_docling_text(pdf_doc)
    pic_refs = [s.self_ref for s in result.spans if s.self_ref.startswith("#/pictures/")]
    assert pic_refs == []


def test_pptx_picture_description_text_substring_in_harvest(
    pptx_doc: DoclingDocument,
) -> None:
    """Sanity check: a known phrase from picture 0's VLM description appears."""
    result = harvest_docling_text(pptx_doc)
    assert "SEMANTIC BRIDGE" in result.full_text


# --- Slide notes (ContentLayer.NOTES) --------------------------------------


def test_slide_notes_included_by_default_pptx(pptx_doc: DoclingDocument) -> None:
    """5 NOTES-layer items (#/texts/3..7) appear when include_slide_notes=True."""
    result = harvest_docling_text(pptx_doc, include_slide_notes=True)
    refs = {s.self_ref for s in result.spans}
    expected = {f"#/texts/{i}" for i in range(3, 8)}
    assert expected.issubset(refs)


def test_slide_notes_excluded_when_disabled_pptx(pptx_doc: DoclingDocument) -> None:
    result = harvest_docling_text(pptx_doc, include_slide_notes=False)
    refs = {s.self_ref for s in result.spans}
    notes = {f"#/texts/{i}" for i in range(3, 8)}
    assert refs.isdisjoint(notes)


def test_notes_toggle_changes_harvest_size_pptx(pptx_doc: DoclingDocument) -> None:
    with_notes = harvest_docling_text(pptx_doc, include_slide_notes=True)
    without = harvest_docling_text(pptx_doc, include_slide_notes=False)
    assert len(with_notes.spans) > len(without.spans)
    assert len(with_notes.full_text) > len(without.full_text)


# --- Furniture layer -------------------------------------------------------


def test_furniture_toggle_changes_harvest_size_pdf(pdf_doc: DoclingDocument) -> None:
    """PDF has 33 furniture-layer items; harvest grows when they're included."""
    without = harvest_docling_text(pdf_doc, include_furniture=False)
    with_ = harvest_docling_text(pdf_doc, include_furniture=True)
    assert len(with_.spans) - len(without.spans) == 33


# --- Self-ref coverage (TextItems reachable via iterate_items) -------------


def test_pptx_body_text_items_all_harvested(pptx_doc: DoclingDocument) -> None:
    """The 3 body-layer text items #/texts/0..2 must all be in the harvest."""
    result = harvest_docling_text(pptx_doc)
    refs = {s.self_ref for s in result.spans}
    for i in range(3):
        assert f"#/texts/{i}" in refs


def test_vtt_all_texts_in_harvest(vtt_doc: DoclingDocument) -> None:
    """VTT has 37 TextItems, all body-layer; all should appear."""
    result = harvest_docling_text(vtt_doc)
    text_refs = {s.self_ref for s in result.spans if s.self_ref.startswith("#/texts/")}
    assert text_refs == {f"#/texts/{i}" for i in range(37)}


# --- Spans are in iteration order ------------------------------------------


def test_spans_in_strictly_ascending_offset_order(pptx_doc: DoclingDocument) -> None:
    result = harvest_docling_text(pptx_doc)
    for prev, curr in zip(result.spans, result.spans[1:], strict=False):
        assert prev.end <= curr.start
