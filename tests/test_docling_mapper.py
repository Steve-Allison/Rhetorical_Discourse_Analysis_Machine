"""Unit tests for ``isanlp_rst.docling.mapper``.

The mapper is two pure functions — ``compute_overlap_refs`` and
``flatten_tree``. Tests use synthetic ``HarvestSpan``/``Boundary``
tuples and a tiny tree builder so no model load is required.
"""

from __future__ import annotations

from dataclasses import dataclass

from isanlp_rst.docling.mapper import (
    NOTE_THRESHOLD,
    compute_overlap_refs,
    flatten_tree,
)
from isanlp_rst.docling.schema import Boundary, HarvestSpan


# --- Synthetic tree node ---------------------------------------------------


@dataclass
class FakeUnit:
    """Stand-in for ``DiscourseUnit`` — same duck-typed attributes."""

    start: int
    end: int
    left: "FakeUnit | None" = None
    right: "FakeUnit | None" = None
    relation: str = ""
    nuclearity: str = ""


def leaf(start: int, end: int) -> FakeUnit:
    return FakeUnit(start=start, end=end)


def node(
    left: FakeUnit, right: FakeUnit, relation: str = "elaboration", nuclearity: str = "NS"
) -> FakeUnit:
    return FakeUnit(
        start=left.start,
        end=right.end,
        left=left,
        right=right,
        relation=relation,
        nuclearity=nuclearity,
    )


# ===========================================================================
# compute_overlap_refs
# ===========================================================================


# --- Exact / single-span overlap -------------------------------------------


def test_exact_match_single_ref_no_note() -> None:
    spans = (HarvestSpan("#/texts/0", "hello", 0, 5),)
    refs, note = compute_overlap_refs(0, 5, spans)
    assert refs == ("#/texts/0",)
    assert note is None


def test_subrange_single_ref_no_note() -> None:
    spans = (HarvestSpan("#/texts/0", "hello world", 0, 11),)
    refs, note = compute_overlap_refs(2, 8, spans)
    assert refs == ("#/texts/0",)
    assert note is None


# --- Multi-span overlap ----------------------------------------------------


def test_50_50_split_both_refs_no_note() -> None:
    spans = (
        HarvestSpan("#/texts/0", "x" * 5, 0, 5),
        HarvestSpan("#/texts/1", "y" * 5, 5, 10),
    )
    refs, note = compute_overlap_refs(2, 8, spans)
    assert refs == ("#/texts/0", "#/texts/1")
    assert note is None


def test_three_span_coverage_no_note() -> None:
    spans = (
        HarvestSpan("#/texts/0", "a" * 30, 0, 30),
        HarvestSpan("#/texts/1", "b" * 40, 30, 70),
        HarvestSpan("#/texts/2", "c" * 30, 70, 100),
    )
    refs, note = compute_overlap_refs(0, 100, spans)
    assert refs == ("#/texts/0", "#/texts/1", "#/texts/2")
    assert note is None


# --- Note threshold edges --------------------------------------------------


def test_89_percent_no_note() -> None:
    spans = (
        HarvestSpan("#/texts/0", "x" * 100, 0, 100),
        HarvestSpan("#/texts/1", "y" * 100, 100, 200),
    )
    # 89 from #/texts/0, 11 from #/texts/1 → dominant ratio = 89/100 = 0.89
    refs, note = compute_overlap_refs(11, 111, spans)
    assert refs == ("#/texts/0", "#/texts/1")
    assert note is None


def test_90_percent_emits_note() -> None:
    spans = (
        HarvestSpan("#/texts/0", "x" * 100, 0, 100),
        HarvestSpan("#/texts/1", "y" * 100, 100, 200),
    )
    # 90 from #/texts/0, 10 from #/texts/1 → ratio = 90/100 = 0.90 (==threshold)
    refs, note = compute_overlap_refs(10, 110, spans)
    assert refs == ("#/texts/0", "#/texts/1")
    assert note is not None
    assert "#/texts/0" in note
    assert "#/texts/1" in note


def test_92_8_lopsided_emits_note() -> None:
    spans = (
        HarvestSpan("#/texts/0", "x" * 100, 0, 100),
        HarvestSpan("#/texts/1", "y" * 100, 100, 200),
    )
    refs, note = compute_overlap_refs(0, 108, spans)
    assert refs == ("#/texts/0", "#/texts/1")
    assert note is not None


# --- Edges -----------------------------------------------------------------


