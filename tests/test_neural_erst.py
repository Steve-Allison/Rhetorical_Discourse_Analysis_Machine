"""Unit tests for NeuralSecondaryEdgeScorer, AcyclicDagDecoder, and eRST candidate generation."""

import pytest
import torch

from isanlp_rst.contracts import (
    NodeKindEnum,
    NuclearityPatternEnum,
    OutputFormalismEnum,
    PrimaryRelationEdge,
    RstAnalysis,
    RstDocument,
    RstNode,
)
from isanlp_rst.english.erst.completer import ErstCompleter
from isanlp_rst.erst.dag_decoder import AcyclicDagDecoder
from isanlp_rst.erst.dataset import (
    SecondaryEdgeCandidate,
    extract_eRST_candidates_from_document,
)
from isanlp_rst.erst.neural_scorer import NeuralSecondaryEdgeScorer
from scripts.train_erst_scorer import compute_edge_metrics


def test_compute_edge_metrics_math() -> None:
    preds = [1, 1, 0, 1, 0]
    targets = [1, 0, 1, 1, 0]

    metrics = compute_edge_metrics(preds, targets)
    assert metrics["true_positives"] == 2
    assert metrics["false_positives"] == 1
    assert metrics["false_negatives"] == 1
    assert metrics["precision"] == pytest.approx(2 / 3)
    assert metrics["recall"] == pytest.approx(2 / 3)


def test_acyclic_dag_decoder_prevents_cycles() -> None:
    # Build a simple primary tree: 3 -> 1 and 3 -> 2
    analysis = RstAnalysis(
        document_id="doc_dag_test",
        formalism=OutputFormalismEnum.RST_TREE,
        nodes=(
            RstNode(node_id=1, kind=NodeKindEnum.EDU, edu_span=(1, 1), char_span=(0, 10), text="Node 1"),
            RstNode(node_id=2, kind=NodeKindEnum.EDU, edu_span=(2, 2), char_span=(11, 20), text="Node 2"),
            RstNode(node_id=3, kind=NodeKindEnum.ROOT, edu_span=(1, 2), char_span=(0, 20), text="Node 1 Node 2"),
        ),
        primary_edges=(
            PrimaryRelationEdge(
                edge_id="p1",
                parent_id=3,
                child_id=1,
                nuclearity=NuclearityPatternEnum.NS,
                relation_raw="Elaboration",
                relation_concept="Elaboration",
            ),
            PrimaryRelationEdge(
                edge_id="p2",
                parent_id=3,
                child_id=2,
                nuclearity=NuclearityPatternEnum.NS,
                relation_raw="Elaboration",
                relation_concept="Elaboration",
            ),
        ),
    )

    # Synthetic candidate edges that would form a cycle if both accepted: 1 -> 2 and 2 -> 1
    cands = [
        SecondaryEdgeCandidate(
            source_id=1,
            target_id=2,
            source_text="Node 1",
            target_text="Node 2",
            source_char_span=(0, 10),
            target_char_span=(11, 20),
            structural_features=(1.0,) * 9,
            is_gold_edge=False,
        ),
        SecondaryEdgeCandidate(
            source_id=2,
            target_id=1,
            source_text="Node 2",
            target_text="Node 1",
            source_char_span=(11, 20),
            target_char_span=(0, 10),
            structural_features=(1.0,) * 9,
            is_gold_edge=False,
        ),
    ]

    # Both have high edge prob, but 1->2 has higher joint score
    edge_probs = [0.95, 0.90]
    rel_logits = [[1.0] + [0.0] * 17, [1.0] + [0.0] * 17]

    decoder = AcyclicDagDecoder(min_confidence_threshold=0.50)
    decoded = decoder.decode(analysis, cands, edge_probs, rel_logits)

    # Exactly 1 edge must be accepted; the 2nd edge (creating a cycle) MUST be rejected!
    assert len(decoded) == 1
    assert decoded[0].source_id == 1
    assert decoded[0].target_id == 2


