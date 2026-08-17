"""Unit tests for ``isanlp_rst.markdown.harvester``.

Tests focus on inline-flattening contracts, blockquote containment,
knob negative-space, table-harvest grid semantics, and the
offset-tiling invariant the mapper depends on.
"""

from isanlp_rst.markdown.harvester import (
    _inline_text,
    harvest_markdown_tables,
    harvest_markdown_text,
)
from isanlp_rst.markdown.loader import load_markdown


def _harvest(src: str, **knobs: bool) -> tuple:
    """Convenience: parse src + harvest with optional knob overrides.

    Knobs are bool-only here (no harvest_separator overrides) — the
    signature reflects that.
    """
    return harvest_markdown_text(load_markdown(src).tokens, **knobs).spans  # type: ignore[arg-type]


def _tables(src: str, **knobs: bool) -> tuple:
    return harvest_markdown_tables(load_markdown(src).tokens, **knobs)  # type: ignore[arg-type]


# --- Inline text flattening contract --------------------------------------


def test_inline_text_drops_emphasis_wrappers() -> None:
    """*em* and **strong** wrappers must not appear in flattened text."""
    spans = _harvest("Plain *em* and **strong** in one para.\n")
    para = next(s for s in spans if s.kind == "paragraph")
    assert "*" not in para.text and "**" not in para.text
    assert "em" in para.text and "strong" in para.text


def test_inline_text_drops_link_wrappers_keeps_visible_text() -> None:
    """`[label](url)` keeps `label`, drops the URL."""
    spans = _harvest("See [the docs](https://example.com/x) here.\n")
    para = next(s for s in spans if s.kind == "paragraph")
    assert "the docs" in para.text
    assert "https://example.com" not in para.text


def test_inline_strikethrough_wrappers_dropped_text_kept() -> None:
    """`~~text~~` must not leave literal tildes in the harvest (the
    strikethrough rule is enabled under gfm=True)."""
    spans = _harvest("Keep ~~this struck~~ text.\n")
    para = next(s for s in spans if s.kind == "paragraph")
    assert "~~" not in para.text
    assert "this struck" in para.text


def test_inline_image_alt_text_lands_in_parent_paragraph() -> None:
    """Image alt text is harvested as part of the containing paragraph."""
    spans = _harvest("Look ![the diagram](x.png) carefully.\n")
    para = next(s for s in spans if s.kind == "paragraph")
    assert "the diagram" in para.text


def test_inline_softbreak_becomes_single_space() -> None:
    spans = _harvest("Line one\nLine two\n")
    para = next(s for s in spans if s.kind == "paragraph")
    # Single space between, not a newline or doubled space.
    assert para.text == "Line one Line two"


def test_inline_code_text_preserved() -> None:
    """Backtick wrappers drop but the code text survives."""
    spans = _harvest("Use `pixi run test` to verify.\n")
    para = next(s for s in spans if s.kind == "paragraph")
    assert "pixi run test" in para.text
    assert "`" not in para.text


def test_inline_text_falls_back_to_content_when_children_none() -> None:
    """Defensive path: when an inline somehow has no children, content
    is the fallback. We construct a minimal Token-like to verify."""

    class _Stub:
        children = None
        content = "fallback"

    assert _inline_text(_Stub()) == "fallback"  # type: ignore[arg-type]


# --- Per-construct routing -------------------------------------------------


def test_heading_kind_and_level_extracted() -> None:
    """h1..h6 must yield level 1..6 respectively."""
    src = "\n".join(f"{'#' * lvl} h{lvl}\n" for lvl in range(1, 7))
    spans = _harvest(src)
    levels = [s.level for s in spans if s.kind == "heading"]
    assert levels == [1, 2, 3, 4, 5, 6]


def test_list_items_each_get_their_own_span() -> None:
    """Three bullet items → three list_item spans, not one."""
    spans = _harvest("- alpha\n- bravo\n- charlie\n")
    items = [s for s in spans if s.kind == "list_item"]
    assert [s.text for s in items] == ["alpha", "bravo", "charlie"]


