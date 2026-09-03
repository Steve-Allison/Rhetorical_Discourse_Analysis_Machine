"""Shared, total metric arithmetic for the two production RST parser families."""

from collections.abc import Sequence

type MetricTriple = tuple[float, float, float]
type MetricQuadruple = tuple[MetricTriple, MetricTriple, MetricTriple, MetricTriple]


def is_no_tree(value: str) -> bool:
    """Return whether a parser span payload represents the explicit no-tree state."""

    return value.casefold() == "none"


def metric_triple(n_correct: float, n_predicted: float, n_gold: float) -> MetricTriple:
    """Calculate precision, recall, and F1 with defined empty-set semantics."""

    precision = n_correct / n_predicted if n_predicted else 0.0
    recall = n_correct / n_gold if n_gold else 0.0
    denominator = n_gold + n_predicted
    f1 = 2 * n_correct / denominator if denominator else 0.0
    return precision, recall, f1


def micro_metrics(
    correct_span: float,
    correct_relation: float,
    correct_nuclearity: float,
    correct_full: float,
    n_system: float,
    n_gold: float,
    n_gold_segments: float,
    n_predicted_segments: float,
    n_correct_segments: float,
) -> tuple[MetricTriple, MetricTriple, MetricTriple, float, MetricTriple]:
    """Calculate all parser micro metrics without partial zero-denominator cases."""

    span = metric_triple(correct_span, n_system, n_gold)
    relation = metric_triple(correct_relation, n_system, n_gold)
    nuclearity = metric_triple(correct_nuclearity, n_system, n_gold)
    full = metric_triple(correct_full, n_system, n_gold)[2]
    segmentation = metric_triple(n_correct_segments, n_predicted_segments, n_gold_segments)
    return span, relation, nuclearity, full, segmentation


def macro_metrics(
    correct_span: Sequence[float],
    correct_nuclearity: Sequence[float],
    correct_relation: Sequence[float],
    correct_full: Sequence[float],
    n_system: Sequence[float],
    n_gold: Sequence[float],
) -> MetricQuadruple:
    """Average document-level metrics after validating aligned input lengths."""

    sequences = (correct_span, correct_nuclearity, correct_relation, correct_full, n_system, n_gold)
    lengths = {len(sequence) for sequence in sequences}
    if len(lengths) != 1:
        raise ValueError("macro metric inputs must have equal lengths")
    if not correct_span:
        zero = (0.0, 0.0, 0.0)
        return zero, zero, zero, zero

    span_rows, nuclearity_rows, relation_rows, full_rows = (
        [
            metric_triple(correct, predicted, gold)
            for correct, predicted, gold in zip(values, n_system, n_gold, strict=True)
        ]
        for values in (correct_span, correct_nuclearity, correct_relation, correct_full)
    )
    return (
        _mean_metric(span_rows),
        _mean_metric(nuclearity_rows),
        _mean_metric(relation_rows),
        _mean_metric(full_rows),
    )


def _mean_metric(rows: Sequence[MetricTriple]) -> MetricTriple:
    count = len(rows)
    return (
        sum(row[0] for row in rows) / count,
        sum(row[1] for row in rows) / count,
        sum(row[2] for row in rows) / count,
    )


__all__ = ["MetricTriple", "is_no_tree", "macro_metrics", "metric_triple", "micro_metrics"]
