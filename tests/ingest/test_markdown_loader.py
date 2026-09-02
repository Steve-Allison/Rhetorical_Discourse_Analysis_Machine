"""Unit tests for ``rdam.rst.markdown.loader``.

Tests focus on failure modes (malformed input), boundaries (empty,
front-matter-only), invariants (front-matter stripped from body
stream), and knob negative-space (gfm=False emits no table tokens).
"""

from rdam.rst.markdown.loader import build_parser, load_markdown


# --- Front-matter handling -------------------------------------------------


def test_front_matter_stripped_from_body_tokens() -> None:
    """When front-matter is present its tokens must not appear in body."""
    src = "---\ntitle: t\n---\n# H\n"
    body = load_markdown(src).tokens
    assert all(t.type != "front_matter" for t in body)


def test_front_matter_format_yaml_when_block_present() -> None:
    assert load_markdown("---\nx: 1\n---\n# H\n").front_matter_format == "yaml"


def test_front_matter_format_none_when_absent() -> None:
    """Plain markdown with no `---` delimiters reports no format."""
    assert load_markdown("# Just a heading\n").front_matter_format is None


def test_front_matter_content_preserves_inner_text() -> None:
    """The raw YAML text round-trips into LoadResult.front_matter."""
    src = "---\ntitle: t\nauthor: s\n---\n# H\n"
    assert load_markdown(src).front_matter == "title: t\nauthor: s"


def test_front_matter_only_source_yields_empty_body_tokens() -> None:
    """A file whose only content is front-matter has no body tokens —
    this is the trigger for EmptyMarkdownError downstream."""
    src = "---\nonly: matter\n---\n"
    assert load_markdown(src).tokens == ()


# --- GFM knob negative-space ----------------------------------------------


def test_gfm_disabled_emits_no_table_tokens() -> None:
    """Without GFM, a pipe-table syntax falls back to paragraphs."""
    src = "| a | b |\n|---|---|\n| 1 | 2 |\n"
    tokens = load_markdown(src, gfm=False).tokens
    assert all(t.type not in ("table_open", "th_open", "td_open") for t in tokens)


def test_gfm_enabled_emits_table_open() -> None:
    """With GFM, the same input tokenises a table_open."""
    src = "| a | b |\n|---|---|\n| 1 | 2 |\n"
    tokens = load_markdown(src, gfm=True).tokens
    assert any(t.type == "table_open" for t in tokens)


# --- Boundaries -----------------------------------------------------------


def test_empty_input_yields_empty_tokens() -> None:
    assert load_markdown("").tokens == ()


def test_whitespace_only_input_yields_empty_tokens() -> None:
    assert load_markdown("   \n\n\t\n").tokens == ()


# --- Block-token contract -------------------------------------------------


def test_block_open_tokens_carry_source_line_map() -> None:
    """The harvester relies on token.map being [line_begin, line_end] for
    every *_open block token. Regression-test the contract."""
    src = "# H\n\npara\n"
    tokens = load_markdown(src).tokens
    block_opens = [t for t in tokens if t.type in ("heading_open", "paragraph_open")]
    assert all(t.map is not None and len(t.map) == 2 for t in block_opens)


# --- Smoke ----------------------------------------------------------------


def test_build_parser_returns_object_with_parse() -> None:
    """End-to-end smoke that build_parser produces a usable MarkdownIt."""
    md = build_parser()
    tokens = md.parse("# H\n")
    assert any(t.type == "heading_open" for t in tokens)
