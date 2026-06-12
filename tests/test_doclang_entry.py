"""Unit + integration tests for ``isanlp_rst.doclang.parse_doclang``.

Fast unit tests cover the pure helpers (device translation, tool-version
resolution, source-origin capture, inventory selection) and the
error-path guards that fire before any model load
(``EmptyDoclangError``, ``EmptyHarvestError``, ``InputTooLargeError``).

Integration tests (``@pytest.mark.slow``) load ``gumrrg`` weights once
and verify end-to-end behaviour on a representative DocLang fixture.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from isanlp_rst.doclang import parse_doclang
from isanlp_rst.doclang._entry import (
    DEFAULT_MAX_HARVEST_CHARS,
    SCHEMA_NAME,
    SCHEMA_VERSION,
    TOOL_NAME,
    _resolve_device,
    _resolve_inventory,
    _resolve_tool_version,
    _source_origin,
)
from isanlp_rst.doclang.errors import (
    EmptyDoclangError,
    EmptyHarvestError,
    InputTooLargeError,
)
from isanlp_rst.doclang.loader import parse_doclang_xml

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "doclang"
COMPREHENSIVE = FIXTURES / "ok_comprehensive.dclg.xml"
TABLE_ONLY = FIXTURES / "ok_table_rectangular.dclg.xml"


# ===========================================================================
# Fast unit tests — no model load
# ===========================================================================


# --- _resolve_device -------------------------------------------------------


@pytest.mark.parametrize(
    "device,expected",
    [
        ("cpu", -1),
        ("mps", 0),
        ("cuda", 0),
        ("cuda:0", 0),
        ("cuda:1", 1),
        ("cuda:7", 7),
    ],
)
def test_resolve_device_valid(device: str, expected: int) -> None:
    assert _resolve_device(device) == expected


def test_resolve_device_auto_follows_torch_backends() -> None:
    """``auto`` is 0 when torch reports a backend, -1 (CPU) otherwise."""
    import torch

    expected = 0 if (torch.cuda.is_available() or torch.backends.mps.is_available()) else -1
    assert _resolve_device("auto") == expected


@pytest.mark.parametrize(
    "device",
    [
        "",
        "gpu",
        "tpu",
        "CUDA",
        "cuda:",
        "cuda:abc",
        "cuda:-1",
        "cuda:0:1",
        "mps:0",
    ],
)
def test_resolve_device_invalid_raises(device: str) -> None:
    with pytest.raises(ValueError):
        _resolve_device(device)


# --- _resolve_tool_version -------------------------------------------------


def test_resolve_tool_version_returns_non_empty_string() -> None:
    v = _resolve_tool_version()
    assert isinstance(v, str)
    assert v != ""


def test_resolve_tool_version_is_cached() -> None:
    assert _resolve_tool_version() is _resolve_tool_version()


# --- _resolve_inventory ----------------------------------------------------


def test_resolve_inventory_explicit_wins() -> None:
    assert _resolve_inventory("unirst", "eng.erst.gum") == "eng.erst.gum"


def test_resolve_inventory_falls_back_to_model_version() -> None:
    assert _resolve_inventory("gumrrg", None) == "gumrrg"


# --- _source_origin --------------------------------------------------------


def test_source_origin_includes_namespace_when_declared() -> None:
    tree = parse_doclang_xml(COMPREHENSIVE)
    origin = _source_origin(tree)
    assert origin["format"] == "doclang"
    assert origin["namespace"] == "https://www.doclang.ai/ns/v0"
    assert origin["version"] == "0.5"


def test_source_origin_empty_namespace_when_absent() -> None:
    tree = parse_doclang_xml(FIXTURES / "ok_no_namespace.dclg.xml")
    origin = _source_origin(tree)
    assert origin["namespace"] == ""


def test_source_origin_lists_head_children_when_present() -> None:
    """``ok_comprehensive.dclg.xml`` has ``<head>`` with several children
    (title, author, date, keywords, custom-field)."""
    tree = parse_doclang_xml(COMPREHENSIVE)
    origin = _source_origin(tree)
    assert "title" in origin["head_children"]
    assert "author" in origin["head_children"]


def test_source_origin_no_head_returns_empty_list() -> None:
    tree = parse_doclang_xml(FIXTURES / "ok_no_namespace.dclg.xml")
    origin = _source_origin(tree)
    assert origin["head_children"] == []


# --- Constants -------------------------------------------------------------


def test_schema_constants() -> None:
    assert SCHEMA_NAME == "isanlp_rst_doclang"
    assert SCHEMA_VERSION == "1.0"
    assert TOOL_NAME == "isanlp_rst"
    assert DEFAULT_MAX_HARVEST_CHARS == 200_000


# --- Error-path guards (fire before any model load) ------------------------


def test_input_too_large_error_raised_with_path() -> None:
    """``ok_comprehensive`` harvests > 10 chars — guard fires before the
    parser is constructed."""
    with pytest.raises(InputTooLargeError) as excinfo:
        parse_doclang(COMPREHENSIVE, validate_xml=False, max_harvest_chars=10)
    assert "exceeds max_harvest_chars=10" in str(excinfo.value)


def test_input_too_large_error_str_and_path_equivalent() -> None:
    """Path and str inputs reach the same guard."""
    with pytest.raises(InputTooLargeError):
        parse_doclang(COMPREHENSIVE, validate_xml=False, max_harvest_chars=10)
    with pytest.raises(InputTooLargeError):
        parse_doclang(str(COMPREHENSIVE), validate_xml=False, max_harvest_chars=10)


def test_empty_doclang_error_on_root_only(tmp_path: Path) -> None:
    """A ``<doclang/>`` with no body must raise ``EmptyDoclangError``."""
    empty_path = tmp_path / "empty.dclg.xml"
    empty_path.write_bytes(b'<doclang xmlns="https://www.doclang.ai/ns/v0"/>')
    with pytest.raises(EmptyDoclangError):
        parse_doclang(empty_path, validate_xml=False)


def test_empty_doclang_error_with_head_only(tmp_path: Path) -> None:
    """A doc whose only child is ``<head>`` has no body."""
    path = tmp_path / "head_only.dclg.xml"
    path.write_bytes(
        b'<doclang xmlns="https://www.doclang.ai/ns/v0">'
        b"<head><title>x</title></head>"
        b"</doclang>"
    )
    with pytest.raises(EmptyDoclangError):
        parse_doclang(path, validate_xml=False)


def test_table_only_raises_only_when_table_analysis_disabled() -> None:
    """Two-level analysis: a table-only document is parseable (the
    content lives in table_analyses), so EmptyHarvestError fires only
    when ``include_table_cells=False`` removes the last harvestable
    content."""
    with pytest.raises(EmptyHarvestError):
        parse_doclang(
            TABLE_ONLY, validate_xml=False, include_table_cells=False
        )


class _StubNode:
    """Duck-typed DiscourseUnit stand-in for two-level orchestration tests."""

    def __init__(self, start: int, end: int, left=None, right=None,
                 relation: str = "", nuclearity: str = "") -> None:
        self.start = start
        self.end = end
        self.left = left
        self.right = right
        self.relation = relation
        self.nuclearity = nuclearity


class _StubParser:
    """Deterministic Parser stand-in — splits at the first separator."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def __call__(self, text: str) -> dict:
        self.calls.append(text)
        n = len(text)
        if "\n\n" in text:
            cut = text.index("\n\n")
            root = _StubNode(0, n, _StubNode(0, cut), _StubNode(cut + 2, n),
                             "elaboration", "NS")
        else:
            root = _StubNode(0, n)
        return {"rst": [root]}


