"""Unit + integration tests for ``isanlp_rst.docling.parse_docling``.

Fast unit tests cover the pure helpers (device translation, tool-version
resolution, source-origin serialisation, inventory selection), the
error-path guards that fire before any model load
(``InputTooLargeError``, ``EmptyDoclingError``), and — via a stub
parser — two-level orchestration and the on-disk cache.

Integration tests (``@pytest.mark.slow``) load ``gumrrg`` weights once
and verify end-to-end behaviour on the real fixtures, including the
parser-injection contract.
"""

import json
from dataclasses import dataclass
from pathlib import Path

import pytest
from docling_core.types.doc.document import DoclingDocument
from pydantic import ValidationError

from isanlp_rst.docling import parse_docling
from isanlp_rst.docling._entry import (
    DEFAULT_MAX_HARVEST_CHARS,
    SCHEMA_NAME,
    SCHEMA_VERSION,
    TOOL_NAME,
    _resolve_inventory,
    _resolve_tool_version,
    _serialise_source_origin,
)
from isanlp_rst.docling.errors import EmptyDoclingError, EmptyHarvestError, InputTooLargeError
from isanlp_rst.parser import Parser

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "docling"
PPTX_FIXTURE = FIXTURES / "pptx.docling.json"


# --- Stub parser -------------------------------------------------------------


@dataclass
class _Node:
    """Duck-typed DiscourseUnit stand-in."""

    start: int
    end: int
    left: _Node | None = None
    right: _Node | None = None
    relation: str = ""
    nuclearity: str = ""


class StubParser:
    """Deterministic Parser stand-in — no model load."""

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
            left = _Node(0, cut)
            right = _Node(cut + 2, n)
            root = _Node(0, n, left, right, "elaboration", "NS")
        else:
            root = _Node(0, n)
        return {"rst": [root]}


def _minimal_docling_json(
    *,
    body_children: list | None = None,
    texts: list | None = None,
) -> dict:
    """Minimal DoclingDocument JSON for tmp_path fixtures."""
    return {
        "schema_name": "DoclingDocument",
        "version": "1.10.0",
        "name": "minimal",
        "origin": {
            "mimetype": "text/plain",
            "binary_hash": 1,
            "filename": "minimal.txt",
        },
        "furniture": {
            "self_ref": "#/furniture",
            "children": [],
            "content_layer": "furniture",
            "name": "_root_",
            "label": "unspecified",
        },
        "body": {
            "self_ref": "#/body",
            "children": body_children if body_children is not None else [],
            "content_layer": "body",
            "name": "_root_",
            "label": "unspecified",
        },
        "texts": texts if texts is not None else [],
        "tables": [],
        "pictures": [],
        "groups": [],
        "key_value_items": [],
        "form_items": [],
        "pages": {},
    }


def _write_one_paragraph_docling(path: Path, text: str = "Hello paragraph.") -> Path:
    payload = _minimal_docling_json(
        body_children=[{"$ref": "#/texts/0"}],
        texts=[
            {
                "self_ref": "#/texts/0",
                "parent": {"$ref": "#/body"},
                "children": [],
                "content_layer": "body",
                "label": "text",
                "prov": [],
                "orig": text,
                "text": text,
            }
        ],
    )
    path.write_text(json.dumps(payload))
    return path


def _write_two_para_docling(path: Path) -> Path:
    """Two paragraphs so the stub emits a relation tree."""
    payload = _minimal_docling_json(
        body_children=[{"$ref": "#/texts/0"}, {"$ref": "#/texts/1"}],
        texts=[
            {
                "self_ref": "#/texts/0",
                "parent": {"$ref": "#/body"},
                "children": [],
                "content_layer": "body",
                "label": "text",
                "prov": [],
                "orig": "First paragraph.",
                "text": "First paragraph.",
            },
            {
                "self_ref": "#/texts/1",
                "parent": {"$ref": "#/body"},
                "children": [],
                "content_layer": "body",
                "label": "text",
                "prov": [],
                "orig": "Second paragraph.",
                "text": "Second paragraph.",
            },
        ],
    )
    path.write_text(json.dumps(payload))
    return path


# ===========================================================================
# Fast unit tests — no model load
# ===========================================================================


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
    doc = DoclingDocument.load_from_json(FIXTURES / "markdown.docling.json")
    origin_dict = _serialise_source_origin(doc.origin)
    assert isinstance(origin_dict, dict)
    assert "mimetype" in origin_dict
    assert origin_dict["mimetype"] == "text/markdown"
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
    assert SCHEMA_VERSION == "1.1"
    assert TOOL_NAME == "isanlp_rst"
    assert DEFAULT_MAX_HARVEST_CHARS == 200_000