def test_nested_list_collapses_into_outer_item() -> None:
    """Nested bullets join their parent item's text rather than emit
    separate spans — by design, the outer list_item swallows its sublist."""
    src = "- outer\n  - nested\n- second\n"
    items = [s for s in _harvest(src) if s.kind == "list_item"]
    assert len(items) == 2
    assert "nested" in items[0].text


# --- Blockquote containment ------------------------------------------------


def test_blockquote_paragraph_kind_marked() -> None:
    """Paragraphs inside `>` become blockquote_paragraph, not paragraph."""
    spans = _harvest("> a quoted line\n")
    quoted = [s for s in spans if s.kind == "blockquote_paragraph"]
    assert len(quoted) == 1


def test_blockquote_paragraph_outside_quote_is_plain_paragraph() -> None:
    """Negative-space: a plain para must not be classified as blockquote."""
    spans = _harvest("Just a paragraph.\n")
    assert not any(s.kind == "blockquote_paragraph" for s in spans)


def test_quoted_heading_kind_is_blockquote_heading() -> None:
    """A heading inside `>` is quoted content — it must not carry the
    plain `heading` kind that opens section boundaries."""
    spans = _harvest("> # Quoted title\n")
    assert [s.kind for s in spans] == ["blockquote_heading"]
    assert spans[0].level == 1


def test_include_blockquotes_false_gates_all_quoted_constructs() -> None:
    """The knob gates the whole quoted region: paragraphs, headings,
    lists, code fences, and HTML blocks alike."""
    src = (
        "Plain.\n\n"
        "> # Quoted heading\n"
        "> quoted para\n"
        ">\n"
        "> - quoted item\n"
        ">\n"
        "> ```\n"
        "> quoted code\n"
        "> ```\n"
    )
    spans = _harvest(src, include_blockquotes=False)
    assert [s.kind for s in spans] == ["paragraph"]


def test_include_blockquotes_true_keeps_quoted_list_items() -> None:
    spans = _harvest("> - quoted item\n")
    assert any(s.kind == "list_item" and s.text == "quoted item" for s in spans)


# --- HTML blocks ------------------------------------------------------------


def test_html_block_tags_stripped_text_kept() -> None:
    """Raw tags must not enter the RST input; the prose between them must."""
    spans = _harvest('<div class="callout">\nactual prose here\n</div>\n')
    html = next(s for s in spans if s.kind == "html_block")
    assert "<" not in html.text and ">" not in html.text
    assert "actual prose here" in html.text


def test_html_block_tags_only_emits_no_span() -> None:
    """An HTML block with no text content strips to nothing → no span."""
    spans = _harvest("<hr/>\n")
    assert not any(s.kind == "html_block" for s in spans)


# --- Main harvest excludes tables -------------------------------------------

TABLE_SRC = "| h1 | h2 |\n|----|----|\n| a  | b  |\n| c  | d  |\n"


def test_main_harvest_never_contains_cells() -> None:
    """Two-level analysis: cells live in table harvests, not the main one."""
    spans = _harvest(TABLE_SRC + "\nAfter table.\n")
    assert [s.kind for s in spans] == ["paragraph"]
    assert not any(s.block_ref.startswith("#/tables/") for s in spans)


# --- Table harvests ----------------------------------------------------------


def test_table_cells_emitted_row_major_with_indices() -> None:
    """Row 0 = header (th), row 1+ = body (td); col indices increment per row."""
    (th,) = _tables(TABLE_SRC)
    headers = [c for c in th.spans if c.row_idx == 0]
    assert all(c.kind == "table_header_cell" for c in headers)
    assert [c.col_idx for c in headers] == [0, 1]
    body = [c for c in th.spans if c.row_idx > 0]
    assert all(c.kind == "table_cell" for c in body)
    assert [c.text for c in body] == ["a", "b", "c", "d"]


