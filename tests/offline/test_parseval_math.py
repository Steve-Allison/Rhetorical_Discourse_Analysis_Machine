"""Mathematical proof tests for Standard-Parseval, eRST scorers, and calibration."""

import pytest

from rdam.rst.annotation_rst import DiscourseUnit
from rdam.rst.converter import du_to_analysis

from rdam.rst.contracts import (
    AnnotationStatusEnum,
    DiscourseSignal,
    NodeKindEnum,
    OutputFormalismEnum,
    RstAnalysis,
    RstNode,
    SecondaryRelationEdge,
    SignalDetectionMethod,
    SignalDetectorProvenance,
)
from workbench.evaluation.rst import (
    CharBracketSpan,
    ErstScorer,
    SoftParsevalScorer,
    StandardParsevalScorer,
    compute_calibration_error,
    compute_span_iou,
)

SIGNAL_TEST_DETECTOR = SignalDetectorProvenance(
    detector_id="scorer-test",
    detector_version="1.0.0",
    method=SignalDetectionMethod.GOLD,
)


def _sample_edus() -> tuple[DiscourseUnit, ...]:
    return tuple(
        DiscourseUnit(id=index + 1, text=str(index), start=index * 2, end=index * 2 + 1)
        for index in range(4)
    )


def _make_sample_tree_1() -> RstAnalysis:
    one, two, three, four = _sample_edus()
    first = DiscourseUnit(id=5, left=one, right=two, nuclearity="NS", relation="Elaboration")
    second = DiscourseUnit(id=6, left=first, right=three, nuclearity="SN", relation="Attribution")
    root = DiscourseUnit(id=7, left=second, right=four, nuclearity="NS", relation="Cause")
    return du_to_analysis(root, document_id="doc-proof-1")


def _make_sample_tree_2() -> RstAnalysis:
    one, two, three, four = _sample_edus()
    first = DiscourseUnit(id=5, left=one, right=two, nuclearity="NS", relation="Elaboration")
    second = DiscourseUnit(id=6, left=three, right=four, nuclearity="NS", relation="Cause")
    root = DiscourseUnit(id=7, left=first, right=second, nuclearity="NS", relation="Cause")
    return du_to_analysis(root, document_id="doc-proof-2")


def test_standard_parseval_identical_trees_score_one() -> None:
    tree = _make_sample_tree_1()
    scorer = StandardParsevalScorer(include_leaves=False, include_root=False)
    metrics = scorer.score(tree, tree)

    assert metrics.span_precision == 1.0
    assert metrics.span_recall == 1.0
    assert metrics.span_f1 == 1.0

    assert metrics.nuclearity_precision == 1.0
    assert metrics.nuclearity_recall == 1.0
    assert metrics.nuclearity_f1 == 1.0

    assert metrics.relation_precision == 1.0
    assert metrics.relation_recall == 1.0
    assert metrics.relation_f1 == 1.0

    assert metrics.full_precision == 1.0
    assert metrics.full_recall == 1.0
    assert metrics.full_f1 == 1.0


def test_standard_parseval_hand_computed_math() -> None:
    gold = _make_sample_tree_1()
    pred = _make_sample_tree_2()

    scorer = StandardParsevalScorer(include_leaves=False, include_root=False)
    metrics = scorer.score(gold, pred)

    # Gold non-trivial non-root spans: [1,2], [1,3] -> count = 2
    # Pred non-trivial non-root spans: [1,2], [3,4] -> count = 2
    # Matched span: [1,2] -> 1
    # Matched nuc: [1,2] both NS -> 1
    # Matched rel: [1,2] both Elaboration -> 1
    # Matched full: [1,2] both NS+Elaboration -> 1

    assert metrics.gold_spans_count == 2
    assert metrics.pred_spans_count == 2
    assert metrics.matched_span == 1
    assert metrics.matched_nuclearity == 1
    assert metrics.matched_relation == 1
    assert metrics.matched_full == 1

    assert metrics.span_precision == 0.5
    assert metrics.span_recall == 0.5
    assert metrics.span_f1 == 0.5

    assert metrics.nuclearity_f1 == 0.5
    assert metrics.relation_f1 == 0.5
    assert metrics.full_f1 == 0.5


