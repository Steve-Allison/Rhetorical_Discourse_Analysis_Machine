"""Unit + integration tests for ``isanlp_rst.doclang.parse_doclang``.

Fast unit tests cover the pure helpers (device translation, tool-version
resolution, source-origin capture, inventory selection) and the
error-path guards that fire before any model load
(``EmptyDoclangError``, ``EmptyHarvestError``, ``InputTooLargeError``).

Integration tests (``@pytest.mark.slow``) load ``gumrrg`` weights once
and verify end-to-end behaviour on a representative DocLang fixture.
"""

import importlib
from pathlib import Path

import pytest

from isanlp_rst.doclang import parse_doclang
from isanlp_rst.doclang._entry import (
    DEFAULT_MAX_HARVEST_CHARS,
    SCHEMA_NAME,
    SCHEMA_VERSION,
    TOOL_NAME,
    _resolve_inventory,
    _resolve_tool_version,
    _source_origin,
)
from isanlp_rst.doclang.errors import (
    EmptyDoclangError,
    EmptyHarvestError,
    InputTooLargeError,
    InvalidDoclangError,
)
from isanlp_rst.doclang.harvester import harvest_doclang_text
from isanlp_rst.doclang.loader import parse_doclang_xml
from isanlp_rst.parser import Parser

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "doclang"
COMPREHENSIVE = FIXTURES / "ok_comprehensive.dclg.xml"
TABLE_ONLY = FIXTURES / "ok_table_rectangular.dclg.xml"


# ===========================================================================
# Fast unit tests — no model load
# ===========================================================================


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
    assert origin["version"] == ""


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
    path.write_bytes(b'<doclang xmlns="https://www.doclang.ai/ns/v0"><head><title>x</title></head></doclang>')
    with pytest.raises(EmptyDoclangError):
        parse_doclang(path, validate_xml=False)


def test_table_only_raises_only_when_table_analysis_disabled() -> None:
    """Two-level analysis: a table-only document is parseable (the
    content lives in table_analyses), so EmptyHarvestError fires only
    when ``include_table_cells=False`` removes the last harvestable
    content."""
    with pytest.raises(EmptyHarvestError):
        parse_doclang(TABLE_ONLY, validate_xml=False, include_table_cells=False)


class _StubNode:
    """Duck-typed DiscourseUnit stand-in for two-level orchestration tests."""

    def __init__(self, start: int, end: int, left=None, right=None, relation: str = "", nuclearity: str = "") -> None:
        self.start = start
        self.end = end
        self.left = left
        self.right = right
        self.relation = relation
        self.nuclearity = nuclearity


class _StubParser:
    """Deterministic Parser stand-in — splits at the first separator."""

    def __init__(
        self,
        hf_model_name: str | None = None,
        hf_model_version: str | None = None,
        relinventory: str | None = None,
    ) -> None:
        self.calls: list[str] = []
        self.hf_model_name = hf_model_name
        self.hf_model_version = hf_model_version
        self.relinventory = relinventory

    def __call__(self, text: str) -> dict:
        self.calls.append(text)
        n = len(text)
        if "\n\n" in text:
            cut = text.index("\n\n")
            root = _StubNode(0, n, _StubNode(0, cut), _StubNode(cut + 2, n), "elaboration", "NS")
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


def test_cache_round_trip_skips_reparse(tmp_path: Path) -> None:
    cache = tmp_path / "cache"
    stub = _StubParser()
    first = parse_doclang(
        COMPREHENSIVE,
        parser=stub,  # type: ignore[arg-type]
        validate_xml=False,
        cache_dir=cache,
    )
    calls_after_first = len(stub.calls)
    second = parse_doclang(
        COMPREHENSIVE,
        parser=stub,  # type: ignore[arg-type]
        validate_xml=False,
        cache_dir=cache,
    )
    assert len(stub.calls) == calls_after_first
    assert first == second


def test_cache_misses_when_validate_xml_changes(tmp_path: Path) -> None:
    """``validate_xml`` is a parse-affecting knob and must be in the key.

    A cached ``validate_xml=False`` result must not be returned when the
    caller asks for ``validate_xml=True``. Either we reparse (full
    Schematron backend available) or validation runs and raises
    ``InvalidDoclangError`` — both prove the cache missed.
    """
    pytest.importorskip("doclang")
    cache = tmp_path / "cache"
    stub = _StubParser()
    parse_doclang(
        COMPREHENSIVE,
        parser=stub,  # type: ignore[arg-type]
        validate_xml=False,
        cache_dir=cache,
    )
    calls_after_first = len(stub.calls)
    try:
        parse_doclang(
            COMPREHENSIVE,
            parser=stub,  # type: ignore[arg-type]
            validate_xml=True,
            cache_dir=cache,
        )
    except InvalidDoclangError:
        # Cache miss: validation executed instead of returning the
        # validate_xml=False entry. (Common when doclang is installed
        # without a Schematron backend.)
        assert len(stub.calls) == calls_after_first
        return
    assert len(stub.calls) > calls_after_first


def test_cache_misses_when_source_changes(tmp_path: Path) -> None:
    cache = tmp_path / "cache"
    stub = _StubParser()
    path = tmp_path / "doc.dclg.xml"
    original = COMPREHENSIVE.read_text(encoding="utf-8")
    path.write_text(original, encoding="utf-8")
    parse_doclang(path, parser=stub, validate_xml=False, cache_dir=cache)  # type: ignore[arg-type]
    # Trailing whitespace changes source bytes without breaking XML.
    path.write_text(original + "\n", encoding="utf-8")
    parse_doclang(path, parser=stub, validate_xml=False, cache_dir=cache)  # type: ignore[arg-type]
    assert len(stub.calls) >= 2