def test_zero_width_range_returns_empty() -> None:
    spans = (HarvestSpan("#/texts/0", "x", 0, 1),)
    refs, note = compute_overlap_refs(5, 5, spans)
    assert refs == ()
    assert note is None


def test_negative_range_returns_empty() -> None:
    spans = (HarvestSpan("#/texts/0", "x", 0, 1),)
    refs, note = compute_overlap_refs(7, 3, spans)
    assert refs == ()
    assert note is None


def test_no_overlap_returns_empty() -> None:
    spans = (HarvestSpan("#/texts/0", "x", 0, 5),)
    refs, note = compute_overlap_refs(10, 20, spans)
    assert refs == ()
    assert note is None


def test_range_at_offset_zero() -> None:
    spans = (HarvestSpan("#/texts/0", "hello", 0, 5),)
    refs, note = compute_overlap_refs(0, 1, spans)
    assert refs == ("#/texts/0",)
    assert note is None


def test_range_at_end_of_document() -> None:
    spans = (HarvestSpan("#/texts/0", "hello", 0, 5),)
    refs, note = compute_overlap_refs(4, 5, spans)
    assert refs == ("#/texts/0",)
    assert note is None


def test_threshold_constant_is_0_90() -> None:
    assert NOTE_THRESHOLD == 0.90


# ===========================================================================
# flatten_tree
# ===========================================================================


def test_single_leaf_one_edu_zero_relations() -> None:
    spans = (HarvestSpan("#/texts/0", "hello", 0, 5),)
    relations, edus = flatten_tree(leaf(0, 5), spans, ())
    assert relations == ()
    assert len(edus) == 1
    assert edus[0].id == 0
    assert edus[0].self_refs == ("#/texts/0",)
    assert edus[0].depth == 0


def test_single_relation_two_leaves() -> None:
    """tree: NS(leaf[0..5], leaf[7..12]) → 1 relation + 2 edus."""
    spans = (
        HarvestSpan("#/texts/0", "hello", 0, 5),
        HarvestSpan("#/texts/1", "world", 7, 12),
    )
    tree = node(leaf(0, 5), leaf(7, 12), relation="elaboration", nuclearity="NS")
    relations, edus = flatten_tree(tree, spans, ())
    assert len(relations) == 1
    assert len(edus) == 2

    rel = relations[0]
    assert rel.id == 0
    assert rel.relation == "elaboration"
    assert rel.nuclearity == "NS"
    assert rel.nucleus_refs == ("#/texts/0",)
    assert rel.satellite_refs == ("#/texts/1",)
    assert rel.depth == 0
    assert rel.left_id == 1
    assert rel.right_id == 2
    assert rel.boundary_memberships == ()
    assert rel.note is None

    assert [e.id for e in edus] == [1, 2]
    assert edus[0].depth == 1
    assert edus[1].depth == 1


def test_nuclearity_sn_swaps_nucleus_satellite() -> None:
    spans = (
        HarvestSpan("#/texts/0", "x", 0, 1),
        HarvestSpan("#/texts/1", "y", 2, 3),
    )
    tree = node(leaf(0, 1), leaf(2, 3), nuclearity="SN")
    relations, _ = flatten_tree(tree, spans, ())
    assert relations[0].nucleus_refs == ("#/texts/1",)
    assert relations[0].satellite_refs == ("#/texts/0",)


def test_nuclearity_nn_puts_all_in_nucleus() -> None:
    spans = (
        HarvestSpan("#/texts/0", "x", 0, 1),
        HarvestSpan("#/texts/1", "y", 2, 3),
    )
    tree = node(leaf(0, 1), leaf(2, 3), nuclearity="NN")
    relations, _ = flatten_tree(tree, spans, ())
    assert relations[0].nucleus_refs == ("#/texts/0", "#/texts/1")
    assert relations[0].satellite_refs == ()


def test_ids_are_preorder_and_shared() -> None:
    """3-level tree: ids visit root, left.left, left.right, right.left, right.right."""
    spans = tuple(HarvestSpan(f"#/texts/{i}", "x", i * 2, i * 2 + 1) for i in range(4))
    tree = node(
        node(leaf(0, 1), leaf(2, 3)),
        node(leaf(4, 5), leaf(6, 7)),
    )
    relations, edus = flatten_tree(tree, spans, ())
    # Pre-order over all 7 nodes:
    #   id=0 root, id=1 left-internal, id=2 leaf 0..1, id=3 leaf 2..3,
    #   id=4 right-internal, id=5 leaf 4..5, id=6 leaf 6..7
    assert [r.id for r in relations] == [0, 1, 4]
    assert [e.id for e in edus] == [2, 3, 5, 6]
    # Verify left_id / right_id resolve into the union of relations + edus
    all_ids = {r.id for r in relations} | {e.id for e in edus}
    for r in relations:
        assert r.left_id in all_ids
        assert r.right_id in all_ids


