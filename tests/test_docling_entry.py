"""Unit + integration tests for ``isanlp_rst.docling.parse_docling``.

Fast unit tests cover the pure helpers (device translation, tool-version
resolution, source-origin serialisation, inventory selection) and the
error-path guards that fire before any model load
(``InputTooLargeError``).

Integration tests (``@pytest.mark.slow``) load ``gumrrg`` weights once
and verify end-to-end behaviour on the real fixtures, including the
parser-injection contract.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from docling_core.types.doc.document import DoclingDocument

from isanlp_rst.docling import parse_docling
from isanlp_rst.docling._entry import (
    DEFAULT_MAX_HARVEST_CHARS,
    SCHEMA_NAME,
    SCHEMA_VERSION,
    TOOL_NAME,
    _resolve_device,
    _resolve_inventory,
    _resolve_tool_version,
    _serialise_source_origin,
)
from isanlp_rst.docling.errors import InputTooLargeError

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "docling"
PPTX_FIXTURE = FIXTURES / "pptx.docling.json"


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
    """Two calls return the identical object — caching is the contract."""
    assert _resolve_tool_version() is _resolve_tool_version()


# --- _serialise_source_origin ---------------------------------------------


def test_serialise_source_origin_none_returns_empty_dict() -> None:
    assert _serialise_source_origin(None) == {}


def test_serialise_source_origin_real_fixture_has_mimetype_and_hash() -> None:
    doc = DoclingDocument.load_from_json(PPTX_FIXTURE)
    origin_dict = _serialise_source_origin(doc.origin)
    assert isinstance(origin_dict, dict)
    assert "mimetype" in origin_dict
    assert origin_dict["mimetype"] == "application/vnd.ms-powerpoint"
    assert "binary_hash" in origin_dict
    assert isinstance(origin_dict["binary_hash"], int)


# --- _resolve_inventory ----------------------------------------------------


def test_resolve_inventory_explicit_wins() -> None:
    assert _resolve_inventory("unirst", "eng.erst.gum") == "eng.erst.gum"


def test_resolve_inventory_falls_back_to_model_version() -> None:
    assert _resolve_inventory("gumrrg", None) == "gumrrg"


# --- Constants -------------------------------------------------------------


def test_schema_constants() -> None:
    assert SCHEMA_NAME == "isanlp_rst_docling"
    assert SCHEMA_VERSION == "1.0"
    assert TOOL_NAME == "isanlp_rst"
    assert DEFAULT_MAX_HARVEST_CHARS == 200_000


# --- InputTooLargeError (fires before any model load) ----------------------


def test_input_too_large_error_raised_with_path() -> None:
    with pytest.raises(InputTooLargeError) as excinfo:
        parse_docling(PPTX_FIXTURE, max_harvest_chars=10)
    assert "exceeds max_harvest_chars=10" in str(excinfo.value)


def test_input_too_large_error_raised_with_str() -> None:
    with pytest.raises(InputTooLargeError):
        parse_docling(str(PPTX_FIXTURE), max_harvest_chars=10)


def test_input_too_large_error_path_and_str_equivalent() -> None:
    """Path and str inputs reach the same guard."""
    with pytest.raises(InputTooLargeError):
        parse_docling(PPTX_FIXTURE, max_harvest_chars=10)
    with pytest.raises(InputTooLargeError):
        parse_docling(str(PPTX_FIXTURE), max_harvest_chars=10)


# ===========================================================================
# Integration tests — model load required (slow-marked)
# ===========================================================================


@pytest.fixture(scope="module")
def parser():
    """Construct gumrrg parser once for the slow tests."""
    from isanlp_rst.parser import Parser
    return Parser(hf_model_version="gumrrg", cuda_device=0)


@pytest.mark.slow
def test_parse_docling_pptx_end_to_end(parser) -> None:
    result = parse_docling(PPTX_FIXTURE, parser=parser)

    assert result.schema_name == SCHEMA_NAME
    assert result.schema_version == SCHEMA_VERSION
    assert result.tool == TOOL_NAME
    assert result.source == "pptx.docling.json"
    assert result.model_version == "gumrrg"
    assert result.inventory == "gumrrg"

    assert len(result.relations) > 0
    assert len(result.edus) > 0
    assert len(result.boundaries) > 0

    # source_origin populated
    assert result.source_origin.get("mimetype") == "application/vnd.ms-powerpoint"
    assert isinstance(result.source_origin.get("binary_hash"), int)


@pytest.mark.slow
def test_parse_docling_ids_resolve_left_right(parser) -> None:
    result = parse_docling(PPTX_FIXTURE, parser=parser)
    all_ids = {r.id for r in result.relations} | {e.id for e in result.edus}
    for relation in result.relations:
        assert relation.left_id in all_ids, f"left_id {relation.left_id} unresolved"
        assert relation.right_id in all_ids, f"right_id {relation.right_id} unresolved"


@pytest.mark.slow
def test_parse_docling_main_relations_never_reference_tables(parser) -> None:
    """Two-level invariant: cells live in table_analyses, the synthetic
    marker lives in the boundary — the main tree references neither."""
    result = parse_docling(PPTX_FIXTURE, parser=parser)
    for relation in result.relations:
        for ref in (*relation.nucleus_refs, *relation.satellite_refs):
            assert not ref.startswith("#/tables/"), f"table ref leaked into main tree: {ref}"


@pytest.mark.slow
def test_parse_docling_table_analyses_end_to_end(parser) -> None:
    """The PPTX fixture has 20 tables — analyses exist for those with
    non-empty cells, and each analysis's refs resolve against its
    boundary."""
    result = parse_docling(PPTX_FIXTURE, parser=parser)
    assert result.table_analyses, "no table analyses produced"
    boundary_by_id = {b.id: b for b in result.boundaries}
    for analysis in result.table_analyses:
        boundary = boundary_by_id[analysis.id]
        assert boundary.kind == "table"
        assert analysis.edus, f"{analysis.id} has no EDUs"
        for edu in analysis.edus:
            for ref in edu.self_refs:
                assert ref in boundary.self_refs, f"{ref} not in {analysis.id}"


@pytest.mark.slow
def test_parse_docling_boundary_memberships_non_empty(parser) -> None:
    result = parse_docling(PPTX_FIXTURE, parser=parser)
    boundary_ids = {b.id for b in result.boundaries}
    for relation in result.relations:
        assert len(relation.boundary_memberships) > 0
        for bid in relation.boundary_memberships:
            assert bid in boundary_ids


@pytest.mark.slow
def test_parse_docling_relation_refs_in_input_set(parser) -> None:
    """Every relation ref points to a self_ref that exists in the source."""
    doc = DoclingDocument.load_from_json(PPTX_FIXTURE)
    input_refs: set[str] = set()
    input_refs.update(t.self_ref for t in doc.texts)
    input_refs.update(p.self_ref for p in doc.pictures)
    input_refs.update(t.self_ref for t in doc.tables)
    input_refs.update(g.self_ref for g in doc.groups)

    result = parse_docling(PPTX_FIXTURE, parser=parser)
    for relation in result.relations:
        for ref in (*relation.nucleus_refs, *relation.satellite_refs):
            assert ref in input_refs, f"unknown self_ref: {ref}"


@pytest.mark.slow
def test_parse_docling_parser_injection_reuses_instance(parser) -> None:
    """Two calls with the same injected parser return consistent results."""
    a = parse_docling(PPTX_FIXTURE, parser=parser)
    b = parse_docling(PPTX_FIXTURE, parser=parser)
    # Deterministic (verified Phase 0 step 7) → same shape
    assert len(a.relations) == len(b.relations)
    assert len(a.edus) == len(b.edus)
    assert [r.relation for r in a.relations] == [r.relation for r in b.relations]


@pytest.mark.slow
def test_parse_docling_str_and_path_inputs_equivalent(parser) -> None:
    a = parse_docling(PPTX_FIXTURE, parser=parser)
    b = parse_docling(str(PPTX_FIXTURE), parser=parser)
    assert a.source == b.source
    assert len(a.relations) == len(b.relations)


@pytest.mark.slow
def test_parse_docling_vtt_produces_turn_boundaries(parser) -> None:
    result = parse_docling(FIXTURES / "vtt.docling.json", parser=parser)
    turns = [b for b in result.boundaries if b.kind == "turn"]
    assert len(turns) == 1
    assert turns[0].id == "turn-0"


@pytest.mark.slow
def test_parse_docling_pdf_produces_section_boundaries(parser) -> None:
    result = parse_docling(FIXTURES / "pdf.docling.json", parser=parser)
    sections = [b for b in result.boundaries if b.kind == "section"]
    assert len(sections) == 11
