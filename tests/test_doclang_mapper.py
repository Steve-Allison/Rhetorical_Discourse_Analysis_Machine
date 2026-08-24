"""Unit tests for ``isanlp_rst.doclang.mapper``.

Two pure functions — ``compute_overlap_refs`` and ``flatten_tree``.
Tests use synthetic ``HarvestSpan`` / ``Boundary`` tuples and a tiny
duck-typed tree builder so no model load is required. The overlap maths
itself is shared with the Docling mapper (covered by
``test_docling_mapper.py``); these tests focus on DocLang-specific
behaviour: xpath addressing and per-node thread_id resolution.
"""

from dataclasses import dataclass

from isanlp_rst.doclang.mapper import (
    NOTE_THRESHOLD,
    compute_overlap_refs,
    flatten_tree as _flatten_tree,
)
from isanlp_rst.doclang.schema import Boundary, HarvestSpan, RstEdu, RstRelation


# --- Synthetic tree node ---------------------------------------------------


@dataclass
class FakeUnit:
    """Stand-in for ``DiscourseUnit`` — duck-typed attributes."""

    start: int
    end: int
    left: FakeUnit | None = None
    right: FakeUnit | None = None
    relation: str = ""
    nuclearity: str = ""


def leaf(start: int, end: int) -> FakeUnit:
    return FakeUnit(start=start, end=end)


def node(left: FakeUnit, right: FakeUnit, relation: str = "elaboration", nuclearity: str = "NS") -> FakeUnit:
    return FakeUnit(
        start=left.start,
        end=right.end,
        left=left,
        right=right,
        relation=relation,
        nuclearity=nuclearity,
    )


def _span(xpath: str, start: int, end: int, thread_id: int | None = None) -> HarvestSpan:
    return HarvestSpan(
        xpath=xpath,
        thread_id=thread_id,
        layer="body",
        text="x" * (end - start),
        start=start,
        end=end,
    )


def _materialize_source(spans: tuple[HarvestSpan, ...]) -> str:
    chars = [" "] * max((span.end for span in spans), default=0)
    for span in spans:
        assert len(span.text) == span.end - span.start
        chars[span.start : span.end] = span.text
    return "".join(chars)


def flatten_tree(
    tree: FakeUnit,
    spans: tuple[HarvestSpan, ...],
    boundaries: tuple[Boundary, ...],
) -> tuple[tuple[RstRelation, ...], tuple[RstEdu, ...]]:
    return _flatten_tree(tree, spans, boundaries, source_text=_materialize_source(spans))


# ===========================================================================
# compute_overlap_refs — xpath wrapper over the shared maths
# ===========================================================================


def test_overlap_returns_xpath_not_self_ref() -> None:
    """The DocLang mapper returns xpaths, not Docling-style self_refs."""
    spans = (_span("/doclang[1]/text[1]", 0, 5),)
    refs, _ = compute_overlap_refs(0, 5, spans)
    assert refs == ("/doclang[1]/text[1]",)
    assert all(r.startswith("/doclang[") for r in refs)


def test_overlap_lopsided_note_uses_xpath() -> None:
    """Lopsided notes carry xpath strings, not self_refs."""
    spans = (
        _span("/doclang[1]/text[1]", 0, 100),
        _span("/doclang[1]/text[2]", 100, 200),
    )
    refs, note = compute_overlap_refs(10, 110, spans)
    assert note is not None
    assert "/doclang[1]/text[1]" in note
    assert "/doclang[1]/text[2]" in note
    assert "#/texts/" not in note


def test_threshold_constant_is_0_90() -> None:
    assert NOTE_THRESHOLD == 0.90


# ===========================================================================
# flatten_tree — DocLang relation / edu construction
# ===========================================================================


def test_single_leaf_emits_one_edu() -> None:
    spans = (_span("/doclang[1]/text[1]", 0, 5),)
    relations, edus = flatten_tree(leaf(0, 5), spans, ())
    assert relations == ()
    assert len(edus) == 1
    assert edus[0].xpaths == ("/doclang[1]/text[1]",)
    assert edus[0].thread_ids == ()


def test_relation_carries_xpaths_per_nuclearity() -> None:
    spans = (
        _span("/doclang[1]/text[1]", 0, 5),
        _span("/doclang[1]/text[2]", 7, 12),
    )
    tree = node(leaf(0, 5), leaf(7, 12), nuclearity="SN")
    relations, _ = flatten_tree(tree, spans, ())
    rel = relations[0]
    assert rel.nucleus_xpaths == ("/doclang[1]/text[2]",)
    assert rel.satellite_xpaths == ("/doclang[1]/text[1]",)