def test_table_only_doc_produces_analyses_with_empty_main_tree() -> None:
    """The 3-table fixture parses to an empty main tree + 3 analyses
    whose refs resolve against their boundaries."""
    stub = _StubParser()
    result = parse_doclang(TABLE_ONLY, parser=stub, validate_xml=False)  # type: ignore[arg-type]
    assert result.relations == ()
    assert result.edus == ()
    assert [a.id for a in result.table_analyses] == ["table-0", "table-1", "table-2"]
    boundary_by_id = {b.id: b for b in result.boundaries}
    for analysis in result.table_analyses:
        boundary = boundary_by_id[analysis.id]
        for edu in analysis.edus:
            for xp in edu.xpaths:
                assert xp in boundary.xpaths
    assert len(stub.calls) == 3  # no main parse, one per table


# ===========================================================================
# Integration tests — model load required (slow-marked)
# ===========================================================================


@pytest.fixture(scope="module")
def parser():
    """Construct gumrrg parser once for the slow tests."""
    from isanlp_rst.parser import Parser
    return Parser(hf_model_version="gumrrg", cuda_device=0)


@pytest.mark.slow
def test_parse_doclang_end_to_end(parser) -> None:
    result = parse_doclang(COMPREHENSIVE, parser=parser, validate_xml=False)

    assert result.schema_name == SCHEMA_NAME
    assert result.schema_version == SCHEMA_VERSION
    assert result.tool == TOOL_NAME
    assert result.source == "ok_comprehensive.dclg.xml"
    assert result.model_version == "gumrrg"
    assert result.inventory == "gumrrg"

    assert len(result.relations) > 0
    assert len(result.edus) > 0
    assert len(result.boundaries) > 0
    assert result.source_origin["format"] == "doclang"


