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
)
from isanlp_rst.eval import (
    ErstScorer,
    StandardParsevalScorer,
    compute_calibration_error,
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
        PrimaryRelationEdge(edge_id="e1", parent_id=5, child_id=2, relation_raw="Elaboration", relation_concept="Elaboration", nuclearity=NuclearityPatternEnum.NS),
        PrimaryRelationEdge(edge_id="e2", parent_id=6, child_id=3, relation_raw="Attribution", relation_concept="Attribution", nuclearity=NuclearityPatternEnum.SN),
        PrimaryRelationEdge(edge_id="e3", parent_id=7, child_id=4, relation_raw="Cause", relation_concept="Cause", nuclearity=NuclearityPatternEnum.NS),
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
        PrimaryRelationEdge(edge_id="e1", parent_id=5, child_id=2, relation_raw="Elaboration", relation_concept="Elaboration", nuclearity=NuclearityPatternEnum.NS),
        PrimaryRelationEdge(edge_id="e2", parent_id=6, child_id=3, relation_raw="Cause", relation_concept="Cause", nuclearity=NuclearityPatternEnum.NS),
        PrimaryRelationEdge(edge_id="e3", parent_id=7, child_id=4, relation_raw="Cause", relation_concept="Cause", nuclearity=NuclearityPatternEnum.NS),
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
    gold_sec = (
        SecondaryRelationEdge(edge_id="s1", source_id=1, target_id=3, relation_raw="Antithesis", relation_concept="Contrast"),
        SecondaryRelationEdge(edge_id="s2", source_id=2, target_id=4, relation_raw="Concession", relation_concept="Contrast"),
    )
    pred_sec = (
        SecondaryRelationEdge(edge_id="s1", source_id=1, target_id=3, relation_raw="Antithesis", relation_concept="Contrast"),
        SecondaryRelationEdge(edge_id="s3", source_id=2, target_id=3, relation_raw="Contrast", relation_concept="Contrast"),
    )

    gold_sig = (
        DiscourseSignal(signal_id="sig1", edge_id="s1", signal_type="dm", signal_subtype="dm", token_ids=(1, 2), status=AnnotationStatusEnum.GOLD),
    )
    pred_sig = (
        DiscourseSignal(signal_id="sig1", edge_id="s1", signal_type="dm", signal_subtype="dm", token_ids=(1, 2), status=AnnotationStatusEnum.PREDICTED),
        DiscourseSignal(signal_id="sig2", edge_id="s3", signal_type="lexical", signal_subtype="indicative_word", token_ids=(5,), status=AnnotationStatusEnum.PREDICTED),
    )

    scorer = ErstScorer()
    sec_metrics = scorer.score_secondary_edges(gold_sec, pred_sec)
    assert sec_metrics.gold_count == 2
    assert sec_metrics.pred_count == 2
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
    # Both empty -> 1.0 F1
    sec_empty = scorer.score_secondary_edges((), ())
    assert sec_empty.full_f1 == 1.0
    assert sec_empty.gold_count == 0

    sig_empty = scorer.score_signals((), ())
    assert sig_empty.token_f1 == 1.0
    assert sig_empty.gold_signals_count == 0

    # Gold empty, pred non-empty -> 0.0 F1
    sec_edge = SecondaryRelationEdge(edge_id="s1", source_id=1, target_id=2, relation_raw="Rel", relation_concept="Rel")
    sec_gold_empty = scorer.score_secondary_edges((), (sec_edge,))
    assert sec_gold_empty.full_f1 == 0.0
    assert sec_gold_empty.direction_precision == 0.0



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

    empty_summary = compute_calibration_error([], [])
    assert empty_summary.sample_count == 0
    assert empty_summary.expected_calibration_error == 0.0

