"""Unit tests for ``isanlp_rst._rst_common``.

Covers what the format-specific suites can't: the deep-tree recursion
guarantee of the iterative flatten, bisect-vs-linear overlap
equivalence at boundaries, and the cache key/store/load contract.
"""

from dataclasses import dataclass
from pathlib import Path

import pytest

from isanlp_rst._rst_common import (
    SpanIndex,
    flatten_tree,
    load_cached,
    model_identity_knobs,
    resolve_inventory,
    resolve_result_model_meta,
    result_cache_key,
    store_cached,
)


@dataclass
class _Span:
    start: int
    end: int
    ref: str


@dataclass
class _Node:
    start: int
    end: int
    left: _Node | None = None
    right: _Node | None = None
    relation: str = ""
    nuclearity: str = ""


def _ref_of(span: _Span) -> str:
    return span.ref


def _make_relation(**kw: object) -> dict:
    return dict(kw)


def _make_edu(**kw: object) -> dict:
    return dict(kw)


# --- Iterative flatten: deep-tree guarantee ---------------------------------


def test_flatten_survives_tree_deeper_than_recursion_limit() -> None:
    """RST joint-chains produce heavily skewed trees. A 5000-deep
    right-branching chain must flatten without RecursionError — the
    failure mode the iterative traversal exists to prevent."""
    depth = 5000
    spans = tuple(_Span(i * 2, i * 2 + 1, f"#/blocks/{i}") for i in range(depth + 1))
    # Build right-branching chain bottom-up: leaf_i spans [i*2, i*2+1).
    node: _Node = _Node(depth * 2, depth * 2 + 1)
    for i in range(depth - 1, -1, -1):
        leaf = _Node(i * 2, i * 2 + 1)
        node = _Node(i * 2, depth * 2 + 1, leaf, node, "joint", "NN")

    relations, edus = flatten_tree(
        node,
        SpanIndex(spans, ref_of=_ref_of),
        [],
        make_relation=_make_relation,
        make_edu=_make_edu,
    )
    assert len(relations) == depth
    assert len(edus) == depth + 1


def test_flatten_preorder_ids_and_depths() -> None:
    """Root id 0; pre-order assignment; depth increments per level."""
    left = _Node(0, 5)
    right = _Node(7, 12)
    root = _Node(0, 12, left, right, "elaboration", "NS")
    spans = (_Span(0, 5, "a"), _Span(7, 12, "b"))
    relations, edus = flatten_tree(
        root,
        SpanIndex(spans, ref_of=_ref_of),
        [("b-0", frozenset({"a"}))],
        make_relation=_make_relation,
        make_edu=_make_edu,
    )
    (rel,) = relations
    assert rel["id"] == 0
    assert rel["left_id"] == 1 and rel["right_id"] == 2
    assert [e["depth"] for e in edus] == [1, 1]
    assert rel["boundary_memberships"] == ("b-0",)
    assert rel["nucleus_refs"] == ("a",) and rel["satellite_refs"] == ("b",)


# --- SpanIndex: bisect correctness at boundaries -----------------------------


def _linear_overlap(start: int, end: int, spans: tuple[_Span, ...]) -> tuple[str, ...]:
    """Reference implementation: brute-force scan."""
    if start >= end:
        return ()
    out = []
    for s in spans:
        if min(end, s.end) > max(start, s.start):
            out.append(s.ref)
    return tuple(out)


def test_span_index_matches_linear_scan_on_every_subrange() -> None:
    """Exhaustive equivalence over every (start, end) pair on a small
    gapped layout — covers span starts, ends, separators, zero-width."""
    spans = (_Span(0, 4, "s0"), _Span(6, 9, "s1"), _Span(11, 11 + 5, "s2"))
    index = SpanIndex(spans, ref_of=_ref_of)
    limit = 18
    for a in range(limit):
        for b in range(a, limit + 1):
            got, _ = index.overlap(a, b)
            want = _linear_overlap(a, b, spans)
            assert got == want, f"[{a},{b}): {got} != {want}"


def test_span_index_empty_spans() -> None:
    index = SpanIndex((), ref_of=_ref_of)
    assert index.overlap(0, 100) == ((), None)


def test_span_index_note_on_lopsided_overlap() -> None:
    """>= 90% dominance with a minor contributor emits a note."""
    spans = (_Span(0, 100, "big"), _Span(102, 202, "small"))
    index = SpanIndex(spans, ref_of=_ref_of)
    refs, note = index.overlap(10, 110)  # 90 chars of big, 8 of small
    assert refs == ("big", "small")
    assert note is not None and "big" in note


# --- Cache --------------------------------------------------------------------


def test_cache_key_sensitive_to_source_and_knobs() -> None:
    base = result_cache_key(b"abc", {"k": 1})
    assert result_cache_key(b"abd", {"k": 1}) != base
    assert result_cache_key(b"abc", {"k": 2}) != base
    assert result_cache_key(b"abc", {"k": 1}) == base


def test_cache_key_order_insensitive_for_knobs() -> None:
    assert result_cache_key(b"x", {"a": 1, "b": 2}) == result_cache_key(b"x", {"b": 2, "a": 1})