def test_table_cell_refs_use_grid_position_namespace() -> None:
    """Cell refs are #/tables/T/cells/K with K counting grid positions."""
    (th,) = _tables(TABLE_SRC)
    assert [s.block_ref for s in th.spans] == [
        f"#/tables/0/cells/{k}" for k in range(6)
    ]


def test_multiple_tables_assigned_distinct_table_idx() -> None:
    src = TABLE_SRC + "\n" + TABLE_SRC
    harvests = _tables(src)
    assert [th.table_idx for th in harvests] == [0, 1]
    assert harvests[1].spans[0].block_ref.startswith("#/tables/1/")


def test_empty_table_cell_keeps_grid_position() -> None:
    """Cells with no text yield no span but their grid position (ref K
    and col_idx) must still advance for subsequent cells."""
    src = "| a |   | c |\n|---|---|---|\n| 1 | 2 | 3 |\n"
    (th,) = _tables(src)
    headers = [s for s in th.spans if s.kind == "table_header_cell"]
    assert [h.col_idx for h in headers] == [0, 2]
    assert [h.block_ref for h in headers] == [
        "#/tables/0/cells/0",
        "#/tables/0/cells/2",
    ]


def test_quoted_table_gated_with_blockquotes_off() -> None:
    """A table inside a blockquote follows the blockquote knob."""
    src = "> | h |\n> |---|\n> | c |\n"
    assert _tables(src, include_blockquotes=False) == ()
    harvests = _tables(src, include_blockquotes=True)
    assert len(harvests) == 1


def test_table_harvest_offsets_tile_full_text() -> None:
    """Same tiling invariant as the main harvest, per table."""
    (th,) = _tables(TABLE_SRC)
    span_len_sum = sum(len(s.text) for s in th.spans)
    sep_len = len("\n\n") * (len(th.spans) - 1)
    assert span_len_sum + sep_len == len(th.full_text)


# --- Knob negative-space --------------------------------------------------


def test_include_code_blocks_false_emits_no_code_block_spans() -> None:
    src = "```\ncode\n```\n"
    assert not [s for s in _harvest(src, include_code_blocks=False)
                if s.kind == "code_block"]


def test_include_html_false_emits_no_html_block_spans() -> None:
    src = "<div>raw html</div>\n"
    assert not [s for s in _harvest(src, include_html=False)
                if s.kind == "html_block"]


# --- Offset-tiling invariant ----------------------------------------------


def test_span_offsets_tile_full_text_with_separators() -> None:
    """Mapper's overlap rule depends on (start, end) ranges that
    tile full_text exactly: sum of span lengths + (N-1) * sep_len ==
    len(full_text). Regression-test the contract."""
    src = "# H\n\npara one\n\npara two\n"
    result = harvest_markdown_text(load_markdown(src).tokens)
    span_len_sum = sum(len(s.text) for s in result.spans)
    sep_len = len("\n\n") * (len(result.spans) - 1)
    assert span_len_sum + sep_len == len(result.full_text)


def test_span_block_refs_are_sequential_zero_indexed() -> None:
    """`#/blocks/N` must be sequential from 0 in document order."""
    spans = _harvest("# H\n\npara\n\n- li\n")
    refs = [s.block_ref for s in spans]
    assert refs == [f"#/blocks/{i}" for i in range(len(refs))]


# --- Boundaries -----------------------------------------------------------


def test_empty_token_stream_returns_empty_harvest() -> None:
    result = harvest_markdown_text(())
    assert result.full_text == ""
    assert result.spans == ()


def test_thematic_break_emits_no_span() -> None:
    """`---` between paragraphs is a divider, not prose."""
    spans = _harvest("a\n\n---\n\nb\n")
    # Only the two paragraphs harvest; no span for the hr.
    assert [s.kind for s in spans] == ["paragraph", "paragraph"]
