"""Unit tests for NeuralSecondaryEdgeScorer and eRST candidate generation."""

from dataclasses import replace
import re

import pytest
import torch
from tokenizers import Tokenizer
from tokenizers.models import WordLevel
from tokenizers.pre_tokenizers import Whitespace
from tokenizers.processors import TemplateProcessing
from transformers import BertConfig, PreTrainedTokenizerFast

from rdam.rst.contracts import (
    DiscourseSignal,
    DocumentToken,
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
from workbench.erst.completer import ErstCompleter
from workbench.training.erst.dataset import (
    extract_eRST_candidates_from_document,
)
from workbench.erst.neural_scorer import NeuralSecondaryEdgeScorer
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

    # Primary tree: root 4 has three EDU children.
    analysis = RstAnalysis(
        document_id="doc_prune",
        formalism=OutputFormalismEnum.RST_TREE,
        nodes=(
            RstNode(node_id=1, kind=NodeKindEnum.EDU, edu_span=(1, 1), char_span=(0, 14), text="Statement one."),
            RstNode(node_id=2, kind=NodeKindEnum.EDU, edu_span=(2, 2), char_span=(15, 29), text="Statement two."),
            RstNode(node_id=3, kind=NodeKindEnum.EDU, edu_span=(3, 3), char_span=(30, 46), text="Statement three."),
            RstNode(node_id=4, kind=NodeKindEnum.ROOT, edu_span=(1, 3), char_span=(0, 46), text=doc.text),
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
    doc = replace(doc, tokens=tuple(
        DocumentToken(token_id=index, text=match.group(), start=match.start(), end=match.end())
        for index, match in enumerate(re.finditer(r"\S+", doc.text))
    ))
    analysis = RstAnalysis(
        document_id="doc_int_test",
        formalism=OutputFormalismEnum.RST_TREE,
        nodes=(
            RstNode(node_id=1, kind=NodeKindEnum.EDU, edu_span=(1, 1), char_span=(0, 13), text="First clause."),
            RstNode(
                node_id=2,
                kind=NodeKindEnum.EDU,
                edu_span=(2, 2),
                char_span=(14, len(doc.text)),
                text="However second clause follows.",
            ),
            RstNode(node_id=3, kind=NodeKindEnum.ROOT, edu_span=(1, 2), char_span=(0, len(doc.text)), text=doc.text),
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

    marker = doc.tokens[2]
    supplied = DiscourseSignal(
        signal_id="synthetic-verified-signal", edge_id=None,
        signal_type="dm", signal_subtype="test_annotation",
        token_ids=(marker.token_id,), char_spans=((marker.start, marker.end),),
        compatible_relations=_RAW_RELATIONS,
        detector=SignalDetectorProvenance(
            detector_id="synthetic-test-annotation", detector_version="1",
            method=SignalDetectionMethod.IMPORTED,
        ),
        sufficient=True,
    )
    analysis = replace(analysis, signals=(supplied,))
    scorer = _tiny_neural_scorer()
    completer = ErstCompleter()
    trace = completer.complete_graph_with_evidence(doc, analysis, neural_scorer=scorer)

    assert trace.analysis.document_id == "doc_int_test"
    assert supplied in trace.signals
    assert trace.candidates
    assert len(trace.candidates) == len(trace.edge_probabilities) == len(trace.relation_logits)
    assert all(len(row) == len(_RAW_RELATIONS) for row in trace.relation_logits)
    assert trace.decoded.receipt.candidate_count == len(trace.candidates)
    assert all(not edge.calibrated for edge in trace.analysis.secondary_edges)


def test_pair_encoding_preserves_complete_spans_and_checks_explicit_budget() -> None:
    from workbench.erst.candidates import SecondaryEdgeCandidate
    from workbench.erst.pair_encoding import SecondaryEdgeInferenceDataset

    text = " ".join("first" for _ in range(200))
    candidate = SecondaryEdgeCandidate(
        document_id="complete-span", source_id=1, target_id=2,
        source_text=text, target_text="second",
        source_char_span=(0, len(text)), target_char_span=(len(text) + 1, len(text) + 7),
        structural_features=(0.0,) * 9, is_gold_edge=False,
    )
    tokenizer = _tiny_neural_scorer().tokenizer
    dataset = SecondaryEdgeInferenceDataset((candidate,), tokenizer)
    tensors = dataset[0]
    width = tensors["src_input_ids"].shape[0]
    assert width > 128  # The removed fixed width silently truncated this case.
    assert tensors["src_offset_mapping"][:, 1].max().item() == len(text)
    assert tensors["src_attention_mask"].sum().item() == width
    assert tensors["tgt_attention_mask"].sum().item() < width
    assert SecondaryEdgeInferenceDataset((candidate,), tokenizer, max_length=width)[0]["src_input_ids"].equal(
        tensors["src_input_ids"],
    )
    with pytest.raises(ValueError, match="exceeds"):
        SecondaryEdgeInferenceDataset((candidate,), tokenizer, max_length=width - 1)
    with pytest.raises(ValueError, match="positive integer"):
        SecondaryEdgeInferenceDataset((candidate,), tokenizer, max_length=0)