def test_cache_misses_when_hf_model_name_changes(tmp_path: Path) -> None:
    cache = tmp_path / "cache"
    stub = _StubParser()
    parse_doclang(
        COMPREHENSIVE,
        parser=stub,  # type: ignore[arg-type]
        validate_xml=False,
        cache_dir=cache,
        hf_model_name="repo/model-a",
    )
    calls_after_first = len(stub.calls)
    parse_doclang(
        COMPREHENSIVE,
        parser=stub,  # type: ignore[arg-type]
        validate_xml=False,
        cache_dir=cache,
        hf_model_name="repo/model-b",
    )
    assert len(stub.calls) > calls_after_first


def test_cache_misses_when_injected_parser_identity_differs(tmp_path: Path) -> None:
    cache = tmp_path / "cache"
    stub_a = _StubParser()
    parse_doclang(
        COMPREHENSIVE,
        parser=stub_a,  # type: ignore[arg-type]
        validate_xml=False,
        cache_dir=cache,
    )
    stub_b = _StubParser(hf_model_version="rstdt")
    parse_doclang(
        COMPREHENSIVE,
        parser=stub_b,  # type: ignore[arg-type]
        validate_xml=False,
        cache_dir=cache,
    )
    assert len(stub_b.calls) > 0


def test_cache_misses_when_device_changes(tmp_path: Path) -> None:
    """``device`` is part of the cache key (locked Wave 4 contract)."""
    cache = tmp_path / "cache"
    stub = _StubParser()
    parse_doclang(
        COMPREHENSIVE,
        parser=stub,  # type: ignore[arg-type]
        validate_xml=False,
        cache_dir=cache,
        device="cpu",
    )
    calls_after_first = len(stub.calls)
    parse_doclang(
        COMPREHENSIVE,
        parser=stub,  # type: ignore[arg-type]
        validate_xml=False,
        cache_dir=cache,
        device="mps",
    )
    assert len(stub.calls) > calls_after_first


def test_validate_xml_import_error_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    """Missing ``doclang`` package must raise ``InvalidDoclangError``, not skip."""
    real_import = importlib.import_module

    def _boom(name: str, package=None):
        if name == "doclang":
            raise ImportError("simulated missing doclang")
        return real_import(name, package)

    monkeypatch.setattr(importlib, "import_module", _boom)
    stub = _StubParser()
    with pytest.raises(InvalidDoclangError, match="requires the doclang package"):
        parse_doclang(
            COMPREHENSIVE,
            parser=stub,  # type: ignore[arg-type]
            validate_xml=True,
        )
    assert stub.calls == []


def test_main_relations_never_reference_table_cell_xpaths() -> None:
    """Two-level invariant on a mixed prose+table fixture."""
    stub = _StubParser()
    result = parse_doclang(
        COMPREHENSIVE,
        parser=stub,  # type: ignore[arg-type]
        validate_xml=False,
    )
    for relation in result.relations:
        for xp in (*relation.nucleus_xpaths, *relation.satellite_xpaths):
            assert "/table[" not in xp, f"table xpath leaked into main tree: {xp}"
            last = xp.rsplit("/", 1)[-1]
            local = last.split("[", 1)[0]
            assert local not in {"ched", "fcel", "rhed", "corn", "ecel", "nl"}, xp


def test_include_table_cells_false_drops_analyses() -> None:
    stub = _StubParser()
    result = parse_doclang(
        COMPREHENSIVE,
        parser=stub,  # type: ignore[arg-type]
        validate_xml=False,
        include_table_cells=False,
    )
    assert result.table_analyses == ()


def test_result_metadata_follows_injected_parser_not_kwargs() -> None:
    stub = _StubParser(hf_model_version="rstdt")
    result = parse_doclang(
        TABLE_ONLY,
        parser=stub,  # type: ignore[arg-type]
        validate_xml=False,
        hf_model_version="gumrrg",
    )
    assert result.model_version == "rstdt"
    assert result.inventory == "rstdt"


def test_validate_xml_true_fail_closed_wraps_backend_errors() -> None:
    """``validate_xml=True`` must not skip validation when Schematron is absent.

    Either validation succeeds (full backend installed) or we get
    ``InvalidDoclangError`` — never a silent proceed-as-valid.
    """
    pytest.importorskip("doclang")
    stub = _StubParser()
    try:
        parse_doclang(
            COMPREHENSIVE,
            parser=stub,  # type: ignore[arg-type]
            validate_xml=True,
        )
    except InvalidDoclangError as exc:
        assert "validation" in str(exc).lower() or "doclang" in str(exc).lower()
        assert stub.calls == []  # failed before any parse
        return
    # Backend available: must have actually parsed (not a no-op skip).
    assert stub.calls


def test_table_only_with_cells_disabled_raises_empty_harvest() -> None:
    with pytest.raises(EmptyHarvestError):
        parse_doclang(
            TABLE_ONLY,
            parser=_StubParser(),  # type: ignore[arg-type]
            validate_xml=False,
            include_table_cells=False,
        )


# ===========================================================================
# Integration tests — model load required (slow-marked)
# ===========================================================================


@pytest.fixture(scope="module")
def parser():
    """Construct gumrrg parser once for the slow tests."""
    return Parser(hf_model_version="gumrrg", device="auto")


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
    result = parse_doclang(FIXTURES / "ok_thread.dclg.xml", parser=parser, validate_xml=False)
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
