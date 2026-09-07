"""Adversarial bracket collections must not reuse gold occurrences for credit."""

import pytest
from itertools import permutations, product

from workbench.evaluation.rst.parseval import (
    BracketSpan,
    CharBracketSpan,
    SoftParsevalScorer,
    StandardParsevalScorer,
    maximum_match_count,
)


def test_standard_repeated_coordinates_do_not_inflate_recall() -> None:
    gold = {BracketSpan(1, 2, "NS", "cause")}
    predicted = gold | {BracketSpan(1, 2, "NS", "contrast"), BracketSpan(1, 2, "NN", "cause")}
    metrics = StandardParsevalScorer().score_span_sets(gold, predicted)
    assert (metrics.matched_span, metrics.matched_nuclearity,
            metrics.matched_relation, metrics.matched_full) == (1, 1, 1, 1)
    assert metrics.span_precision == pytest.approx(1 / 3)
    assert metrics.span_recall == 1
    assert metrics.span_f1 == 0.5


@pytest.mark.parametrize("gold_count,predicted_count", [(1, 3), (3, 1), (2, 3), (3, 3)])
def test_character_exact_matching_preserves_occurrence_counts(gold_count: int, predicted_count: int) -> None:
    bracket = CharBracketSpan(0, 10, "NS", "cause")
    metrics = SoftParsevalScorer().score_span_sets([bracket] * gold_count, [bracket] * predicted_count)
    matches = min(gold_count, predicted_count)
    assert (metrics.matched_span, metrics.matched_nuclearity,
            metrics.matched_relation, metrics.matched_full) == (matches,) * 4
    assert metrics.full_precision == matches / predicted_count
    assert metrics.full_recall == matches / gold_count


def test_label_matches_cannot_be_combined_into_a_nonexistent_full_match() -> None:
    gold = [CharBracketSpan(0, 10, "NS", "cause"), CharBracketSpan(0, 10, "NN", "contrast")]
    predicted = [CharBracketSpan(0, 10, "NN", "cause"), CharBracketSpan(0, 10, "NS", "contrast")]
    scorer = SoftParsevalScorer()
    metrics = scorer.score_span_sets(gold, predicted)
    assert (metrics.matched_span, metrics.matched_nuclearity,
            metrics.matched_relation, metrics.matched_full) == (2, 2, 2, 0)
    assert scorer.score_span_sets(list(reversed(gold)), list(reversed(predicted))) == metrics


def test_overlap_matching_reassigns_a_greedy_choice() -> None:
    gold = [CharBracketSpan(0, 10, "NS", "cause"), CharBracketSpan(0, 6, "NS", "cause")]
    predicted = [CharBracketSpan(0, 9, "NS", "cause"), CharBracketSpan(4, 10, "NS", "cause")]
    # First prediction prefers gold[0], but can match gold[1]. The second can
    # only match gold[0]. Both matches are attainable at an overlap of 1/2.
    scorer = SoftParsevalScorer(min_iou=0.5)
    for gold_order in permutations(gold):
        for prediction_order in permutations(predicted):
            metrics = scorer.score_span_sets(gold_order, prediction_order)
            assert metrics.matched_span == metrics.matched_full == 2
            assert metrics.full_f1 == 1


def test_overlap_label_metrics_have_independent_eligible_matches() -> None:
    gold = [CharBracketSpan(0, 10, "NS", "cause"), CharBracketSpan(0, 9, "NN", "contrast")]
    predicted = [CharBracketSpan(0, 10, "NN", "contrast"), CharBracketSpan(0, 9, "NS", "cause")]
    metrics = SoftParsevalScorer(min_iou=0.8).score_span_sets(gold, predicted)
    assert metrics.span_f1 == metrics.nuclearity_f1 == metrics.relation_f1 == metrics.full_f1 == 1


def test_maximum_matching_against_exhaustive_assignment_oracle() -> None:
    # Every 3-by-3 eligibility graph; independently enumerate assignments,
    # including unmatched predictions, rather than reproducing augmenting paths.
    size = 3
    for eligible in product((False, True), repeat=size * size):
        candidates = [[g for g in range(size) if eligible[p * size + g]] for p in range(size)]
        maximum = 0
        for assignment in product(range(-1, size), repeat=size):
            assigned = [g for g in assignment if g >= 0]
            if len(set(assigned)) != len(assigned):
                continue
            if all(g < 0 or g in candidates[p] for p, g in enumerate(assignment)):
                maximum = max(maximum, len(assigned))
        assert maximum_match_count(candidates) == maximum


def test_matching_supports_augmenting_paths_beyond_python_recursion_depth() -> None:
    import sys

    size = sys.getrecursionlimit() + 1
    candidates = [[index, index + 1] for index in range(size)] + [[0]]
    assert maximum_match_count(candidates) == size + 1
