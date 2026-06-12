"""Unit tests for ``isanlp_rst._rst_common``.

Covers what the format-specific suites can't: the deep-tree recursion
guarantee of the iterative flatten, bisect-vs-linear overlap
equivalence at boundaries, and the cache key/store/load contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from isanlp_rst._rst_common import (
    SpanIndex,
    flatten_tree,
    load_cached,
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
    left: "_Node | None" = None
    right: "_Node | None" = None
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
    assert result_cache_key(b"x", {"a": 1, "b": 2}) == result_cache_key(
        b"x", {"b": 2, "a": 1}
    )


def test_cache_store_load_round_trip(tmp_path: Path) -> None:
    value = {"nested": ("tuple", 1), "n": 2}
    key = result_cache_key(b"src", {"knob": True})
    store_cached(tmp_path / "cache", key, value)
    assert load_cached(tmp_path / "cache", key) == value


def test_cache_load_returns_none_on_miss(tmp_path: Path) -> None:
    assert load_cached(tmp_path, "no-such-key") is None