def test_erst_secondary_and_signals_scoring() -> None:
    nodes = tuple(
        RstNode(
            node_id=index,
            kind=NodeKindEnum.EDU,
            edu_span=(index, index),
            char_span=(index - 1, index),
            text=str(index),
        )
        for index in range(1, 5)
    )
    gold_sec = (
        SecondaryRelationEdge(
            edge_id="s1", source_id=1, target_id=3, relation_raw="Antithesis", relation_concept="Contrast"
        ),
        SecondaryRelationEdge(
            edge_id="s2", source_id=2, target_id=4, relation_raw="Concession", relation_concept="Contrast"
        ),
    )
    pred_sec = (
        SecondaryRelationEdge(
            edge_id="s1", source_id=1, target_id=3, relation_raw="Antithesis", relation_concept="Contrast"
        ),
        SecondaryRelationEdge(
            edge_id="s3", source_id=2, target_id=3, relation_raw="Contrast", relation_concept="Contrast"
        ),
    )

    gold_sig = (
        DiscourseSignal(
            signal_id="sig1",
            edge_id="s1",
            signal_type="dm",
            signal_subtype="dm",
            token_ids=(1, 2),
            detector=SIGNAL_TEST_DETECTOR,
            status=AnnotationStatusEnum.GOLD,
        ),
    )
    pred_sig = (
        DiscourseSignal(
            signal_id="sig1",
            edge_id="s1",
            signal_type="dm",
            signal_subtype="dm",
            token_ids=(1, 2),
            detector=SIGNAL_TEST_DETECTOR,
            status=AnnotationStatusEnum.PREDICTED,
        ),
        DiscourseSignal(
            signal_id="sig2",
            edge_id="s3",
            signal_type="lexical",
            signal_subtype="indicative_word",
            token_ids=(5,),
            detector=SIGNAL_TEST_DETECTOR,
            status=AnnotationStatusEnum.PREDICTED,
        ),
    )

    scorer = ErstScorer()
    gold_analysis = RstAnalysis(
        document_id="secondary-math",
        formalism=OutputFormalismEnum.ERST_GRAPH,
        nodes=nodes,
        primary_edges=(),
        secondary_edges=gold_sec,
    )
    pred_analysis = RstAnalysis(
        document_id="secondary-math",
        formalism=OutputFormalismEnum.ERST_GRAPH,
        nodes=nodes,
        primary_edges=(),
        secondary_edges=pred_sec,
    )
    sec_metrics = scorer.score_secondary_edges(gold_analysis, pred_analysis)
    assert sec_metrics.gold_count == 2
    assert sec_metrics.pred_count == 2
    assert sec_metrics.matched_span == 1
    assert sec_metrics.matched_direction == 1
    assert sec_metrics.matched_relation == 1
    assert sec_metrics.full_f1 == 0.5

    sig_metrics = scorer.score_signals(gold_sig, pred_sig, identities_prealigned=True)
    assert sig_metrics.gold_signals_count == 1
    assert sig_metrics.pred_signals_count == 2
    assert sig_metrics.matched_detection == 1
    assert sig_metrics.matched_type == 1
    assert sig_metrics.matched_subtype == 1
    assert sig_metrics.token_precision == pytest.approx(2 / 3, rel=1e-4)
    assert sig_metrics.token_recall == 1.0
    assert sig_metrics.token_f1 == 0.8


