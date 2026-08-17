"""Unit tests for ``isanlp_rst.markdown.boundaries``.

Tests focus on boundary cases (zero headings, heading at start, mixed
levels), the quoted-heading exclusion, invariants (no main span
orphaned; synthetic ``#/tables/T`` marker never a span), and the
two-level table boundary shape.
"""

from isanlp_rst.markdown.boundaries import detect_boundaries
from isanlp_rst.markdown.harvester import (
    harvest_markdown_tables,
    harvest_markdown_text,
)
from isanlp_rst.markdown.loader import load_markdown


def _boundaries(src: str) -> tuple:
    tokens = load_markdown(src).tokens
    harvest = harvest_markdown_text(tokens)
    tables = harvest_markdown_tables(tokens)
    return detect_boundaries(harvest.spans, tables), harvest.spans, tables


# --- Section / document fallback ------------------------------------------


def test_no_headings_emits_single_document_boundary() -> None:
    boundaries, _, _ = _boundaries("Just one paragraph of prose.\n")
    assert [b.kind for b in boundaries] == ["document"]


def test_heading_at_start_no_document_boundary() -> None:
    """If the very first span is a heading, there's no pre-heading bucket."""
    boundaries, _, _ = _boundaries("# H\n\npara\n")
    kinds = [b.kind for b in boundaries]
    assert "document" not in kinds
    assert "section" in kinds


def test_pre_heading_content_creates_document_boundary() -> None:
    boundaries, _, _ = _boundaries("lead-in\n\n# H\n\npara\n")
    kinds = [b.kind for b in boundaries]
    assert kinds[0] == "document"
    assert kinds[1] == "section"


def test_multi_level_sections_carry_their_heading_levels() -> None:
    src = "# H1\n\np\n\n## H2\n\np\n\n### H3\n\np\n"
    boundaries, _, _ = _boundaries(src)
    levels = [b.level for b in boundaries if b.kind == "section"]
    assert levels == [1, 2, 3]


def test_section_label_carries_heading_text() -> None:
    """The first section's label must be the heading text — not None."""
    boundaries, _, _ = _boundaries("# Introduction\n\npara\n")
    section = next(b for b in boundaries if b.kind == "section")
    assert section.label == "Introduction"


def test_quoted_heading_does_not_open_a_section() -> None:
    """`> # Quoted` is quoted content, not document structure."""
    boundaries, _, _ = _boundaries("intro\n\n> # Quoted title\n> quoted\n")
    assert not any(b.kind == "section" for b in boundaries)
    # The quoted spans live in the document boundary instead.
    doc = next(b for b in boundaries if b.kind == "document")
    assert len(doc.block_refs) == 3  # intro + quoted heading + quoted para


# --- Table boundaries -------------------------------------------------------


TABLE_SRC = "| h |\n|---|\n| a |\n| b |\n"


def test_table_boundary_emitted() -> None:
    boundaries, _, _ = _boundaries(TABLE_SRC)
    assert any(b.kind == "table" for b in boundaries)


def test_table_boundary_contains_synthetic_marker_first() -> None:
    """Convention: marker is first in block_refs, cells follow in order."""
    boundaries, _, _ = _boundaries(TABLE_SRC)
    table = next(b for b in boundaries if b.kind == "table")
    assert table.block_refs[0] == "#/tables/0"
    assert all(r.startswith("#/tables/0/cells/") for r in table.block_refs[1:])


def test_table_boundary_covers_every_harvested_cell() -> None:
    boundaries, _, tables = _boundaries(TABLE_SRC)
    table = next(b for b in boundaries if b.kind == "table")
    cell_refs = {s.block_ref for s in tables[0].spans}
    assert cell_refs.issubset(set(table.block_refs))


def test_synthetic_table_marker_not_in_any_harvest_span() -> None:
    """Invariant: ``#/tables/T`` is boundary-only and never a span ref."""
    _, spans, tables = _boundaries(TABLE_SRC)
    all_refs = {s.block_ref for s in spans}
    for th in tables:
        all_refs.update(s.block_ref for s in th.spans)
    assert "#/tables/0" not in all_refs


def test_cells_do_not_belong_to_sections() -> None:
    """Two-level analysis: cells are not part of the document tree, so
    they live only in their table boundary — never in a section."""
    boundaries, _, _ = _boundaries("# A\n\n| h |\n|---|\n| c |\n")
    section = next(b for b in boundaries if b.kind == "section")
    assert not any("/cells/" in r for r in section.block_refs)


# --- Code-block boundaries ------------------------------------------------


def test_code_block_boundary_per_block() -> None:
    src = "```\nx\n```\n\n```\ny\n```\n"
    boundaries, _, _ = _boundaries(src)
    assert sum(1 for b in boundaries if b.kind == "code_block") == 2


def test_code_block_boundary_references_its_span() -> None:
    """The boundary's single block_ref must match the code_block span."""
    src = "```\nx\n```\n"
    boundaries, spans, _ = _boundaries(src)
    code_span = next(s for s in spans if s.kind == "code_block")
    code_boundary = next(b for b in boundaries if b.kind == "code_block")
    assert code_boundary.block_refs == (code_span.block_ref,)


# --- Cross-boundary membership invariants ---------------------------------


def test_every_main_span_appears_in_at_least_one_boundary() -> None:
    """Invariant: no main-harvest span is orphaned."""
    src = (
        "lead\n\n# A\n\npara\n\n"
        "| h |\n|---|\n| c |\n\n"
        "```\ncode\n```\n\n"
        "> quoted\n"
    )
    boundaries, spans, _ = _boundaries(src)
    boundary_union = set()
    for b in boundaries:
        boundary_union.update(b.block_refs)
    for sp in spans:
        assert sp.block_ref in boundary_union, f"orphan span: {sp.block_ref}"


def test_every_table_cell_appears_in_its_table_boundary() -> None:
    """Invariant: per-table analysis refs resolve against the boundary."""
    src = "# A\n\n| h |\n|---|\n| c |\n"
    boundaries, _, tables = _boundaries(src)
    table_boundary = next(b for b in boundaries if b.kind == "table")
    for s in tables[0].spans:
        assert s.block_ref in table_boundary.block_refs


# --- Boundaries: zero-input edge ------------------------------------------


def test_empty_spans_emits_no_boundaries() -> None:
    assert detect_boundaries((), ()) == ()