# --- InputTooLargeError (fires before any model load) ----------------------


def test_input_too_large_error_raised_with_path(tmp_path: Path) -> None:
    path = _write_one_paragraph_docling(tmp_path / "big.docling.json", "x" * 100)
    with pytest.raises(InputTooLargeError) as excinfo:
        parse_docling(path, max_harvest_chars=10, parser=StubParser())  # type: ignore[arg-type]
    assert "exceeds max_harvest_chars=10" in str(excinfo.value)


def test_input_too_large_error_raised_with_str(tmp_path: Path) -> None:
    path = _write_one_paragraph_docling(tmp_path / "big.docling.json", "x" * 100)
    with pytest.raises(InputTooLargeError):
        parse_docling(str(path), max_harvest_chars=10, parser=StubParser())  # type: ignore[arg-type]


def test_input_too_large_error_path_and_str_equivalent(tmp_path: Path) -> None:
    """Path and str inputs reach the same guard."""
    path = _write_one_paragraph_docling(tmp_path / "big.docling.json", "x" * 100)
    with pytest.raises(InputTooLargeError):
        parse_docling(path, max_harvest_chars=10, parser=StubParser())  # type: ignore[arg-type]
    with pytest.raises(InputTooLargeError):
        parse_docling(str(path), max_harvest_chars=10, parser=StubParser())  # type: ignore[arg-type]


# --- Stub-parser orchestration + cache -------------------------------------


def test_stub_parse_shape_and_no_table_refs_in_main(tmp_path: Path) -> None:
    """Hand-written prose-only Docling: empty ``table_analyses``, and main
    relations never reference ``#/tables/``."""
    path = _write_two_para_docling(tmp_path / "two.docling.json")
    result = parse_docling(path, parser=StubParser())  # type: ignore[arg-type]
    assert result.schema_name == SCHEMA_NAME
    assert result.edus or result.relations or result.boundaries
    assert result.table_analyses == ()
    for relation in result.relations:
        for ref in (*relation.nucleus_refs, *relation.satellite_refs):
            assert not ref.startswith("#/tables/"), ref


def test_cache_round_trip_skips_reparse(tmp_path: Path) -> None:
    path = _write_two_para_docling(tmp_path / "doc.docling.json")
    cache = tmp_path / "cache"
    stub = StubParser()
    first = parse_docling(path, parser=stub, cache_dir=cache)  # type: ignore[arg-type]
    calls_after_first = len(stub.calls)
    second = parse_docling(path, parser=stub, cache_dir=cache)  # type: ignore[arg-type]
    assert len(stub.calls) == calls_after_first
    assert first == second


def test_cache_misses_when_hf_model_name_changes(tmp_path: Path) -> None:
    path = _write_two_para_docling(tmp_path / "doc.docling.json")
    cache = tmp_path / "cache"
    stub = StubParser()
    parse_docling(
        path,
        parser=stub,  # type: ignore[arg-type]
        cache_dir=cache,
        hf_model_name="repo/model-a",
    )
    calls_after_first = len(stub.calls)
    parse_docling(
        path,
        parser=stub,  # type: ignore[arg-type]
        cache_dir=cache,
        hf_model_name="repo/model-b",
    )
    assert len(stub.calls) > calls_after_first


def test_cache_misses_when_source_changes(tmp_path: Path) -> None:
    path = _write_two_para_docling(tmp_path / "doc.docling.json")
    cache = tmp_path / "cache"
    stub = StubParser()
    parse_docling(path, parser=stub, cache_dir=cache)  # type: ignore[arg-type]
    # Change bytes in place.
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["name"] = "mutated-doc"
    path.write_text(json.dumps(payload), encoding="utf-8")
    parse_docling(path, parser=stub, cache_dir=cache)  # type: ignore[arg-type]
    assert len(stub.calls) == 2


def test_cache_misses_when_knobs_change(tmp_path: Path) -> None:
    path = _write_two_para_docling(tmp_path / "doc.docling.json")
    cache = tmp_path / "cache"
    stub = StubParser()
    parse_docling(path, parser=stub, cache_dir=cache)  # type: ignore[arg-type]
    calls_after_first = len(stub.calls)
    parse_docling(
        path, parser=stub, cache_dir=cache, include_table_cells=False  # type: ignore[arg-type]
    )
    assert len(stub.calls) > calls_after_first