def test_erst_empty_and_asymmetric_edges() -> None:
    scorer = ErstScorer()
    empty = RstAnalysis(
        document_id="empty-secondary",
        formalism=OutputFormalismEnum.ERST_GRAPH,
        nodes=(),
        primary_edges=(),
    )
    # Both empty -> 1.0 F1
    sec_empty = scorer.score_secondary_edges(empty, empty)
    assert sec_empty.full_f1 == 1.0
    assert sec_empty.gold_count == 0

    sig_empty = scorer.score_signals((), ())
    assert sig_empty.token_f1 == 1.0
    assert sig_empty.gold_signals_count == 0

    # Gold empty, pred non-empty -> 0.0 F1
    sec_edge = SecondaryRelationEdge(edge_id="s1", source_id=1, target_id=2, relation_raw="Rel", relation_concept="Rel")
    pred = RstAnalysis(
        document_id="empty-secondary",
        formalism=OutputFormalismEnum.ERST_GRAPH,
        nodes=(
            RstNode(node_id=1, kind=NodeKindEnum.EDU, edu_span=(1, 1), char_span=(0, 1), text="1"),
            RstNode(node_id=2, kind=NodeKindEnum.EDU, edu_span=(2, 2), char_span=(1, 2), text="2"),
        ),
        primary_edges=(),
        secondary_edges=(sec_edge,),
    )
    sec_gold_empty = scorer.score_secondary_edges(empty, pred)
    assert sec_gold_empty.full_f1 == 0.0
    assert sec_gold_empty.direction_precision == 0.0


def test_signal_scores_do_not_reuse_gold_or_assume_alignment() -> None:
    gold = DiscourseSignal(
        signal_id="gold", edge_id="shared-edge", signal_type="dm", signal_subtype="dm",
        token_ids=(1, 2), detector=SIGNAL_TEST_DETECTOR, status=AnnotationStatusEnum.GOLD,
    )
    scorer = ErstScorer()
    with pytest.raises(ValueError, match="verified shared"):
        scorer.score_signals((gold,), (gold,))
    result = scorer.score_signals((gold,), (gold, gold), identities_prealigned=True)
    assert result.matched_detection == result.matched_type == result.matched_subtype == 1
    assert result.detection_precision == result.token_precision == 0.5
    assert result.detection_recall == result.token_recall == 1.0
    unattached = gold.model_copy(update={"edge_id": None})
    result = scorer.score_signals((unattached,), (unattached,), identities_prealigned=True)
    assert result.matched_detection == 0
    assert result.token_f1 == 0.0


def test_erst_secondary_parseval_uses_endpoint_yields_and_separates_all_four_metrics() -> None:
    gold = RstAnalysis(
        document_id="yield-identity",
        formalism=OutputFormalismEnum.ERST_GRAPH,
        nodes=(
            RstNode(node_id=1, kind=NodeKindEnum.EDU, edu_span=(1, 1), char_span=(0, 1), text="a"),
            RstNode(node_id=2, kind=NodeKindEnum.SPAN, edu_span=(2, 3), char_span=(2, 5), text="b c"),
        ),
        primary_edges=(),
        secondary_edges=(
            SecondaryRelationEdge(
                edge_id="gold",
                source_id=1,
                target_id=2,
                relation_raw="adversative-contrast",
                relation_concept="Contrast",
            ),
        ),
    )
    reversed_prediction = RstAnalysis(
        document_id="yield-identity",
        formalism=OutputFormalismEnum.ERST_GRAPH,
        nodes=(
            RstNode(node_id=10, kind=NodeKindEnum.EDU, edu_span=(1, 1), char_span=(0, 1), text="a"),
            RstNode(node_id=20, kind=NodeKindEnum.SPAN, edu_span=(2, 3), char_span=(2, 5), text="b c"),
        ),
        primary_edges=(),
        secondary_edges=(
            SecondaryRelationEdge(
                edge_id="prediction",
                source_id=20,
                target_id=10,
                relation_raw="adversative-contrast",
                relation_concept="Contrast",
            ),
        ),
    )

    metrics = ErstScorer().score_secondary_edges(gold, reversed_prediction)

    assert metrics.span_f1 == 1.0
    assert metrics.direction_f1 == 0.0
    assert metrics.relation_f1 == 1.0
    assert metrics.full_f1 == 0.0

    wrong_relation_prediction = RstAnalysis(
        document_id="yield-identity",
        formalism=OutputFormalismEnum.ERST_GRAPH,
        nodes=reversed_prediction.nodes,
        primary_edges=(),
        secondary_edges=(
            SecondaryRelationEdge(
                edge_id="wrong-relation",
                source_id=10,
                target_id=20,
                relation_raw="causal-result",
                relation_concept="Contrast",
            ),
        ),
    )
    wrong_relation = ErstScorer().score_secondary_edges(gold, wrong_relation_prediction)
    assert wrong_relation.span_f1 == 1.0
    assert wrong_relation.direction_f1 == 1.0
    assert wrong_relation.relation_f1 == 0.0
    assert wrong_relation.full_f1 == 0.0


