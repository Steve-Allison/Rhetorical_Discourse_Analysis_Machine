"""Unit tests for ``isanlp_rst.docling.boundaries.detect_boundaries``."""

from __future__ import annotations

from pathlib import Path

import pytest
from docling_core.types.doc.document import DoclingDocument

from isanlp_rst.docling.boundaries import detect_boundaries

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


# --- PPTX -------------------------------------------------------------------


def test_pptx_emits_9_slide_boundaries(pptx_doc: DoclingDocument) -> None:
    result = detect_boundaries(pptx_doc)
    slides = [b for b in result if b.kind == "slide"]
    assert len(slides) == 9
    assert {b.id for b in slides} == {f"slide-{i}" for i in range(9)}


def test_pptx_slide_0_label_is_first_title(pptx_doc: DoclingDocument) -> None:
    result = detect_boundaries(pptx_doc)
    slide_0 = next(b for b in result if b.id == "slide-0")
    assert slide_0.label == "GenAI Creation"


def test_pptx_slide_0_parent_self_ref(pptx_doc: DoclingDocument) -> None:
    result = detect_boundaries(pptx_doc)
    slide_0 = next(b for b in result if b.id == "slide-0")
    assert slide_0.parent_self_ref == "#/groups/0"


def test_pptx_slide_0_self_refs_match_group_children(pptx_doc: DoclingDocument) -> None:
    """slide-0 group has children [texts/0, texts/1, pictures/0]."""
    result = detect_boundaries(pptx_doc)
    slide_0 = next(b for b in result if b.id == "slide-0")
    assert slide_0.self_refs == ("#/texts/0", "#/texts/1", "#/pictures/0")


def test_pptx_slide_notes_emitted_for_5_slides(pptx_doc: DoclingDocument) -> None:
    """Slides 1, 3, 4, 7, 8 have notes-layer items in the pptx fixture."""
    result = detect_boundaries(pptx_doc)
    notes = [b for b in result if b.kind == "slide-notes"]
    assert {b.id for b in notes} == {
        "slide-1-notes",
        "slide-3-notes",
        "slide-4-notes",
        "slide-7-notes",
        "slide-8-notes",
    }


def test_pptx_slide_1_notes_self_ref(pptx_doc: DoclingDocument) -> None:
    result = detect_boundaries(pptx_doc)
    notes_1 = next(b for b in result if b.id == "slide-1-notes")
    assert notes_1.self_refs == ("#/texts/3",)
    assert notes_1.parent_self_ref == "#/groups/1"


def test_pptx_notes_omitted_when_include_slide_notes_false(
    pptx_doc: DoclingDocument,
) -> None:
    """Boundaries must honour the same NOTES knob as the harvester."""
    result = detect_boundaries(pptx_doc, include_slide_notes=False)
    assert [b for b in result if b.kind == "slide-notes"] == []
    slide_1 = next(b for b in result if b.id == "slide-1")
    assert "#/texts/3" not in slide_1.self_refs


def test_pptx_tables_emitted(pptx_doc: DoclingDocument) -> None:
    result = detect_boundaries(pptx_doc)
    tables = [b for b in result if b.kind == "table"]
    assert len(tables) == 20
    # Each table boundary's self_refs starts with the synthetic table
    # marker, followed by real JSON-pointer cell refs that resolve
    # against the source document (data/table_cells path).
    assert tables[0].self_refs[0] == "#/tables/0"
    for ref in tables[0].self_refs[1:]:
        assert ref.startswith("#/tables/0/data/table_cells/")


# --- VTT --------------------------------------------------------------------


def test_vtt_single_speaker_coalesces_to_one_turn(vtt_doc: DoclingDocument) -> None:
    result = detect_boundaries(vtt_doc)
    turns = [b for b in result if b.kind == "turn"]
    assert len(turns) == 1
    assert turns[0].id == "turn-0"
    assert turns[0].label == "SPEAKER_00"
    assert len(turns[0].self_refs) == 37


def test_vtt_no_coalesce_produces_37_turns(vtt_doc: DoclingDocument) -> None:
    result = detect_boundaries(vtt_doc, coalesce_speaker_turns=False)
    turns = [b for b in result if b.kind == "turn"]
    assert len(turns) == 37


def test_vtt_no_tables(vtt_doc: DoclingDocument) -> None:
    result = detect_boundaries(vtt_doc)
    tables = [b for b in result if b.kind == "table"]
    assert tables == []


# --- PDF --------------------------------------------------------------------


def test_pdf_emits_11_section_boundaries(pdf_doc: DoclingDocument) -> None:
    """PDF fixture has 11 section_headers per the smoke-iterate survey."""
    result = detect_boundaries(pdf_doc)
    sections = [b for b in result if b.kind == "section"]
    assert len(sections) == 11


def test_pdf_section_label_is_header_text(pdf_doc: DoclingDocument) -> None:
    """The first section header in the pdf fixture is 'Workbook Day 1 - Day 2'."""
    result = detect_boundaries(pdf_doc)
    sections = [b for b in result if b.kind == "section"]
    assert sections[0].label == "Workbook Day 1 - Day 2"


def test_pdf_section_kind_carries_level(pdf_doc: DoclingDocument) -> None:
    """All PDF section_headers are level 1 in this fixture."""
    result = detect_boundaries(pdf_doc)
    sections = [b for b in result if b.kind == "section"]
    levels = {b.level for b in sections}
    assert levels == {1}


def test_pdf_one_table_boundary(pdf_doc: DoclingDocument) -> None:
    result = detect_boundaries(pdf_doc)
    tables = [b for b in result if b.kind == "table"]
    assert len(tables) == 1
    assert tables[0].id == "table-0"


# --- Markdown ---------------------------------------------------------------


def test_markdown_emits_section_boundaries(markdown_doc: DoclingDocument) -> None:
    """Markdown fixture has 4 section_headers (levels 2 and 3)."""
    result = detect_boundaries(markdown_doc)
    sections = [b for b in result if b.kind == "section"]
    assert len(sections) == 4


def test_markdown_section_levels(markdown_doc: DoclingDocument) -> None:
    result = detect_boundaries(markdown_doc)
    sections = [b for b in result if b.kind == "section"]
    levels = {b.level for b in sections}
    assert levels == {2, 3}


# --- Global properties ------------------------------------------------------


@pytest.mark.parametrize(
    "doc_fixture",
    ["pptx_doc", "pdf_doc", "vtt_doc", "markdown_doc"],
)
def test_all_boundary_ids_unique(
    doc_fixture: str, request: pytest.FixtureRequest
) -> None:
    doc = request.getfixturevalue(doc_fixture)
    result = detect_boundaries(doc)
    ids = [b.id for b in result]
    assert len(ids) == len(set(ids)), f"duplicate boundary ids: {ids}"


@pytest.mark.parametrize(
    "doc_fixture",
    ["pptx_doc", "pdf_doc", "vtt_doc", "markdown_doc"],
)
def test_all_self_refs_in_boundaries_are_unique(
    doc_fixture: str, request: pytest.FixtureRequest
) -> None:
    """Within each boundary, self_refs has no duplicates."""
    doc = request.getfixturevalue(doc_fixture)
    result = detect_boundaries(doc)
    for b in result:
        assert len(set(b.self_refs)) == len(b.self_refs), (
            f"duplicate self_refs in boundary {b.id}: {b.self_refs}"
        )
