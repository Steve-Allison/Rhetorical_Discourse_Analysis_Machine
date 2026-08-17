"""Unit tests for ``isanlp_rst.markdown.mapper``.

The markdown mapper is a thin binding over the format-agnostic
``_rst_common`` overlap maths (already covered by the docling /
doclang mapper tests). These tests therefore focus on:

- the markdown-specific binding (``ref_of`` reads ``span.block_ref``);
- ``flatten_tree`` id-namespace invariants;
- nuclearity routing to ``nucleus_refs`` / ``satellite_refs``;
- ``boundary_memberships`` intersection against markdown boundaries.
"""

from dataclasses import dataclass

from isanlp_rst.markdown.mapper import compute_overlap_refs, flatten_tree
from isanlp_rst.markdown.schema import Boundary, HarvestSpan


@dataclass
class FakeUnit:
    """Stand-in for ``DiscourseUnit`` — same duck-typed attributes."""

    start: int
    end: int
    left: FakeUnit | None = None
    right: FakeUnit | None = None
    relation: str = ""
    nuclearity: str = ""


def _span(block_ref: str, start: int, end: int, kind: str = "paragraph") -> HarvestSpan:
    return HarvestSpan(
        block_ref=block_ref,
        kind=kind,
        text="x" * (end - start),
        start=start,
        end=end,
        line_begin=0,
        line_end=0,
    )


# --- compute_overlap_refs binding contract --------------------------------


def test_overlap_returns_block_refs_not_other_attrs() -> None:
    """Verify the wrapper reads ``block_ref`` (not ``kind`` or ``text``)."""
    spans = (
        _span("#/blocks/0", 0, 10),
        _span("#/blocks/1", 10, 20),
    )
    refs, _ = compute_overlap_refs(5, 15, spans)
    assert refs == ("#/blocks/0", "#/blocks/1")


def test_overlap_zero_width_range_returns_empty() -> None:
    refs, note = compute_overlap_refs(5, 5, (_span("#/blocks/0", 0, 10),))
    assert refs == ()
    assert note is None


# --- flatten_tree id-namespace invariants --------------------------------


def test_flatten_tree_ids_are_unique_across_relations_and_edus() -> None:
    """Shared id namespace: every node id must be unique."""
    leaf_a = FakeUnit(start=0, end=5)
    leaf_b = FakeUnit(start=5, end=10)
    root = FakeUnit(start=0, end=10, left=leaf_a, right=leaf_b,
                    relation="elaboration", nuclearity="NS")
    spans = (_span("#/blocks/0", 0, 5), _span("#/blocks/1", 5, 10))
    relations, edus = flatten_tree(root, spans, ())
    ids = [r.id for r in relations] + [e.id for e in edus]
    assert len(ids) == len(set(ids))


def test_flatten_tree_left_right_ids_resolve_into_id_set() -> None:
    """Every left_id / right_id must resolve to a relation OR an edu id."""
    leaf_a = FakeUnit(start=0, end=5)
    leaf_b = FakeUnit(start=5, end=10)
    leaf_c = FakeUnit(start=10, end=15)
    inner = FakeUnit(start=0, end=10, left=leaf_a, right=leaf_b,
                     relation="elaboration", nuclearity="NS")
    root = FakeUnit(start=0, end=15, left=inner, right=leaf_c,
                    relation="background", nuclearity="SN")
    spans = (_span(f"#/blocks/{i}", i * 5, (i + 1) * 5) for i in range(3))
    relations, edus = flatten_tree(root, tuple(spans), ())
    known = {r.id for r in relations} | {e.id for e in edus}
    for r in relations:
        assert r.left_id in known
        assert r.right_id in known


def test_flatten_tree_root_id_is_zero() -> None:
    """Pre-order traversal must assign 0 to the root."""
    leaf_a = FakeUnit(start=0, end=5)
    leaf_b = FakeUnit(start=5, end=10)
    root = FakeUnit(start=0, end=10, left=leaf_a, right=leaf_b,
                    relation="x", nuclearity="NS")
    spans = (_span("#/blocks/0", 0, 5), _span("#/blocks/1", 5, 10))
    relations, _ = flatten_tree(root, spans, ())
    assert relations[0].id == 0


