"""Attachment labels belong to the parent decision, never its children."""

import sys
from dataclasses import replace

import pytest

from rdam.rst.annotation_rst import DiscourseUnit
from rdam.rst.converter import du_to_analysis
from workbench.evaluation.rst.parseval import BracketSpan, StandardParsevalScorer, rst_parseval_spans


def test_du_extraction_reads_each_internal_nodes_own_decision() -> None:
    left = DiscourseUnit(
        left=DiscourseUnit(), right=DiscourseUnit(), nuclearity="SN", relation="concession",
    )
    root = DiscourseUnit(left=left, right=DiscourseUnit(), nuclearity="NS", relation="cause")
    assert StandardParsevalScorer(include_root=True).extract_spans_from_du(root) == {
        BracketSpan(1, 2, "SN", "concession"), BracketSpan(1, 3, "NS", "cause"),
    }
    assert StandardParsevalScorer(include_root=False).extract_spans_from_du(root) == {
        BracketSpan(1, 2, "SN", "concession"),
    }


@pytest.mark.parametrize("nuclearity,relation", [("", "cause"), ("SS", "cause"), ("NS", ""), ("NS", "span")])
def test_du_extraction_rejects_missing_or_invalid_labels(nuclearity: str, relation: str) -> None:
    root = DiscourseUnit(
        left=DiscourseUnit(), right=DiscourseUnit(), nuclearity=nuclearity, relation=relation,
    )
    with pytest.raises(ValueError, match="nuclearity|rhetorical relation"):
        StandardParsevalScorer().extract_spans_from_du(root)


def test_du_extraction_rejects_non_tree_topology() -> None:
    child = DiscourseUnit()
    shared = DiscourseUnit(left=child, right=child, nuclearity="NN", relation="joint")
    with pytest.raises(ValueError, match="shared children"):
        StandardParsevalScorer().extract_spans_from_du(shared)
    shared.left = shared
    with pytest.raises(ValueError, match="cycles"):
        StandardParsevalScorer().extract_spans_from_du(shared)
    shared.left = None
    with pytest.raises(ValueError, match="both children"):
        StandardParsevalScorer().extract_spans_from_du(shared)


def test_du_extraction_handles_a_tree_deeper_than_the_recursion_limit() -> None:
    depth = sys.getrecursionlimit() + 1
    root = DiscourseUnit()
    for _ in range(depth):
        root = DiscourseUnit(left=root, right=DiscourseUnit(), nuclearity="NN", relation="joint")
    brackets = StandardParsevalScorer(include_root=True).extract_spans_from_du(root)
    assert len(brackets) == depth
    assert BracketSpan(1, depth + 1, "NN", "joint") in brackets


@pytest.mark.parametrize("pattern", ["NS", "SN", "NN"])
def test_native_and_du_extraction_agree_and_preserve_native_labels(pattern: str) -> None:
    first = DiscourseUnit(id=1, text="a", start=0, end=1)
    second = DiscourseUnit(id=2, text="b", start=2, end=3)
    third = DiscourseUnit(id=3, text="c", start=4, end=5)
    subtree = DiscourseUnit(id=4, left=first, right=second, nuclearity=pattern, relation="concession")
    root = DiscourseUnit(id=5, left=subtree, right=third, nuclearity="NS", relation="cause")
    native = du_to_analysis(root)
    native = replace(native, primary_edges=tuple(
        replace(edge, relation_concept="Contrast") for edge in native.primary_edges
    ))
    scorer = StandardParsevalScorer()
    expected = {BracketSpan(1, 2, pattern, "concession"), BracketSpan(1, 3, "NS", "cause")}
    assert scorer.extract_spans_from_du(root) == expected
    assert scorer.extract_spans_from_analysis(native) == expected
    assert scorer.score(root, native).full_f1 == 1
    reordered = replace(native,
        nodes=tuple(reversed(native.nodes)), primary_edges=tuple(reversed(native.primary_edges)),
    )
    assert scorer.extract_spans_from_analysis(reordered) == expected


def test_rst_parseval_scores_incoming_roles_including_leaves_but_not_root() -> None:
    first = DiscourseUnit(id=1, text="a", start=0, end=1)
    second = DiscourseUnit(id=2, text="b", start=2, end=3)
    third = DiscourseUnit(id=3, text="c", start=4, end=5)
    subtree = DiscourseUnit(id=4, left=first, right=second, nuclearity="SN", relation="concession")
    root = DiscourseUnit(id=5, left=subtree, right=third, nuclearity="NS", relation="cause")
    native = du_to_analysis(root)
    assert rst_parseval_spans(native) == {
        BracketSpan(1, 1, "S", "concession"), BracketSpan(2, 2, "N", "span"),
        BracketSpan(1, 2, "N", "span"), BracketSpan(3, 3, "S", "cause"),
    }
    assert len(StandardParsevalScorer().extract_spans_from_analysis(native)) == 2
