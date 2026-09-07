"""Segmentation scoring uses source coordinates, not renumbered EDU identities."""

from rdam.rst.contracts import NodeKindEnum, OutputFormalismEnum, RstAnalysis, RstNode
from workbench.evaluation.rst.regression import segmentation_counts


def _leaves(spans: tuple[tuple[int, int], ...]) -> RstAnalysis:
    return RstAnalysis(
        document_id="source", formalism=OutputFormalismEnum.RST_TREE, primary_edges=(),
        nodes=tuple(RstNode(node_id=index, kind=NodeKindEnum.EDU, edu_span=(index, index),
                            char_span=span, text="x") for index, span in enumerate(spans, start=1)),
    )


def test_inserted_boundary_does_not_shift_later_coordinate_matches() -> None:
    gold = _leaves(((0, 10), (11, 20), (21, 30)))
    prediction = _leaves(((0, 5), (6, 10), (11, 20), (21, 30)))
    assert segmentation_counts(gold, prediction) == {
        "edu_spans": {"gold": 3, "predicted": 4, "matched": 2},
        "internal_boundaries": {"gold": 2, "predicted": 3, "matched": 2},
    }


def test_document_end_is_not_credited_as_an_internal_segmentation_decision() -> None:
    gold = _leaves(((0, 10), (11, 20)))
    prediction = _leaves(((0, 20),))
    assert segmentation_counts(gold, prediction) == {
        "edu_spans": {"gold": 2, "predicted": 1, "matched": 0},
        "internal_boundaries": {"gold": 1, "predicted": 0, "matched": 0},
    }


def test_empty_predictions_do_not_gain_boundary_credit() -> None:
    metrics = segmentation_counts(_leaves(((0, 10), (11, 20))), _leaves(()))
    assert metrics["edu_spans"] == {"gold": 2, "predicted": 0, "matched": 0}
    assert metrics["internal_boundaries"] == {"gold": 1, "predicted": 0, "matched": 0}
