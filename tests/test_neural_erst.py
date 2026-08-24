"""Unit tests for NeuralSecondaryEdgeScorer and eRST candidate generation."""

import pytest
import torch
from tokenizers import Tokenizer
from tokenizers.models import WordLevel
from tokenizers.pre_tokenizers import Whitespace
from tokenizers.processors import TemplateProcessing
from transformers import BertConfig, PreTrainedTokenizerFast

from isanlp_rst.contracts import (
    DiscourseSignal,
    NodeKindEnum,
    NuclearityPatternEnum,
    OutputFormalismEnum,
    PrimaryRelationEdge,
    RstAnalysis,
    RstDocument,
    RstNode,
    SignalDetectionMethod,
    SignalDetectorProvenance,
)
from isanlp_rst.english.erst.completer import ErstCompleter
from isanlp_rst.erst.dataset import (
    extract_eRST_candidates_from_document,
)
from isanlp_rst.erst.neural_scorer import NeuralSecondaryEdgeScorer
from scripts.train_erst_scorer import compute_edge_metrics

_RAW_RELATIONS = ("adversative-contrast", "elaboration-additional")


def _tiny_neural_scorer() -> NeuralSecondaryEdgeScorer:
    vocabulary = {
        "[PAD]": 0,
        "[UNK]": 1,
        "[CLS]": 2,
        "[SEP]": 3,
        "first": 4,
        "however": 5,
        "second": 6,
        ".": 7,
    }
    backend = Tokenizer(WordLevel(vocab=vocabulary, unk_token="[UNK]"))
    backend.pre_tokenizer = Whitespace()
    backend.post_processor = TemplateProcessing(
        single="[CLS] $A [SEP]",
        special_tokens=(("[CLS]", 2), ("[SEP]", 3)),
    )
    tokenizer = PreTrainedTokenizerFast(
        tokenizer_object=backend,
        unk_token="[UNK]",
        pad_token="[PAD]",
        cls_token="[CLS]",
        sep_token="[SEP]",
    )
    config = BertConfig(
        vocab_size=len(vocabulary),
        hidden_size=16,
        num_hidden_layers=1,
        num_attention_heads=2,
        intermediate_size=32,
        max_position_embeddings=64,
    )
    return NeuralSecondaryEdgeScorer(
        model_name_or_path="tiny-bert-test",
        raw_relation_inventory=_RAW_RELATIONS,
        device="cpu",
        encoder_config=config,
        tokenizer=tokenizer,
        proj_dim=8,
    )


def test_compute_edge_metrics_math() -> None:
    preds = [1, 1, 0, 1, 0]
    targets = [1, 0, 1, 1, 0]

    metrics = compute_edge_metrics(preds, targets)
    assert metrics["true_positives"] == 2
    assert metrics["false_positives"] == 1
    assert metrics["false_negatives"] == 1
    assert metrics["precision"] == pytest.approx(2 / 3)
    assert metrics["recall"] == pytest.approx(2 / 3)


def test_extract_erst_candidates_includes_primary_ancestors_and_descendants() -> None:
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
        signals=(
            DiscourseSignal(
                signal_id="sig-unanchored",
                edge_id=None,
                signal_type="graphical",
                signal_subtype="layout",
                compatible_relations=("Elaboration",),
                detector=SignalDetectorProvenance(
                    detector_id="candidate-regression",
                    detector_version="1.0.0",
                    method=SignalDetectionMethod.IMPORTED,
                ),
            ),
        ),
    )

    candidates = extract_eRST_candidates_from_document(doc, analysis)
    pairs = {(candidate.source_id, candidate.target_id) for candidate in candidates}
    assert len(pairs) == 12
    assert {(4, 1), (1, 4), (4, 2), (2, 4), (4, 3), (3, 4)} <= pairs


@pytest.mark.slow
def test_neural_secondary_edge_scorer_forward() -> None:
    scorer = _tiny_neural_scorer()

    src_ids = torch.randint(1, 8, (2, 16))
    src_mask = torch.ones((2, 16), dtype=torch.long)
    tgt_ids = torch.randint(1, 8, (2, 16))
    tgt_mask = torch.ones((2, 16), dtype=torch.long)
    struct_feats = torch.randn((2, 9), dtype=torch.float)
    edge_labels = torch.tensor([1.0, 0.0], dtype=torch.float)
    rel_labels = torch.tensor([1, -100], dtype=torch.long)
    special_tokens_mask = torch.zeros((2, 16), dtype=torch.long)
    token_offsets = torch.stack(
        (
            torch.arange(16, dtype=torch.long),
            torch.arange(1, 17, dtype=torch.long),
        ),
        dim=-1,
    ).unsqueeze(0).expand(2, -1, -1)

    out = scorer(
        src_input_ids=src_ids,
        src_attention_mask=src_mask,
        src_special_tokens_mask=special_tokens_mask,
        src_offset_mapping=token_offsets,
        tgt_input_ids=tgt_ids,
        tgt_attention_mask=tgt_mask,
        tgt_special_tokens_mask=special_tokens_mask,
        tgt_offset_mapping=token_offsets,
        struct_features=struct_feats,
        edge_label=edge_labels,
        rel_label=rel_labels,
    )

    assert "edge_logits" in out
    assert "edge_probs" in out
    assert "rel_logits" in out
    assert "loss" in out
    assert out["edge_probs"].shape == (2,)
    assert out["rel_logits"].shape == (2, len(_RAW_RELATIONS))
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

    scorer = _tiny_neural_scorer()
    completer = ErstCompleter()
    completed_analysis = completer.complete_graph(doc, analysis, neural_scorer=scorer)

    assert completed_analysis.document_id == "doc_int_test"
    assert isinstance(completed_analysis.secondary_edges, tuple)
    assert isinstance(completed_analysis.signals, tuple)
