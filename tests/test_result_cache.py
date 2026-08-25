"""Result-cache identity and persisted provenance regressions."""

from dataclasses import dataclass
import json
from pathlib import Path
import re
import unicodedata

import pytest

from isanlp_rst._rst_common import result_cache_key
from isanlp_rst.doclang import parse_doclang
from isanlp_rst.docling import parse_docling
from isanlp_rst.markdown import parse_markdown

FIXTURES = Path(__file__).resolve().parent / "fixtures"


@dataclass
class _Node:
    start: int
    end: int
    left: _Node | None = None
    right: _Node | None = None
    relation: str = ""
    nuclearity: str = ""


class _StubParser:
    hf_model_name = "test/cache-model"
    hf_model_version = "cache-revision"
    relinventory = "cache-inventory"

    def __init__(self) -> None:
        self.calls = 0

    def __call__(self, text: str) -> dict[str, list[_Node]]:
        self.calls += 1
        return {"rst": [_Node(0, len(text))]}


def test_equal_bytes_under_different_basenames_do_not_share_identity() -> None:
    first = result_cache_key(b"same", {"schema_version": "1.1"}, source_basename="first.md")
    second = result_cache_key(b"same", {"schema_version": "1.1"}, source_basename="second.md")
    assert first != second


def test_cache_identity_uses_basename_not_parent_directory() -> None:
    first = result_cache_key(b"same", {"schema_version": "1.1"}, source_basename="one/sample.md")
    second = result_cache_key(b"same", {"schema_version": "1.1"}, source_basename="two/sample.md")
    assert first == second


def test_cache_identity_normalizes_unicode_basename() -> None:
    composed = "résumé.md"
    decomposed = unicodedata.normalize("NFD", composed)
    assert composed != decomposed
    first = result_cache_key(b"same", {"schema_version": "1.1"}, source_basename=composed)
    second = result_cache_key(b"same", {"schema_version": "1.1"}, source_basename=decomposed)
    assert first == second


def test_schema_version_bump_forces_cache_miss() -> None:
    old = result_cache_key(b"same", {"schema_version": "1.0"}, source_basename="sample.md")
    current = result_cache_key(b"same", {"schema_version": "1.1"}, source_basename="sample.md")
    assert old != current


def test_behavior_option_change_forces_cache_miss() -> None:
    included = result_cache_key(
        b"same",
        {"schema_version": "1.1", "include_code_blocks": True},
        source_basename="sample.md",
    )
    excluded = result_cache_key(
        b"same",
        {"schema_version": "1.1", "include_code_blocks": False},
        source_basename="sample.md",
    )
    assert included != excluded


@pytest.mark.parametrize("basename", ["", ".", ".."])
def test_invalid_source_basename_fails_closed(basename: str) -> None:
    with pytest.raises(ValueError, match="source_basename"):
        result_cache_key(b"same", {"schema_version": "1.1"}, source_basename=basename)


@pytest.mark.parametrize(
    ("format_name", "source", "schema_name", "schema_version"),
    [
        ("docling", FIXTURES / "docling" / "markdown.docling.json", "isanlp_rst_docling", "1.2"),
        ("doclang", FIXTURES / "doclang" / "ok_namespaced_and_versioned.dclg", "isanlp_rst_doclang", "1.1"),
        ("markdown", FIXTURES / "markdown" / "minimal.md", "isanlp_rst_markdown", "1.1"),
    ],
)
def test_persisted_cache_contains_truthful_provenance(
    tmp_path: Path,
    format_name: str,
    source: Path,
    schema_name: str,
    schema_version: str,
) -> None:
    cache_dir = tmp_path / format_name
    parser = _StubParser()
    if format_name == "docling":
        first = parse_docling(source, parser=parser, cache_dir=cache_dir)
    elif format_name == "doclang":
        first = parse_doclang(source, parser=parser, validate_xml=False, cache_dir=cache_dir)
    else:
        first = parse_markdown(source, parser=parser, cache_dir=cache_dir)
    calls_after_first_parse = parser.calls

    if format_name == "docling":
        second = parse_docling(source, parser=parser, cache_dir=cache_dir)
    elif format_name == "doclang":
        second = parse_doclang(source, parser=parser, validate_xml=False, cache_dir=cache_dir)
    else:
        second = parse_markdown(source, parser=parser, cache_dir=cache_dir)

    assert second == first
    assert calls_after_first_parse >= 1
    assert parser.calls == calls_after_first_parse
    cache_files = tuple(cache_dir.glob("*.json"))
    assert len(cache_files) == 1
    envelope = json.loads(cache_files[0].read_text(encoding="utf-8"))
    assert envelope["v"] == 1
    payload = envelope["payload"]
    assert payload["source"] == source.name
    assert payload["schema_name"] == schema_name
    assert payload["schema_version"] == schema_version
    assert payload["tool_version"] == "4.0.0"
    assert re.fullmatch(r"[0-9a-f]{40}(?:-dirty)?", payload["source_revision"])
    assert payload["model_version"] == "cache-revision"
    assert payload["inventory"] == "cache-inventory"