def test_erst_secondary_parseval_rejects_missing_nodes_and_mismatched_corpora() -> None:
    invalid = RstAnalysis(
        document_id="invalid-secondary",
        formalism=OutputFormalismEnum.ERST_GRAPH,
        nodes=(),
        primary_edges=(),
        secondary_edges=(
            SecondaryRelationEdge(
                edge_id="missing",
                source_id=1,
                target_id=2,
                relation_raw="joint-list",
                relation_concept="Joint",
            ),
        ),
    )
    scorer = ErstScorer()
    with pytest.raises(ValueError, match="references a node absent"):
        scorer.score_secondary_edges(invalid, invalid)
    with pytest.raises(ValueError, match="same number of documents"):
        scorer.score_secondary_corpus((invalid,), ())


def test_calibration_ece_hand_computed() -> None:
    # 4 predictions:
    # 2 predictions in [0.8, 1.0]: confs = 0.9, 0.9; both correct (1, 1). Acc = 1.0, Conf = 0.9 -> Err = 0.1
    # 2 predictions in [0.6, 0.8]: confs = 0.7, 0.7; 1 correct (1, 0). Acc = 0.5, Conf = 0.7 -> Err = 0.2
    # Total samples = 4
    # ECE = (2/4)*0.1 + (2/4)*0.2 = 0.05 + 0.10 = 0.15
    confs = [0.9, 0.9, 0.7, 0.7]
    accs = [True, True, True, False]

    summary = compute_calibration_error(confs, accs, n_bins=5)
    assert summary.sample_count == 4
    assert summary.expected_calibration_error == pytest.approx(0.15, rel=1e-6)
    assert summary.max_calibration_error == pytest.approx(0.20, rel=1e-6)


def test_parseval_disjoint_trees_score_zero() -> None:
    gold = _make_sample_tree_1()  # Non-root internal spans [1,2] and [1,3].
    one, two, three, four = _sample_edus()
    first = DiscourseUnit(id=5, left=three, right=four, nuclearity="NS", relation="Elaboration")
    second = DiscourseUnit(id=6, left=two, right=first, nuclearity="NS", relation="Attribution")
    root = DiscourseUnit(id=7, left=one, right=second, nuclearity="NS", relation="Cause")
    pred = du_to_analysis(root)  # Non-root internal spans [3,4] and [2,4].
    metrics = StandardParsevalScorer(include_root=False).score(gold, pred)
    assert metrics.span_f1 == 0.0
    assert metrics.full_f1 == 0.0


def test_parseval_empty_and_corpus_validation() -> None:
    empty_analysis = RstAnalysis(document_id="e", formalism=OutputFormalismEnum.RST_TREE, nodes=(), primary_edges=())
    scorer = StandardParsevalScorer()
    metrics = scorer.score(empty_analysis, empty_analysis)
    assert metrics.span_f1 == 1.0
    assert metrics.gold_spans_count == 0

    with pytest.raises(ValueError, match="Corpus size mismatch"):
        scorer.score_corpus([empty_analysis], [])