def test_cache_store_load_round_trip(tmp_path: Path) -> None:
    value = {"nested": ["tuple", 1], "n": 2}
    key = result_cache_key(b"src", {"knob": True})
    store_cached(tmp_path / "cache", key, value)
    assert load_cached(tmp_path / "cache", key) == value


def test_cache_load_returns_none_on_miss(tmp_path: Path) -> None:
    assert load_cached(tmp_path, "no-such-key") is None


def test_cache_key_rejects_non_scalar_knob() -> None:
    """Lists (and other non-repr-stable types) must raise, not silently hash."""
    with pytest.raises(TypeError, match="non-repr-stable"):
        result_cache_key(b"src", {"bad": ["a", "b"]})


def test_cache_load_returns_none_on_corrupt_json(tmp_path: Path) -> None:
    key = "deadbeef"
    path = tmp_path / f"{key}.json"
    path.write_text("{not-json", encoding="utf-8")
    assert load_cached(tmp_path, key) is None


def test_cache_ignores_legacy_pickle_files(tmp_path: Path) -> None:
    """Old ``.pkl`` cache files must not be loaded (no pickle execution)."""
    key = "legacy"
    (tmp_path / f"{key}.pkl").write_bytes(b"cos\nsystem\n(S'echo pwned'\ntR.")
    assert load_cached(tmp_path, key) is None


def test_cache_refuses_world_writable_dir(tmp_path: Path) -> None:
    cache = tmp_path / "shared"
    cache.mkdir()
    cache.chmod(0o777)
    with pytest.raises(PermissionError, match="world-writable"):
        store_cached(cache, "k", {"a": 1})


# --- model_identity_knobs ----------------------------------------------------


class _InjectedParser:
    def __init__(
        self,
        hf_model_name: str | None = None,
        hf_model_version: str | None = None,
        relinventory: str | None = None,
    ) -> None:
        self.hf_model_name = hf_model_name
        self.hf_model_version = hf_model_version
        self.relinventory = relinventory


def test_model_identity_knobs_construct_vs_injected_vs_stub() -> None:
    construct = model_identity_knobs(
        hf_model_name="repo/a",
        hf_model_version="gumrrg",
        relinventory=None,
        parser=None,
    )
    assert construct["parser_source"] == "construct"
    assert construct["hf_model_name"] == "repo/a"
    assert "parser_id" not in construct

    injected_parser = _InjectedParser(
        hf_model_name="repo/b",
        hf_model_version="rstdt",
        relinventory="eng.erst.gum",
    )
    injected = model_identity_knobs(
        hf_model_name="ignored",
        hf_model_version="ignored",
        relinventory="ignored",
        parser=injected_parser,
    )
    assert injected["parser_source"] == "injected"
    assert injected["hf_model_name"] == "repo/b"
    assert injected["hf_model_version"] == "rstdt"
    assert injected["relinventory"] == "eng.erst.gum"
    assert injected["parser_id"] == id(injected_parser)

    stub = object()
    stub_knobs = model_identity_knobs(
        hf_model_name="repo/c",
        hf_model_version="gumrrg",
        relinventory=None,
        parser=stub,
    )
    assert stub_knobs["parser_source"] == "injected"
    assert stub_knobs["hf_model_name"] == "repo/c"
    assert stub_knobs["parser_id"] == id(stub)


def test_model_identity_knobs_different_stubs_differ() -> None:
    a, b = object(), object()
    ka = model_identity_knobs(hf_model_name="r", hf_model_version="gumrrg", relinventory=None, parser=a)
    kb = model_identity_knobs(hf_model_name="r", hf_model_version="gumrrg", relinventory=None, parser=b)
    assert ka["parser_id"] != kb["parser_id"]
    assert ka != kb


def test_model_identity_knobs_same_stub_stable() -> None:
    stub = object()
    ka = model_identity_knobs(hf_model_name="r", hf_model_version="gumrrg", relinventory=None, parser=stub)
    kb = model_identity_knobs(hf_model_name="r", hf_model_version="gumrrg", relinventory=None, parser=stub)
    assert ka == kb
    assert ka["parser_id"] == id(stub)


def test_resolve_result_model_meta_prefers_injected_parser_over_kwargs() -> None:
    """Metadata must not silently report kwargs when the injected parser differs."""
    parser = _InjectedParser(
        hf_model_name="repo/x",
        hf_model_version="rstdt",
        relinventory=None,
    )
    version, inventory = resolve_result_model_meta(
        parser,
        hf_model_version="gumrrg",  # disagrees on purpose
        relinventory="should_be_ignored_when_parser_has_none_then_fallback",
        resolve_inventory=resolve_inventory,
    )
    # version from parser; inventory falls back to kwargs relinventory then version
    assert version == "rstdt"
    assert inventory == "should_be_ignored_when_parser_has_none_then_fallback"


def test_resolve_result_model_meta_injected_relinventory_wins() -> None:
    parser = _InjectedParser(
        hf_model_version="unirst",
        relinventory="eng.erst.gum",
    )
    version, inventory = resolve_result_model_meta(
        parser,
        hf_model_version="gumrrg",
        relinventory="eng.rst.rstdt",
        resolve_inventory=resolve_inventory,
    )
    assert version == "unirst"
    assert inventory == "eng.erst.gum"