def test_boundary_memberships_intersection() -> None:
    spans = (
        HarvestSpan("#/texts/0", "x", 0, 1),
        HarvestSpan("#/texts/1", "y", 2, 3),
        HarvestSpan("#/texts/2", "z", 4, 5),
    )
    boundaries = (
        Boundary(id="slide-0", kind="slide", label=None, parent_self_ref=None, self_refs=("#/texts/0", "#/texts/1")),
        Boundary(id="slide-1", kind="slide", label=None, parent_self_ref=None, self_refs=("#/texts/2",)),
    )
    # Relation spanning all three texts touches both slides.
    tree = node(
        node(leaf(0, 1), leaf(2, 3)),  # in slide-0 only
        leaf(4, 5),                    # in slide-1 only
    )
    relations, _ = flatten_tree(tree, spans, boundaries)
    # Root relation covers 0..5 → touches both slides
    assert set(relations[0].boundary_memberships) == {"slide-0", "slide-1"}
    # Left-internal relation covers 0..3 → slide-0 only
    assert relations[1].boundary_memberships == ("slide-0",)


def test_lopsided_note_appears_on_relation() -> None:
    spans = (
        HarvestSpan("#/texts/0", "x" * 100, 0, 100),
        HarvestSpan("#/texts/1", "y" * 100, 100, 200),
    )
    # Relation node spans 0..108: 100 chars from texts/0, 8 from texts/1 → lopsided.
    tree = node(leaf(0, 100), leaf(100, 108))
    relations, _ = flatten_tree(tree, spans, ())
    assert relations[0].note is not None


def test_edu_order_matches_reading_order() -> None:
    """For binary trees with left-precedes-right text ordering, edus[] in
    pre-order is the same as ascending-start (reading) order."""
    spans = tuple(HarvestSpan(f"#/texts/{i}", "x", i * 2, i * 2 + 1) for i in range(4))
    tree = node(
        node(leaf(0, 1), leaf(2, 3)),
        node(leaf(4, 5), leaf(6, 7)),
    )
    _, edus = flatten_tree(tree, spans, ())
    starts = [e.self_refs for e in edus]
    assert starts == [("#/texts/0",), ("#/texts/1",), ("#/texts/2",), ("#/texts/3",)]


def test_relations_in_preorder() -> None:
    """Pre-order DFS: root, left-subtree, right-subtree."""
    spans = tuple(HarvestSpan(f"#/texts/{i}", "x", i * 2, i * 2 + 1) for i in range(4))
    tree = node(
        node(leaf(0, 1), leaf(2, 3), relation="left-internal"),
        node(leaf(4, 5), leaf(6, 7), relation="right-internal"),
        relation="root",
    )
    relations, _ = flatten_tree(tree, spans, ())
    assert [r.relation for r in relations] == ["root", "left-internal", "right-internal"]


def test_short_input_dummy_tree_single_edu() -> None:
    """Parser short-input fallback returns a single-leaf tree."""
    spans = (HarvestSpan("#/texts/0", "hi", 0, 2),)
    relations, edus = flatten_tree(leaf(0, 2), spans, ())
    assert relations == ()
    assert len(edus) == 1


def test_relation_depth_increments() -> None:
    spans = tuple(HarvestSpan(f"#/texts/{i}", "x", i * 2, i * 2 + 1) for i in range(4))
    tree = node(
        node(leaf(0, 1), leaf(2, 3)),
        leaf(4, 5),
    )
    relations, edus = flatten_tree(tree, spans, ())
    # Root at depth 0, left-internal at depth 1.
    assert relations[0].depth == 0
    assert relations[1].depth == 1
    # Leaves: 2 at depth 2, 1 at depth 1.
    assert sorted(e.depth for e in edus) == [1, 2, 2]


def test_unrecognised_nuclearity_treated_as_NN() -> None:
    spans = (
        HarvestSpan("#/texts/0", "x", 0, 1),
        HarvestSpan("#/texts/1", "y", 2, 3),
    )
    tree = node(leaf(0, 1), leaf(2, 3), nuclearity="WAT")
    relations, _ = flatten_tree(tree, spans, ())
    assert relations[0].nucleus_refs == ("#/texts/0", "#/texts/1")
    assert relations[0].satellite_refs == ()