def test_calibration_error_mismatched_and_empty() -> None:
    with pytest.raises(ValueError, match="Length mismatch"):
        compute_calibration_error([0.5, 0.8], [True])

    with pytest.raises(ValueError, match="n_bins must be at least 1"):
        compute_calibration_error([0.5], [True], n_bins=0)

    empty_summary = compute_calibration_error([], [])
    assert empty_summary.sample_count == 0
    assert empty_summary.expected_calibration_error is None


def test_parseval_zero_prediction_against_nonempty_gold() -> None:
    # Gold has spans, pred has 0 spans -> precision, recall, and F1 must all be 0.0
    gold = _make_sample_tree_1()
    empty_pred = RstAnalysis(document_id="empty", formalism=OutputFormalismEnum.RST_TREE, nodes=(), primary_edges=())
    scorer = StandardParsevalScorer(include_leaves=False, include_root=False)
    metrics = scorer.score(gold, empty_pred)

    assert metrics.gold_spans_count == 2
    assert metrics.pred_spans_count == 0
    assert metrics.span_precision == 0.0
    assert metrics.span_recall == 0.0
    assert metrics.span_f1 == 0.0



def test_compute_span_iou_math() -> None:
    # CharBracketSpan properties
    span = CharBracketSpan(start_char=10, end_char=25, nuclearity="NS", relation="elaboration")
    assert span.start_char == 10
    assert span.end_char == 25
    assert span.length == 15
    assert span.nuclearity == "NS"
    assert span.relation == "elaboration"

    # Exact overlap
    assert compute_span_iou(0, 10, 0, 10) == 1.0
    # No overlap
    assert compute_span_iou(0, 5, 5, 10) == 0.0
    assert compute_span_iou(0, 5, 10, 15) == 0.0
    # Partial overlap: [0, 10] and [2, 10] -> intersection 8, union 10 -> 0.8
    assert compute_span_iou(0, 10, 2, 10) == pytest.approx(0.8, rel=1e-6)
    # Subset: [2, 8] inside [0, 10] -> intersection 6, union 10 -> 0.6
    assert compute_span_iou(0, 10, 2, 8) == pytest.approx(0.6, rel=1e-6)
    # Zero length
    assert compute_span_iou(5, 5, 5, 5) == 0.0


def test_soft_parseval_exact_and_fuzzy() -> None:
    def analysis_with_boundary(boundary: int) -> RstAnalysis:
        one = DiscourseUnit(id=1, text="one", start=0, end=20)
        two = DiscourseUnit(id=2, text="two", start=21, end=boundary)
        three = DiscourseUnit(id=3, text="three", start=51, end=100)
        first = DiscourseUnit(id=4, left=one, right=two, nuclearity="NS", relation="Elaboration")
        root = DiscourseUnit(id=5, left=first, right=three, nuclearity="NN", relation="Joint")
        return du_to_analysis(root)

    gold = analysis_with_boundary(50)
    pred = analysis_with_boundary(48)
    exact_metrics = SoftParsevalScorer(include_root=False).score(gold, pred)
    assert exact_metrics.matched_span == 0
    assert exact_metrics.span_f1 == 0.0
    soft_metrics = SoftParsevalScorer(include_root=False, min_iou=0.85).score(gold, pred)
    assert soft_metrics.matched_span == 1
    assert soft_metrics.span_f1 == 1.0
    assert soft_metrics.nuclearity_f1 == 1.0
    assert soft_metrics.relation_f1 == 1.0
    assert soft_metrics.full_f1 == 1.0
    # Including the root counts its correct attachment as well.
    assert SoftParsevalScorer().score(gold, pred).matched_full == 1


def test_soft_parseval_invalid_min_iou() -> None:
    with pytest.raises(ValueError, match="min_iou must be in"):
        SoftParsevalScorer(min_iou=0.0)

    with pytest.raises(ValueError, match="min_iou must be in"):
        SoftParsevalScorer(min_iou=1.5)
