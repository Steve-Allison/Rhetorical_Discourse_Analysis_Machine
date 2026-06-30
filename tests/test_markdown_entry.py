"""Unit + integration tests for ``isanlp_rst.markdown.parse_markdown``.

Fast unit tests cover the pure helpers, the error-path guards that fire
before any model load, and — via a stub parser — the two-level table
analysis orchestration and the on-disk cache.

Integration tests (``@pytest.mark.slow``) load ``gumrrg`` weights once
and verify end-to-end behaviour on representative markdown fixtures.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from isanlp_rst.markdown import parse_markdown
from isanlp_rst.markdown._entry import (
    DEFAULT_MAX_HARVEST_CHARS,
    SCHEMA_NAME,
    SCHEMA_VERSION,
    TOOL_NAME,
    _resolve_inventory,
    _resolve_tool_version,
    _source_origin,
)
from isanlp_rst.markdown.errors import (
    EmptyHarvestError,
    EmptyMarkdownError,
    InputTooLargeError,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "markdown"
MINIMAL = FIXTURES / "minimal.md"
MULTI_LEVEL = FIXTURES / "multi-level.md"
GFM_RICH = FIXTURES / "gfm-rich.md"


# --- Stub parser -------------------------------------------------------------


@dataclass
class _Node:
    """Duck-typed DiscourseUnit stand-in."""

    start: int
    end: int
    left: "_Node | None" = None
    right: "_Node | None" = None
    relation: str = ""
    nuclearity: str = ""


class StubParser:
    """Deterministic Parser stand-in — no model load.

    Splits at the first ``\\n\\n`` into a two-leaf NS tree when present,
    otherwise returns a single-leaf tree. Records every input text.
    """

    def __init__(self) -> None:
        self.calls: list[str] = []

    def __call__(self, text: str) -> dict:
        self.calls.append(text)
        n = len(text)
        if "\n\n" in text:
            cut = text.index("\n\n")
            left = _Node(0, cut)
            right = _Node(cut + 2, n)
            root = _Node(0, n, left, right, "elaboration", "NS")
        else:
            root = _Node(0, n)
        return {"rst": [root]}


# ===========================================================================
# Fast unit tests — no model load
# ===========================================================================


# --- _resolve_tool_version — caching invariant -----------------------------


def test_resolve_tool_version_is_cached() -> None:
    """``@cache`` invariant: identical object across calls."""
    assert _resolve_tool_version() is _resolve_tool_version()


# --- _resolve_inventory — precedence contract -----------------------------


def test_inventory_explicit_overrides_model_version() -> None:
    assert _resolve_inventory("unirst", "eng.erst.gum") == "eng.erst.gum"


def test_inventory_falls_back_to_model_version() -> None:
    assert _resolve_inventory("gumrrg", None) == "gumrrg"


# --- _source_origin shape --------------------------------------------------


def test_source_origin_carries_front_matter_when_present() -> None:
    origin = _source_origin("title: t", "yaml", gfm=True)
    assert origin == {
        "format": "markdown",
        "gfm": True,
        "front_matter": "title: t",
        "front_matter_format": "yaml",
    }


def test_source_origin_null_front_matter_when_absent() -> None:
    origin = _source_origin(None, None, gfm=False)
    assert origin["front_matter"] is None
    assert origin["front_matter_format"] is None
    assert origin["gfm"] is False


# --- Schema constants — regression-pinned ----------------------------------


def test_schema_constants_pinned() -> None:
    """Pin the wire-format identifier — downstream consumers branch on it."""
    assert SCHEMA_NAME == "isanlp_rst_markdown"
    assert SCHEMA_VERSION == "1.0"
    assert TOOL_NAME == "isanlp_rst"
    assert DEFAULT_MAX_HARVEST_CHARS == 200_000


# --- Error-path guards (fire before any model load) -------------------------


def test_input_too_large_error_with_threshold_message() -> None:
    with pytest.raises(InputTooLargeError) as excinfo:
        parse_markdown(MINIMAL, max_harvest_chars=10)
    assert "exceeds max_harvest_chars=10" in str(excinfo.value)


def test_str_and_path_input_reach_same_guard() -> None:
    with pytest.raises(InputTooLargeError):
        parse_markdown(MINIMAL, max_harvest_chars=10)
    with pytest.raises(InputTooLargeError):
        parse_markdown(str(MINIMAL), max_harvest_chars=10)


def test_empty_markdown_error_on_whitespace_only(tmp_path: Path) -> None:
    p = tmp_path / "ws.md"
    p.write_text("   \n\n   \n")
    with pytest.raises(EmptyMarkdownError):
        parse_markdown(p)


def test_empty_markdown_error_on_front_matter_only(tmp_path: Path) -> None:
    """A file whose only content is front-matter has no body tokens."""
    p = tmp_path / "fm.md"
    p.write_text("---\ntitle: t\n---\n")
    with pytest.raises(EmptyMarkdownError):
        parse_markdown(p)


def test_empty_harvest_error_on_divider_only(tmp_path: Path) -> None:
    """Thematic breaks tokenise but harvest nothing."""
    p = tmp_path / "hr.md"
    p.write_text("---\n\n***\n")
    with pytest.raises((EmptyMarkdownError, EmptyHarvestError)):
        parse_markdown(p)


# --- Two-level table analysis (stub parser, no model) ----------------------

TABLE_DOC = "# T\n\nIntro para.\n\n| h1 | h2 |\n|----|----|\n| a  | b  |\n"


def test_table_only_doc_parses_with_empty_main_tree(tmp_path: Path) -> None:
    """A table-only document must NOT raise: the main tree is empty and
    the table analysis carries the content."""
    p = tmp_path / "table_only.md"
    p.write_text("| h |\n|---|\n| a |\n| b |\n")
    stub = StubParser()
    result = parse_markdown(p, parser=stub)  # type: ignore[arg-type]
    assert result.relations == ()
    assert result.edus == ()
    assert len(result.table_analyses) == 1
    assert result.table_analyses[0].edus


def test_table_analysis_refs_resolve_against_table_boundary(tmp_path: Path) -> None:
    p = tmp_path / "doc.md"
    p.write_text(TABLE_DOC)
    stub = StubParser()
    result = parse_markdown(p, parser=stub)  # type: ignore[arg-type]
    (analysis,) = result.table_analyses
    table_boundary = next(b for b in result.boundaries if b.id == analysis.id)
    for edu in analysis.edus:
        for ref in edu.block_refs:
            assert ref in table_boundary.block_refs


def test_main_relations_never_reference_cells(tmp_path: Path) -> None:
    """Two-level invariant: the document tree knows nothing of cells."""
    p = tmp_path / "doc.md"
    p.write_text(TABLE_DOC)
    result = parse_markdown(p, parser=StubParser())  # type: ignore[arg-type]
    for r in result.relations:
        for ref in (*r.nucleus_refs, *r.satellite_refs):
            assert not ref.startswith("#/tables/")


def test_include_table_cells_false_drops_analyses_and_table_boundaries(
    tmp_path: Path,
) -> None:
    p = tmp_path / "doc.md"
    p.write_text(TABLE_DOC)
    result = parse_markdown(p, parser=StubParser(), include_table_cells=False)  # type: ignore[arg-type]
    assert result.table_analyses == ()
    assert not any(b.kind == "table" for b in result.boundaries)


def test_one_parser_call_per_table_plus_main(tmp_path: Path) -> None:
    p = tmp_path / "doc.md"
    p.write_text(TABLE_DOC + "\n| x |\n|---|\n| y |\n")
    stub = StubParser()
    parse_markdown(p, parser=stub)  # type: ignore[arg-type]
    assert len(stub.calls) == 3  # main + 2 tables


# --- On-disk result cache ---------------------------------------------------


def test_cache_round_trip_skips_reparse(tmp_path: Path) -> None:
    p = tmp_path / "doc.md"
    p.write_text(TABLE_DOC)
    cache = tmp_path / "cache"
    stub = StubParser()
    first = parse_markdown(p, parser=stub, cache_dir=cache)  # type: ignore[arg-type]
    calls_after_first = len(stub.calls)
    second = parse_markdown(p, parser=stub, cache_dir=cache)  # type: ignore[arg-type]
    assert len(stub.calls) == calls_after_first  # no new parses
    assert first == second


def test_cache_misses_when_knobs_change(tmp_path: Path) -> None:
    """A different knob set must produce a different key, not a stale hit."""
    p = tmp_path / "doc.md"
    p.write_text(TABLE_DOC)
    cache = tmp_path / "cache"
    stub = StubParser()
    parse_markdown(p, parser=stub, cache_dir=cache)  # type: ignore[arg-type]
    calls_after_first = len(stub.calls)
    parse_markdown(p, parser=stub, cache_dir=cache, include_code_blocks=False)  # type: ignore[arg-type]
    assert len(stub.calls) > calls_after_first


def test_cache_misses_when_source_changes(tmp_path: Path) -> None:
    p = tmp_path / "doc.md"
    p.write_text("para one\n")
    cache = tmp_path / "cache"
    stub = StubParser()
    parse_markdown(p, parser=stub, cache_dir=cache)  # type: ignore[arg-type]
    p.write_text("para two\n")
    parse_markdown(p, parser=stub, cache_dir=cache)  # type: ignore[arg-type]
    assert len(stub.calls) == 2


# --- Serialisation -----------------------------------------------------------


def test_to_dict_round_trips_through_json(tmp_path: Path) -> None:
    """to_json must be valid JSON whose payload equals to_dict."""
    import json

    p = tmp_path / "doc.md"
    p.write_text(TABLE_DOC)
    result = parse_markdown(p, parser=StubParser())  # type: ignore[arg-type]
    payload = result.to_dict()
    assert json.loads(result.to_json()) == json.loads(json.dumps(payload))
    assert payload["schema_name"] == SCHEMA_NAME
    assert payload["table_analyses"][0]["id"] == "table-0"


def test_golden_output_shape(tmp_path: Path) -> None:
    """Golden-output regression: the serialised shape for a fixed source
    + deterministic stub tree must match the committed golden file
    (tool_version normalised — it varies per checkout state)."""
    import json

    p = tmp_path / "golden_src.md"
    p.write_text("# Title\n\nFirst para.\n\nSecond para.\n")
    result = parse_markdown(p, parser=StubParser())  # type: ignore[arg-type]
    got = result.to_dict()
    got["tool_version"] = "<normalised>"
    golden = json.loads((FIXTURES / "golden_two_para.rst.json").read_text())
    assert got == golden


# ===========================================================================
# Integration tests — model load required (slow-marked)
# ===========================================================================


@pytest.fixture(scope="module")
def parser():
    """Construct gumrrg parser once for the slow tests."""
    from isanlp_rst.parser import Parser
    return Parser(hf_model_version="gumrrg", device="auto")


@pytest.mark.slow
def test_parse_markdown_emits_expected_metadata(parser) -> None:
    """End-to-end smoke: verify the result carries the pinned wire-format
    identifiers and has non-empty boundaries/relations/edus."""
    result = parse_markdown(MINIMAL, parser=parser)
    assert result.schema_name == SCHEMA_NAME
    assert result.schema_version == SCHEMA_VERSION
    assert result.tool == TOOL_NAME
    assert result.source == "minimal.md"
    assert result.model_version == "gumrrg"
    assert result.boundaries
    assert result.relations
    assert result.edus


@pytest.mark.slow
def test_parse_markdown_ids_resolve_left_right(parser) -> None:
    """Shared id namespace invariant — every left/right ref points
    to a known relation OR edu."""
    result = parse_markdown(MULTI_LEVEL, parser=parser)
    known = {r.id for r in result.relations} | {e.id for e in result.edus}
    for r in result.relations:
        assert r.left_id in known
        assert r.right_id in known


@pytest.mark.slow
def test_parse_markdown_table_analysis_end_to_end(parser) -> None:
    """gfm-rich has one table → one analysis whose refs resolve against
    the table boundary; the main tree never references cells."""
    result = parse_markdown(GFM_RICH, parser=parser)
    (analysis,) = result.table_analyses
    table_boundary = next(b for b in result.boundaries if b.id == analysis.id)
    for edu in analysis.edus:
        for ref in edu.block_refs:
            assert ref in table_boundary.block_refs
    for r in result.relations:
        for ref in (*r.nucleus_refs, *r.satellite_refs):
            assert not ref.startswith("#/tables/")


@pytest.mark.slow
def test_parse_markdown_relation_refs_are_harvested_block_refs(parser) -> None:
    """Round-trip closure: every relation ref must be a HarvestSpan block_ref."""
    from isanlp_rst.markdown.harvester import harvest_markdown_text
    from isanlp_rst.markdown.loader import load_markdown
    src = MULTI_LEVEL.read_text(encoding="utf-8")
    expected = {s.block_ref for s in harvest_markdown_text(load_markdown(src).tokens).spans}

    result = parse_markdown(MULTI_LEVEL, parser=parser)
    for r in result.relations:
        for ref in (*r.nucleus_refs, *r.satellite_refs):
            assert ref in expected, f"unknown ref: {ref}"


@pytest.mark.slow
def test_parse_markdown_parser_injection_consistent(parser) -> None:
    """Idempotence: same input + same parser → identical relation shape."""
    a = parse_markdown(MULTI_LEVEL, parser=parser)
    b = parse_markdown(MULTI_LEVEL, parser=parser)
    assert len(a.relations) == len(b.relations)
    assert len(a.edus) == len(b.edus)
    assert [r.relation for r in a.relations] == [r.relation for r in b.relations]
