"""Unit tests for ``rdam.rst.doclang.loader``.

The local-name canonical XPath is load-bearing — every other module
addresses elements through it. Tests focus on:

- namespace transparency (identical paths regardless of ``xmlns``)
- uniqueness within a document
- round-trip resolvability against ``lxml.etree``'s structural model
- behaviour on pathological inputs (empty docs, mixed siblings)
"""

from pathlib import Path

import pytest
from lxml import etree

from rdam.rst.doclang.loader import local_name, local_path

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "doclang"


def _parse_fixture(name: str) -> etree._ElementTree:
    return etree.parse(FIXTURES / name)


def _resolve_local_path(tree: etree._ElementTree, path: str) -> etree._Element | None:
    """Reverse the ``local_path`` walker — used for round-trip checks."""
    root = tree.getroot()
    parts = [p for p in path.split("/") if p]
    head = parts[0].split("[", 1)[0]
    if local_name(root) != head:
        return None
    cur: etree._Element = root
    for step in parts[1:]:
        tag_, _, idx_ = step.partition("[")
        pos = int(idx_.rstrip("]"))
        same = [c for c in cur if isinstance(c.tag, str) and local_name(c) == tag_]
        if pos < 1 or pos > len(same):
            return None
        cur = same[pos - 1]
    return cur


# --- Namespace transparency -------------------------------------------------


def test_paths_are_namespace_agnostic_between_two_fixtures() -> None:
    """Two semantically-identical fixtures with and without ``xmlns`` must
    produce identical path roots."""
    ns_tree = _parse_fixture("ok_comprehensive.dclg")
    no_ns_tree = _parse_fixture("ok_no_namespace.dclg")
    assert local_path(ns_tree.getroot()) == "/doclang[1]"
    assert local_path(no_ns_tree.getroot()) == "/doclang[1]"


def test_namespaced_doc_path_never_contains_wildcard() -> None:
    """Regression: lxml's ``getpath()`` emits ``/*/*[N]`` on namespaced
    docs. Our walker must not."""
    tree = _parse_fixture("ok_comprehensive.dclg")
    for el in tree.iter():
        if not isinstance(el.tag, str):
            continue
        path = local_path(el)
        assert "/*" not in path, f"wildcard leaked into path: {path}"


# --- Uniqueness / round-trip ------------------------------------------------


@pytest.mark.parametrize(
    "fixture_name",
    [
        "ok_comprehensive.dclg",
        "ok_no_namespace.dclg",
        "doclang_example.dclg",
        "ok_list_with_unwrapped_text.dclg",
        "ok_thread.dclg",
    ],
)
def test_local_path_is_unique_within_document(fixture_name: str) -> None:
    tree = _parse_fixture(fixture_name)
    paths = [local_path(el) for el in tree.iter() if isinstance(el.tag, str)]
    assert len(paths) == len(set(paths)), f"duplicate paths in {fixture_name}"


@pytest.mark.parametrize(
    "fixture_name",
    [
        "ok_comprehensive.dclg",
        "ok_no_namespace.dclg",
        "ok_list_with_unwrapped_text.dclg",
    ],
)
def test_local_path_round_trips_via_index(fixture_name: str) -> None:
    """Every emitted path resolves back to its own element."""
    tree = _parse_fixture(fixture_name)
    for el in tree.iter():
        if not isinstance(el.tag, str):
            continue
        path = local_path(el)
        found = _resolve_local_path(tree, path)
        assert found is el, f"path {path} did not round-trip"


# --- Sibling position indexing ----------------------------------------------


def test_sibling_positions_are_per_local_name() -> None:
    """In ``<x><a/><b/><a/></x>``, the second ``<a/>`` is ``[2]`` even
    though it's the third child overall."""
    xml = b"<doclang><a/><b/><a/></doclang>"
    tree = etree.ElementTree(etree.fromstring(xml))
    second_a = tree.getroot()[2]
    assert local_path(second_a) == "/doclang[1]/a[2]"


def test_first_sibling_is_index_1_not_omitted() -> None:
    """We always emit ``[1]`` for first-and-only siblings. lxml's
    ``getpath()`` omits it; we don't, for stability."""
    xml = b"<doclang><solo/></doclang>"
    tree = etree.ElementTree(etree.fromstring(xml))
    solo = tree.getroot()[0]
    assert local_path(solo) == "/doclang[1]/solo[1]"


# --- local_name -------------------------------------------------------------


def test_local_name_strips_default_namespace() -> None:
    xml = b'<doclang xmlns="https://www.doclang.ai/ns/v0"><text>hi</text></doclang>'
    tree = etree.ElementTree(etree.fromstring(xml))
    root = tree.getroot()
    child = root[0]
    assert local_name(root) == "doclang"
    assert local_name(child) == "text"


def test_local_name_no_namespace_unchanged() -> None:
    xml = b"<doclang><text>hi</text></doclang>"
    tree = etree.ElementTree(etree.fromstring(xml))
    assert local_name(tree.getroot()[0]) == "text"


def test_non_element_nodes_have_no_local_name_or_address() -> None:
    root = etree.fromstring(b"<doclang><!-- comment --><text>hi</text></doclang>")
    comment = root[0]
    assert local_name(comment) == ""
    assert local_path(comment) == ""