@pytest.mark.slow
def test_parse_doclang_ids_resolve_left_right(parser) -> None:
    result = parse_doclang(COMPREHENSIVE, parser=parser, validate_xml=False)
    all_ids = {r.id for r in result.relations} | {e.id for e in result.edus}
    for relation in result.relations:
        assert relation.left_id in all_ids, f"left_id {relation.left_id} unresolved"
        assert relation.right_id in all_ids, f"right_id {relation.right_id} unresolved"


@pytest.mark.slow
def test_parse_doclang_main_relations_never_reference_tables(parser) -> None:
    """Two-level invariant: table content (cells AND the synthetic
    marker) lives in table_analyses, never in the main tree."""
    result = parse_doclang(COMPREHENSIVE, parser=parser, validate_xml=False)
    for relation in result.relations:
        for xp in (*relation.nucleus_xpaths, *relation.satellite_xpaths):
            assert "/table[" not in xp, f"table xpath leaked into main tree: {xp}"


@pytest.mark.slow
def test_parse_doclang_relation_xpaths_in_harvest_set(parser) -> None:
    """Every relation xpath points to a harvest span's xpath."""
    from isanlp_rst.doclang.harvester import harvest_doclang_text
    tree = parse_doclang_xml(COMPREHENSIVE)
    expected = {s.xpath for s in harvest_doclang_text(tree).spans}

    result = parse_doclang(COMPREHENSIVE, parser=parser, validate_xml=False)
    for relation in result.relations:
        for xp in (*relation.nucleus_xpaths, *relation.satellite_xpaths):
            assert xp in expected, f"unknown xpath: {xp}"


@pytest.mark.slow
def test_parse_doclang_thread_ids_captured_when_present(parser) -> None:
    """``ok_thread.dclg.xml`` — both ``<text>`` elements carry
    ``thread_id=1``. Any relation over them must mention thread id 1."""
    result = parse_doclang(
        FIXTURES / "ok_thread.dclg.xml", parser=parser, validate_xml=False
    )
    seen = set()
    for relation in result.relations:
        seen.update(relation.nucleus_thread_ids)
        seen.update(relation.satellite_thread_ids)
    for edu in result.edus:
        seen.update(edu.thread_ids)
    assert 1 in seen


@pytest.mark.slow
def test_parse_doclang_parser_injection_consistent(parser) -> None:
    """Two calls with the same injected parser produce the same shape."""
    a = parse_doclang(COMPREHENSIVE, parser=parser, validate_xml=False)
    b = parse_doclang(COMPREHENSIVE, parser=parser, validate_xml=False)
    assert len(a.relations) == len(b.relations)
    assert len(a.edus) == len(b.edus)
    assert [r.relation for r in a.relations] == [r.relation for r in b.relations]
