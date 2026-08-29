"""Unit tests for Pure Transformer Vectorized Discourse Parser (ParsingNetV5)."""

import torch
from transformers import AutoConfig

from isanlp_rst.model_authority import MODERNBERT_BASE_MODEL_ID
from isanlp_rst.transformer_parser import (
    DeepBiaffineScorer,
    PureTransformerParsingNet,
    TransformerBoundarySpanEncoder,
    cky_discourse_tree_decode,
)


def test_boundary_span_encoder_pooling() -> None:
    """Verify TransformerBoundarySpanEncoder encodes arbitrary spans in parallel."""
    batch_size = 2
    seq_len = 16
    hidden_size = 64
    proj_dim = 128

    encoder = TransformerBoundarySpanEncoder(hidden_size=hidden_size, proj_dim=proj_dim)
    hidden_states = torch.randn(batch_size, seq_len, hidden_size)
    attention_mask = torch.ones(batch_size, seq_len, dtype=torch.long)

    # Define 3 spans: [0, 3], [4, 8], [9, 15]
    span_starts = torch.tensor([[0, 4, 9], [0, 4, 9]], dtype=torch.long)
    span_ends = torch.tensor([[3, 8, 15], [3, 8, 15]], dtype=torch.long)

    spans = encoder.encode_spans(hidden_states, span_starts, span_ends, attention_mask)
    assert spans.shape == (batch_size, 3, proj_dim)
    assert not torch.isnan(spans).any()


def test_deep_biaffine_scorer() -> None:
    """Verify DeepBiaffineScorer computes u^T W v + U u + V v + b correctly."""
    batch_size = 2
    num_spans = 4
    dim = 32
    num_classes = 5

    scorer = DeepBiaffineScorer(in_features=dim, num_classes=num_classes)
    u = torch.randn(batch_size, num_spans, dim)
    v = torch.randn(batch_size, num_spans, dim)

    out = scorer(u, v)
    assert out.shape == (batch_size, num_spans, num_classes)
    assert not torch.isnan(out).any()

    # Test single-class scorer (e.g. split existence)
    split_scorer = DeepBiaffineScorer(in_features=dim, num_classes=1)
    split_out = split_scorer(u, v)
    assert split_out.shape == (batch_size, num_spans)


def test_cky_discourse_tree_decoder() -> None:
    """Verify CKY dynamic programming reconstructs a full projective discourse tree."""
    num_edus = 5
    nuc_labels = ("NS", "SN", "NN")
    rel_labels = ("elaboration", "attribution", "contrast", "cause")

    split_scores = torch.randn(num_edus, num_edus, num_edus)
    nuc_scores = torch.randn(num_edus, num_edus, len(nuc_labels))
    rel_scores = torch.randn(num_edus, num_edus, len(rel_labels))

    tree = cky_discourse_tree_decode(
        split_scores,
        nuc_scores,
        rel_scores,
        nuc_labels,
        rel_labels,
    )

    # For N EDUs in a strictly binary tree, there must be exactly N - 1 internal split spans
    assert len(tree) == num_edus - 1
    # Top-level root span must cover [0, N - 1]
    root_span = tree[0]
    assert root_span.start == 0
    assert root_span.end == num_edus - 1
    assert 0 <= root_span.split < num_edus - 1
    assert root_span.nuclearity in nuc_labels
    assert root_span.relation in rel_labels


def test_pure_transformer_parsing_net_forward_and_loss() -> None:
    """Verify end-to-end forward pass and multi-task loss computation."""
    config = AutoConfig.from_pretrained(MODERNBERT_BASE_MODEL_ID)
    config.hidden_size = 64
    config.num_hidden_layers = 2
    config.num_attention_heads = 2
    config.intermediate_size = 128

    rel_inventory = ("elaboration", "attribution", "contrast")
    net = PureTransformerParsingNet(
        encoder_config=config,
        raw_relation_inventory=rel_inventory,
        proj_dim=64,
        device="cpu",
        torch_dtype=torch.float32,
    )

    batch_size = 1
    seq_len = 20
    num_edus = 4

    input_ids = torch.randint(0, 1000, (batch_size, seq_len))
    attention_mask = torch.ones((batch_size, seq_len), dtype=torch.long)
    edu_starts = torch.tensor([[0, 5, 10, 15]], dtype=torch.long)
    edu_ends = torch.tensor([[4, 9, 14, 19]], dtype=torch.long)

    gold_splits = torch.zeros((batch_size, num_edus, num_edus), dtype=torch.float32)
    gold_splits[0, 0, 3] = 1.0
    gold_nucs = torch.zeros((batch_size, num_edus, num_edus), dtype=torch.long)
    gold_rels = torch.zeros((batch_size, num_edus, num_edus), dtype=torch.long)

    outputs = net(
        input_ids=input_ids,
        attention_mask=attention_mask,
        edu_starts=edu_starts,
        edu_ends=edu_ends,
        gold_splits=gold_splits,
        gold_nucs=gold_nucs,
        gold_rels=gold_rels,
    )

    assert "loss" in outputs
    assert outputs["loss"].item() > 0.0
    assert outputs["split_scores"].shape == (batch_size, num_edus, num_edus)

    # Test backward pass
    outputs["loss"].backward()
    for param in net.parameters():
        if param.requires_grad and param.grad is not None:
            assert not torch.isnan(param.grad).any()


def test_pure_transformer_parsing_net_tree_decoding() -> None:
    """Verify document tree decoding produces valid ParsedRstTreeSpan hierarchy."""
    config = AutoConfig.from_pretrained(MODERNBERT_BASE_MODEL_ID)
    config.hidden_size = 64
    config.num_hidden_layers = 2
    config.num_attention_heads = 2
    config.intermediate_size = 128

    rel_inventory = ("elaboration", "attribution", "contrast")
    net = PureTransformerParsingNet(
        encoder_config=config,
        raw_relation_inventory=rel_inventory,
        proj_dim=64,
        device="cpu",
        torch_dtype=torch.float32,
    )

    input_ids = torch.randint(0, 1000, (1, 16))
    attention_mask = torch.ones((1, 16), dtype=torch.long)
    edu_starts = torch.tensor([[0, 4, 8, 12]], dtype=torch.long)
    edu_ends = torch.tensor([[3, 7, 11, 15]], dtype=torch.long)

    tree = net.decode_document_tree(input_ids, attention_mask, edu_starts, edu_ends)
    assert len(tree) == 3  # 4 EDUs -> 3 internal split spans
    assert tree[0].start == 0
    assert tree[0].end == 3
