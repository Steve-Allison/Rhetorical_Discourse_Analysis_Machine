"""Unit test verifying mathematical gradient stability and non-NaN loss in PureTransformerParsingNet."""

import torch
from transformers import AutoTokenizer

from rdam.rst.model_authority import MODERNBERT_BASE_MODEL_ID, MODERNBERT_BASE_REVISION
from rdam.rst.transformer_parser import PureTransformerParsingNet
from workbench.training.modern.gum_dataset import (
    COARSE_RELATIONS,
    NUCLEARITY_CLASSES,
    align_edus_with_tokenizer,
    build_target_matrices,
    extract_edus_from_tree,
    parse_dis_tree,
)

SAMPLE_DIS = """( Root (span 1 3)
  ( Satellite (leaf 1) (rel2par context-background) (text _!First background EDU._!) )
  ( Nucleus (span 2 3) (rel2par span)
    ( Nucleus (leaf 2) (rel2par joint-list) (text _!Second main EDU._!) )
    ( Nucleus (leaf 3) (rel2par joint-list) (text _!Third main EDU._!) )
  )
)
"""


def test_parsing_net_finite_loss_and_gradients() -> None:
    tokenizer = AutoTokenizer.from_pretrained(
        MODERNBERT_BASE_MODEL_ID,
        revision=MODERNBERT_BASE_REVISION,
        use_fast=True,
    )
    tree = parse_dis_tree(SAMPLE_DIS)
    edu_texts = extract_edus_from_tree(tree)
    input_ids, attention_mask, edu_starts, edu_ends = align_edus_with_tokenizer(edu_texts, tokenizer)
    gold_splits, gold_nucs, gold_rels = build_target_matrices(tree, len(edu_texts))

    model = PureTransformerParsingNet(
        model_name_or_path=MODERNBERT_BASE_MODEL_ID,
        model_revision=MODERNBERT_BASE_REVISION,
        raw_relation_inventory=COARSE_RELATIONS,
        nuclearity_labels=NUCLEARITY_CLASSES,
        device="cpu",
    )
    model.train()

    outputs = model(
        input_ids=input_ids,
        attention_mask=attention_mask,
        edu_starts=edu_starts,
        edu_ends=edu_ends,
        gold_splits=gold_splits,
        gold_nucs=gold_nucs,
        gold_rels=gold_rels,
    )

    loss = outputs["loss"]
    assert torch.isfinite(loss), f"Loss is not finite: {loss.item()}"
    assert loss.item() > 0.0, f"Loss must be positive: {loss.item()}"

    loss.backward()

    for name, param in model.named_parameters():
        if param.grad is not None:
            assert torch.all(torch.isfinite(param.grad)), f"NaN/Inf gradient detected in parameter {name}"

    # Verify decoding produces tree
    model.eval()
    tree_evidence = model.decode_document_tree_with_evidence(
        input_ids=input_ids,
        attention_mask=attention_mask,
        edu_starts=edu_starts,
        edu_ends=edu_ends,
    )
    assert len(tree_evidence) == 2  # A binary tree over 3 EDUs has 2 internal splits