def test_extract_erst_candidates_ancestry_pruning() -> None:
    doc = RstDocument.from_text("Statement one. Statement two. Statement three.", document_id="doc_prune")

    # Primary tree: Root 4 -> Span 1, 2 (Node 3) and Node 3 -> Node 1, Node 2
    analysis = RstAnalysis(
        document_id="doc_prune",
        formalism=OutputFormalismEnum.RST_TREE,
        nodes=(
            RstNode(node_id=1, kind=NodeKindEnum.EDU, edu_span=(1, 1), char_span=(0, 14), text="Statement one."),
            RstNode(node_id=2, kind=NodeKindEnum.EDU, edu_span=(2, 2), char_span=(15, 29), text="Statement two."),
            RstNode(node_id=3, kind=NodeKindEnum.EDU, edu_span=(3, 3), char_span=(30, 46), text="Statement three."),
            RstNode(node_id=4, kind=NodeKindEnum.ROOT, edu_span=(1, 3), char_span=(0, 46), text="Full text"),
        ),
        primary_edges=(
            PrimaryRelationEdge(
                edge_id="e1",
                parent_id=4,
                child_id=1,
                nuclearity=NuclearityPatternEnum.NS,
                relation_raw="Elaboration",
                relation_concept="Elaboration",
            ),
            PrimaryRelationEdge(
                edge_id="e2",
                parent_id=4,
                child_id=2,
                nuclearity=NuclearityPatternEnum.NS,
                relation_raw="Elaboration",
                relation_concept="Elaboration",
            ),
            PrimaryRelationEdge(
                edge_id="e3",
                parent_id=4,
                child_id=3,
                nuclearity=NuclearityPatternEnum.NS,
                relation_raw="Elaboration",
                relation_concept="Elaboration",
            ),
        ),
    )

    candidates = extract_eRST_candidates_from_document(doc, analysis)
    assert len(candidates) > 0

    # Verify no candidate links a node to its direct ancestor (Node 4)
    for c in candidates:
        assert c.source_id != c.target_id
        # Primary parent 4 cannot be target from child or vice versa
        assert not (c.source_id == 4 and c.target_id in (1, 2, 3))
        assert not (c.source_id in (1, 2, 3) and c.target_id == 4)


@pytest.mark.slow
def test_neural_secondary_edge_scorer_forward() -> None:
    scorer = NeuralSecondaryEdgeScorer(model_name_or_path="microsoft/deberta-v3-base", device="cpu")

    src_ids = torch.randint(1, 1000, (2, 16))
    src_mask = torch.ones((2, 16), dtype=torch.long)
    tgt_ids = torch.randint(1, 1000, (2, 16))
    tgt_mask = torch.ones((2, 16), dtype=torch.long)
    struct_feats = torch.randn((2, 9), dtype=torch.float)
    edge_labels = torch.tensor([1.0, 0.0], dtype=torch.float)
    rel_labels = torch.tensor([2, -100], dtype=torch.long)

    out = scorer(
        src_input_ids=src_ids,
        src_attention_mask=src_mask,
        tgt_input_ids=tgt_ids,
        tgt_attention_mask=tgt_mask,
        struct_features=struct_feats,
        edge_label=edge_labels,
        rel_label=rel_labels,
    )

    assert "edge_logits" in out
    assert "edge_probs" in out
    assert "rel_logits" in out
    assert "loss" in out
    assert out["edge_probs"].shape == (2,)
    assert out["rel_logits"].shape == (2, 18)
    assert out["loss"].item() > 0.0


@pytest.mark.slow
def test_erst_completer_integration_with_neural_scorer() -> None:
    doc = RstDocument.from_text("First clause. However second clause follows.", document_id="doc_int_test")
    analysis = RstAnalysis(
        document_id="doc_int_test",
        formalism=OutputFormalismEnum.RST_TREE,
        nodes=(
            RstNode(node_id=1, kind=NodeKindEnum.EDU, edu_span=(1, 1), char_span=(0, 13), text="First clause."),
            RstNode(
                node_id=2,
                kind=NodeKindEnum.EDU,
                edu_span=(2, 2),
                char_span=(14, 44),
                text="However second clause follows.",
            ),
            RstNode(node_id=3, kind=NodeKindEnum.ROOT, edu_span=(1, 2), char_span=(0, 44), text="Full text"),
        ),
        primary_edges=(
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
                parent_id=3,
                child_id=2,
                nuclearity=NuclearityPatternEnum.NS,
                relation_raw="Elaboration",
                relation_concept="Elaboration",
            ),
        ),
    )

    scorer = NeuralSecondaryEdgeScorer(model_name_or_path="microsoft/deberta-v3-base", device="cpu")
    completer = ErstCompleter()
    completed_analysis = completer.complete_graph(doc, analysis, neural_scorer=scorer)

    assert completed_analysis.document_id == "doc_int_test"
    assert isinstance(completed_analysis.secondary_edges, tuple)
    assert isinstance(completed_analysis.signals, tuple)