def test_cache_misses_when_injected_parser_identity_differs(tmp_path: Path) -> None:
    path = _write_two_para_docling(tmp_path / "doc.docling.json")
    cache = tmp_path / "cache"
    stub_a = StubParser()
    parse_docling(path, parser=stub_a, cache_dir=cache)  # type: ignore[arg-type]
    stub_b = StubParser(hf_model_version="rstdt")
    parse_docling(path, parser=stub_b, cache_dir=cache)  # type: ignore[arg-type]
    assert len(stub_b.calls) > 0


def test_cache_misses_when_device_changes(tmp_path: Path) -> None:
    path = _write_two_para_docling(tmp_path / "doc.docling.json")
    cache = tmp_path / "cache"
    stub = StubParser()
    parse_docling(
        path, parser=stub, cache_dir=cache, device="cpu"  # type: ignore[arg-type]
    )
    calls_after_first = len(stub.calls)
    parse_docling(
        path, parser=stub, cache_dir=cache, device="mps"  # type: ignore[arg-type]
    )
    assert len(stub.calls) > calls_after_first


def test_empty_docling_error(tmp_path: Path) -> None:
    path = tmp_path / "empty.docling.json"
    path.write_text(json.dumps(_minimal_docling_json(body_children=[])))
    with pytest.raises(EmptyDoclingError):
        parse_docling(path, parser=StubParser())  # type: ignore[arg-type]


def test_one_paragraph_docling_parses(tmp_path: Path) -> None:
    """Tiny hand-written Docling JSON with one text paragraph."""
    path = _write_one_paragraph_docling(tmp_path / "one.docling.json")
    result = parse_docling(path, parser=StubParser())  # type: ignore[arg-type]
    assert result.edus
    assert result.table_analyses == ()


def test_result_metadata_follows_injected_parser_not_kwargs(
    tmp_path: Path,
) -> None:
    path = _write_one_paragraph_docling(tmp_path / "meta.docling.json")
    stub = StubParser(hf_model_version="rstdt")
    result = parse_docling(
        path,
        parser=stub,  # type: ignore[arg-type]
        hf_model_version="gumrrg",
    )
    assert result.model_version == "rstdt"
    assert result.inventory == "rstdt"


def test_malformed_docling_json_raises(tmp_path: Path) -> None:
    path = tmp_path / "broken.docling.json"
    path.write_text("{not-json")
    with pytest.raises(ValidationError):
        parse_docling(path, parser=StubParser())  # type: ignore[arg-type]


def _write_table_only_docling(path: Path) -> Path:
    """Body contains only a one-cell table — no prose harvest."""
    payload = _minimal_docling_json(
        body_children=[{"$ref": "#/tables/0"}],
        texts=[],
    )
    payload["tables"] = [
        {
            "self_ref": "#/tables/0",
            "parent": {"$ref": "#/body"},
            "children": [],
            "content_layer": "body",
            "label": "table",
            "prov": [],
            "captions": [],
            "references": [],
            "footnotes": [],
            "annotations": [],
            "data": {
                "table_cells": [
                    {
                        "text": "cell",
                        "row_span": 1,
                        "col_span": 1,
                        "start_row_offset_idx": 0,
                        "end_row_offset_idx": 1,
                        "start_col_offset_idx": 0,
                        "end_col_offset_idx": 1,
                        "column_header": False,
                        "row_header": False,
                        "row_section": False,
                    }
                ],
                "num_rows": 1,
                "num_cols": 1,
                "grid": [
                    [
                        {
                            "text": "cell",
                            "row_span": 1,
                            "col_span": 1,
                            "start_row_offset_idx": 0,
                            "end_row_offset_idx": 1,
                            "start_col_offset_idx": 0,
                            "end_col_offset_idx": 1,
                            "column_header": False,
                            "row_header": False,
                            "row_section": False,
                        }
                    ]
                ],
            },
        }
    ]
    path.write_text(json.dumps(payload))
    return path


def test_empty_harvest_error_when_tables_disabled_on_table_only_doc(
    tmp_path: Path,
) -> None:
    """Table-only + ``include_table_cells=False`` → nothing to parse."""
    path = _write_table_only_docling(tmp_path / "table_only.docling.json")
    with pytest.raises(EmptyHarvestError):
        parse_docling(
            path,
            parser=StubParser(),  # type: ignore[arg-type]
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
    boundary_ids = {b.id: b for b in result.boundaries}
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
