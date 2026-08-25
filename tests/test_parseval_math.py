"""Mathematical proof tests for Standard-Parseval, eRST scorers, and calibration."""

import pytest

from isanlp_rst.contracts import (
    AnnotationStatusEnum,
    DiscourseSignal,
    NodeKindEnum,
    NuclearityPatternEnum,
    OutputFormalismEnum,
    PrimaryRelationEdge,
    RstAnalysis,
    RstNode,
    SecondaryRelationEdge,
    SignalDetectionMethod,
    SignalDetectorProvenance,
)
from isanlp_rst.eval import (
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


def _make_sample_tree_1() -> RstAnalysis:
    # 4 EDUs: (1,2) joined, then joined with 3, then joined with 4 (root)
    nodes = (
        RstNode(node_id=1, kind=NodeKindEnum.EDU, edu_span=(1, 1), char_span=(0, 5), text="EDU1"),
        RstNode(node_id=2, kind=NodeKindEnum.EDU, edu_span=(2, 2), char_span=(6, 10), text="EDU2"),
        RstNode(node_id=3, kind=NodeKindEnum.EDU, edu_span=(3, 3), char_span=(11, 15), text="EDU3"),
        RstNode(node_id=4, kind=NodeKindEnum.EDU, edu_span=(4, 4), char_span=(16, 20), text="EDU4"),
        RstNode(node_id=5, kind=NodeKindEnum.SPAN, edu_span=(1, 2), char_span=(0, 10), text="EDU1 EDU2"),
        RstNode(node_id=6, kind=NodeKindEnum.SPAN, edu_span=(1, 3), char_span=(0, 15), text="EDU1 EDU2 EDU3"),
        RstNode(node_id=7, kind=NodeKindEnum.ROOT, edu_span=(1, 4), char_span=(0, 20), text="EDU1 EDU2 EDU3 EDU4"),
    )
    primary_edges = (
        PrimaryRelationEdge(
            edge_id="e1",
            parent_id=5,
            child_id=2,
            relation_raw="Elaboration",
            relation_concept="Elaboration",
            nuclearity=NuclearityPatternEnum.NS,
        ),
        PrimaryRelationEdge(
            edge_id="e2",
            parent_id=6,
            child_id=3,
            relation_raw="Attribution",
            relation_concept="Attribution",
            nuclearity=NuclearityPatternEnum.SN,
        ),
        PrimaryRelationEdge(
            edge_id="e3",
            parent_id=7,
            child_id=4,
            relation_raw="Cause",
            relation_concept="Cause",
            nuclearity=NuclearityPatternEnum.NS,
        ),
    )
    return RstAnalysis(
        document_id="doc-proof-1",
        formalism=OutputFormalismEnum.RST_TREE,
        nodes=nodes,
        primary_edges=primary_edges,
    )


def _make_sample_tree_2() -> RstAnalysis:
    # 4 EDUs: (1,2) joined, (2,3) wrongly proposed instead of (1,3), then root (1,4)
    nodes = (
        RstNode(node_id=1, kind=NodeKindEnum.EDU, edu_span=(1, 1), char_span=(0, 5), text="EDU1"),
        RstNode(node_id=2, kind=NodeKindEnum.EDU, edu_span=(2, 2), char_span=(6, 10), text="EDU2"),
        RstNode(node_id=3, kind=NodeKindEnum.EDU, edu_span=(3, 3), char_span=(11, 15), text="EDU3"),
        RstNode(node_id=4, kind=NodeKindEnum.EDU, edu_span=(4, 4), char_span=(16, 20), text="EDU4"),
        RstNode(node_id=5, kind=NodeKindEnum.SPAN, edu_span=(1, 2), char_span=(0, 10), text="EDU1 EDU2"),
        RstNode(node_id=6, kind=NodeKindEnum.SPAN, edu_span=(2, 3), char_span=(6, 15), text="EDU2 EDU3"),
        RstNode(node_id=7, kind=NodeKindEnum.ROOT, edu_span=(1, 4), char_span=(0, 20), text="EDU1 EDU2 EDU3 EDU4"),
    )
    primary_edges = (
        PrimaryRelationEdge(
            edge_id="e1",
            parent_id=5,
            child_id=2,
            relation_raw="Elaboration",
            relation_concept="Elaboration",
            nuclearity=NuclearityPatternEnum.NS,
        ),
        PrimaryRelationEdge(
            edge_id="e2",
            parent_id=6,
            child_id=3,
            relation_raw="Cause",
            relation_concept="Cause",
            nuclearity=NuclearityPatternEnum.NS,
        ),
        PrimaryRelationEdge(
            edge_id="e3",
            parent_id=7,
            child_id=4,
            relation_raw="Cause",
            relation_concept="Cause",
            nuclearity=NuclearityPatternEnum.NS,
        ),
    )
    return RstAnalysis(
        document_id="doc-proof-2",
        formalism=OutputFormalismEnum.RST_TREE,
        nodes=nodes,
        primary_edges=primary_edges,
    )


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
    # Pred non-trivial non-root spans: [1,2], [2,3] -> count = 2
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

    sig_metrics = scorer.score_signals(gold_sig, pred_sig)
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
    # Gold has [1,2], Pred has [3,4]
    nodes_gold = (
        RstNode(node_id=1, kind=NodeKindEnum.EDU, edu_span=(1, 1), char_span=(0, 5), text="1"),
        RstNode(node_id=2, kind=NodeKindEnum.EDU, edu_span=(2, 2), char_span=(6, 10), text="2"),
        RstNode(node_id=3, kind=NodeKindEnum.EDU, edu_span=(3, 3), char_span=(11, 15), text="3"),
        RstNode(node_id=4, kind=NodeKindEnum.EDU, edu_span=(4, 4), char_span=(16, 20), text="4"),
        RstNode(node_id=5, kind=NodeKindEnum.SPAN, edu_span=(1, 2), char_span=(0, 10), text="1 2"),
        RstNode(node_id=6, kind=NodeKindEnum.ROOT, edu_span=(1, 4), char_span=(0, 20), text="1 2 3 4"),
    )
    nodes_pred = (
        RstNode(node_id=1, kind=NodeKindEnum.EDU, edu_span=(1, 1), char_span=(0, 5), text="1"),
        RstNode(node_id=2, kind=NodeKindEnum.EDU, edu_span=(2, 2), char_span=(6, 10), text="2"),
        RstNode(node_id=3, kind=NodeKindEnum.EDU, edu_span=(3, 3), char_span=(11, 15), text="3"),
        RstNode(node_id=4, kind=NodeKindEnum.EDU, edu_span=(4, 4), char_span=(16, 20), text="4"),
        RstNode(node_id=5, kind=NodeKindEnum.SPAN, edu_span=(3, 4), char_span=(11, 20), text="3 4"),
        RstNode(node_id=6, kind=NodeKindEnum.ROOT, edu_span=(1, 4), char_span=(0, 20), text="1 2 3 4"),
    )
    gold = RstAnalysis(document_id="g", formalism=OutputFormalismEnum.RST_TREE, nodes=nodes_gold, primary_edges=())
    pred = RstAnalysis(document_id="p", formalism=OutputFormalismEnum.RST_TREE, nodes=nodes_pred, primary_edges=())

    scorer = StandardParsevalScorer(include_leaves=False, include_root=False)
    metrics = scorer.score(gold, pred)
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
    assert empty_summary.expected_calibration_error == 0.0


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
    # Tree 1: [0, 50] contains [0, 20] (Elaboration) and [21, 50] (Joint)
    nodes_gold = (
        RstNode(node_id=1, kind=NodeKindEnum.EDU, edu_span=(1, 1), char_span=(0, 20), text="EDU1"),
        RstNode(node_id=2, kind=NodeKindEnum.EDU, edu_span=(2, 2), char_span=(21, 50), text="EDU2"),
        RstNode(node_id=3, kind=NodeKindEnum.SPAN, edu_span=(1, 2), char_span=(0, 50), text="EDU1 EDU2"),
        RstNode(node_id=4, kind=NodeKindEnum.ROOT, edu_span=(1, 3), char_span=(0, 100), text="All"),
    )
    edges_gold = (
        PrimaryRelationEdge(
            edge_id="e1",
            parent_id=3,
            child_id=1,
            nuclearity=NuclearityPatternEnum.NS,
            relation_raw="Elaboration",
            relation_concept="Elaboration",
        ),
        PrimaryRelationEdge(
            edge_id="e2",
            parent_id=4,
            child_id=3,
            nuclearity=NuclearityPatternEnum.NS,
            relation_raw="Joint",
            relation_concept="Joint",
        ),
    )
    gold = RstAnalysis(
        document_id="g", formalism=OutputFormalismEnum.RST_TREE, nodes=nodes_gold, primary_edges=edges_gold
    )

    # Pred has a slightly shifted boundary: [0, 48] instead of [0, 50] (e.g. trailing period segmentation difference)
    nodes_pred = (
        RstNode(node_id=10, kind=NodeKindEnum.EDU, edu_span=(1, 1), char_span=(0, 20), text="EDU1"),
        RstNode(node_id=20, kind=NodeKindEnum.EDU, edu_span=(2, 2), char_span=(21, 48), text="EDU2"),
        RstNode(node_id=30, kind=NodeKindEnum.SPAN, edu_span=(1, 2), char_span=(0, 48), text="EDU1 EDU2"),
        RstNode(node_id=40, kind=NodeKindEnum.ROOT, edu_span=(1, 3), char_span=(0, 100), text="All"),
    )
    edges_pred = (
        PrimaryRelationEdge(
            edge_id="ep1",
            parent_id=30,
            child_id=10,
            nuclearity=NuclearityPatternEnum.NS,
            relation_raw="Elaboration",
            relation_concept="Elaboration",
        ),
        PrimaryRelationEdge(
            edge_id="ep2",
            parent_id=40,
            child_id=30,
            nuclearity=NuclearityPatternEnum.NS,
            relation_raw="Joint",
            relation_concept="Joint",
        ),
    )
    pred = RstAnalysis(
        document_id="p", formalism=OutputFormalismEnum.RST_TREE, nodes=nodes_pred, primary_edges=edges_pred
    )

    # Exact character scorer: [0, 48] != [0, 50] -> 0 matched span
    exact_scorer = SoftParsevalScorer(min_iou=1.0)
    exact_metrics = exact_scorer.score(gold, pred)
    assert exact_metrics.matched_span == 0
    assert exact_metrics.span_f1 == 0.0

    # Soft character scorer: IoU([0, 50], [0, 48]) = 48/50 = 0.96 >= 0.85 -> matched!
    soft_scorer = SoftParsevalScorer(min_iou=0.85)
    soft_metrics = soft_scorer.score(gold, pred)
    assert soft_metrics.matched_span == 1
    assert soft_metrics.span_f1 == 1.0
    assert soft_metrics.nuclearity_f1 == 1.0
    assert soft_metrics.relation_f1 == 1.0
    assert soft_metrics.full_f1 == 1.0


def test_soft_parseval_invalid_min_iou() -> None:
    with pytest.raises(ValueError, match="min_iou must be in"):
        SoftParsevalScorer(min_iou=0.0)

    with pytest.raises(ValueError, match="min_iou must be in"):
        SoftParsevalScorer(min_iou=1.5)