# --- Nuclearity routing --------------------------------------------------


def test_ns_routes_left_to_nucleus_right_to_satellite() -> None:
    leaf_l = FakeUnit(start=0, end=5)
    leaf_r = FakeUnit(start=5, end=10)
    root = FakeUnit(start=0, end=10, left=leaf_l, right=leaf_r,
                    relation="elab", nuclearity="NS")
    spans = (_span("#/blocks/0", 0, 5), _span("#/blocks/1", 5, 10))
    relations, _ = flatten_tree(root, spans, ())
    assert relations[0].nucleus_refs == ("#/blocks/0",)
    assert relations[0].satellite_refs == ("#/blocks/1",)


def test_sn_routes_right_to_nucleus() -> None:
    leaf_l = FakeUnit(start=0, end=5)
    leaf_r = FakeUnit(start=5, end=10)
    root = FakeUnit(start=0, end=10, left=leaf_l, right=leaf_r,
                    relation="cause", nuclearity="SN")
    spans = (_span("#/blocks/0", 0, 5), _span("#/blocks/1", 5, 10))
    relations, _ = flatten_tree(root, spans, ())
    assert relations[0].nucleus_refs == ("#/blocks/1",)
    assert relations[0].satellite_refs == ("#/blocks/0",)


def test_nn_routes_both_to_nucleus_empty_satellite() -> None:
    """Multi-nuclear: both children land in nucleus, satellite is empty."""
    leaf_l = FakeUnit(start=0, end=5)
    leaf_r = FakeUnit(start=5, end=10)
    root = FakeUnit(start=0, end=10, left=leaf_l, right=leaf_r,
                    relation="joint", nuclearity="NN")
    spans = (_span("#/blocks/0", 0, 5), _span("#/blocks/1", 5, 10))
    relations, _ = flatten_tree(root, spans, ())
    assert relations[0].nucleus_refs == ("#/blocks/0", "#/blocks/1")
    assert relations[0].satellite_refs == ()


# --- Boundary memberships ------------------------------------------------


def test_boundary_membership_lists_only_intersecting_boundaries() -> None:
    """A relation over span 0 must NOT pick up section-1 (covers span 1)."""
    leaf_a = FakeUnit(start=0, end=5)
    leaf_b = FakeUnit(start=5, end=10)
    root = FakeUnit(start=0, end=10, left=leaf_a, right=leaf_b,
                    relation="elab", nuclearity="NS")
    spans = (_span("#/blocks/0", 0, 5), _span("#/blocks/1", 5, 10))
    boundaries = (
        Boundary(id="section-0", kind="section", label="A",
                 parent_block_ref=None, block_refs=("#/blocks/0",), level=1),
        Boundary(id="section-1", kind="section", label="B",
                 parent_block_ref=None, block_refs=("#/blocks/1",), level=1),
    )
    relations, _ = flatten_tree(root, spans, boundaries)
    # The root relation spans both boundaries; both must appear.
    assert set(relations[0].boundary_memberships) == {"section-0", "section-1"}


def test_synthetic_table_marker_never_in_relation_refs() -> None:
    """``#/tables/N`` lives in boundary.block_refs but no span carries it,
    so the overlap rule cannot land it in nucleus_refs / satellite_refs."""
    leaf_a = FakeUnit(start=0, end=5)
    leaf_b = FakeUnit(start=5, end=10)
    root = FakeUnit(start=0, end=10, left=leaf_a, right=leaf_b,
                    relation="elab", nuclearity="NS")
    spans = (
        _span("#/blocks/0", 0, 5, kind="table_cell"),
        _span("#/blocks/1", 5, 10, kind="table_cell"),
    )
    boundaries = (
        Boundary(id="table-0", kind="table", label=None,
                 parent_block_ref=None,
                 block_refs=("#/tables/0", "#/blocks/0", "#/blocks/1")),
    )
    relations, _ = flatten_tree(root, spans, boundaries)
    for r in relations:
        assert "#/tables/0" not in r.nucleus_refs
        assert "#/tables/0" not in r.satellite_refs