def test_thread_id_deduplicated_into_relation() -> None:
    """Two text spans share ``thread_id=1`` — the relation must list it
    once, not twice."""
    spans = (
        _span("/doclang[1]/text[1]", 0, 5, thread_id=1),
        _span("/doclang[1]/text[2]", 7, 12, thread_id=1),
    )
    tree = node(leaf(0, 5), leaf(7, 12), nuclearity="NN")
    relations, _ = flatten_tree(tree, spans, ())
    assert relations[0].nucleus_thread_ids == (1,)
    assert relations[0].satellite_thread_ids == ()


def test_no_thread_id_means_empty_tuple() -> None:
    spans = (
        _span("/doclang[1]/text[1]", 0, 5),
        _span("/doclang[1]/text[2]", 7, 12),
    )
    tree = node(leaf(0, 5), leaf(7, 12))
    relations, edus = flatten_tree(tree, spans, ())
    assert relations[0].nucleus_thread_ids == ()
    assert relations[0].satellite_thread_ids == ()
    assert all(e.thread_ids == () for e in edus)


def test_thread_ids_split_by_nuclearity() -> None:
    """Left thread-1 + right thread-2 + NS → nucleus has thread 1,
    satellite has thread 2."""
    spans = (
        _span("/doclang[1]/text[1]", 0, 5, thread_id=1),
        _span("/doclang[1]/text[2]", 7, 12, thread_id=2),
    )
    tree = node(leaf(0, 5), leaf(7, 12), nuclearity="NS")
    relations, _ = flatten_tree(tree, spans, ())
    assert relations[0].nucleus_thread_ids == (1,)
    assert relations[0].satellite_thread_ids == (2,)


def test_thread_id_propagates_to_leaf_edus() -> None:
    spans = (_span("/doclang[1]/text[1]", 0, 5, thread_id=7),)
    relations, edus = flatten_tree(leaf(0, 5), spans, ())
    assert edus[0].thread_ids == (7,)


# --- Boundary memberships --------------------------------------------------


def test_boundary_membership_via_xpath_intersection() -> None:
    spans = (
        _span("/doclang[1]/text[1]", 0, 5),
        _span("/doclang[1]/text[2]", 7, 12),
        _span("/doclang[1]/text[3]", 14, 19),
    )
    boundaries = (
        Boundary(
            id="heading-0",
            kind="heading",
            label=None,
            parent_xpath=None,
            xpaths=("/doclang[1]/text[1]", "/doclang[1]/text[2]"),
        ),
        Boundary(
            id="heading-1",
            kind="heading",
            label=None,
            parent_xpath=None,
            xpaths=("/doclang[1]/text[3]",),
        ),
    )
    tree = node(node(leaf(0, 5), leaf(7, 12)), leaf(14, 19))
    relations, _ = flatten_tree(tree, spans, boundaries)
    assert set(relations[0].boundary_memberships) == {"heading-0", "heading-1"}
    assert relations[1].boundary_memberships == ("heading-0",)


# --- Pre-order id assignment (shared with Docling — DocLang regression) ----


def test_ids_preorder_relations_and_edus_share_namespace() -> None:
    spans = tuple(_span(f"/doclang[1]/text[{i + 1}]", i * 2, i * 2 + 1) for i in range(4))
    tree = node(
        node(leaf(0, 1), leaf(2, 3)),
        node(leaf(4, 5), leaf(6, 7)),
    )
    relations, edus = flatten_tree(tree, spans, ())
    assert [r.id for r in relations] == [0, 1, 4]
    assert [e.id for e in edus] == [2, 3, 5, 6]
    all_ids = {r.id for r in relations} | {e.id for e in edus}
    for r in relations:
        assert r.left_id in all_ids
        assert r.right_id in all_ids


def test_relations_in_preorder_relation_label() -> None:
    spans = tuple(_span(f"/doclang[1]/text[{i + 1}]", i * 2, i * 2 + 1) for i in range(4))
    tree = node(
        node(leaf(0, 1), leaf(2, 3), relation="left-internal"),
        node(leaf(4, 5), leaf(6, 7), relation="right-internal"),
        relation="root",
    )
    relations, _ = flatten_tree(tree, spans, ())
    assert [r.relation for r in relations] == ["root", "left-internal", "right-internal"]


def test_unrecognised_nuclearity_treated_as_NN() -> None:
    spans = (
        _span("/doclang[1]/text[1]", 0, 1),
        _span("/doclang[1]/text[2]", 2, 3),
    )
    tree = node(leaf(0, 1), leaf(2, 3), nuclearity="WAT")
    relations, _ = flatten_tree(tree, spans, ())
    assert relations[0].nucleus_xpaths == (
        "/doclang[1]/text[1]",
        "/doclang[1]/text[2]",
    )
    assert relations[0].satellite_xpaths == ()


def test_lopsided_overlap_note_appears_on_relation() -> None:
    spans = (
        _span("/doclang[1]/text[1]", 0, 100),
        _span("/doclang[1]/text[2]", 100, 200),
    )
    tree = node(leaf(0, 100), leaf(100, 108))
    relations, _ = flatten_tree(tree, spans, ())
    assert relations[0].note is not None
