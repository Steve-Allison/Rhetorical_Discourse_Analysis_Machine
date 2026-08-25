from pathlib import Path

import pytest
from tokenizers import Tokenizer
from tokenizers.models import WordLevel
from tokenizers.pre_tokenizers import Whitespace
from tokenizers.processors import TemplateProcessing
from transformers import BertConfig, BertForTokenClassification, PreTrainedTokenizerFast

from isanlp_rst.contracts import RstDocument
from isanlp_rst.parser import Parser
from offline_workbench.training.segmentation.dataset import (
    parse_disrpt_tok_file,
    parse_rs4_to_sentences,
)
from isanlp_rst.segmentation.transformer_segmenter import (
    InvalidSegmenterCheckpointError,
    TransformerEduSegmenter,
)
from scripts.train_segmenter import compute_metrics


def _tiny_segmenter_checkpoint(path: Path) -> Path:
    vocabulary = {
        "[PAD]": 0,
        "[UNK]": 1,
        "[CLS]": 2,
        "[SEP]": 3,
        "the": 4,
        "system": 5,
        "initialized": 6,
        "because": 7,
        "cache": 8,
        "loaded": 9,
        ".": 10,
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
    config.num_labels = 2
    config.id2label = {0: "I-EDU", 1: "B-EDU"}
    config.label2id = {"I-EDU": 0, "B-EDU": 1}
    BertForTokenClassification(config).save_pretrained(path, safe_serialization=True)
    tokenizer.save_pretrained(path)
    return path


def test_compute_metrics_math() -> None:
    # 3 TP, 1 FP, 1 FN
    preds = [1, 1, 0, 1, 0]
    targets = [1, 1, 1, 0, 0]

    metrics = compute_metrics(preds, targets)
    assert metrics["true_positives"] == 2
    assert metrics["false_positives"] == 1
    assert metrics["false_negatives"] == 1
    assert metrics["precision"] == pytest.approx(2 / 3)
    assert metrics["recall"] == pytest.approx(2 / 3)
    assert metrics["f1"] == pytest.approx(2 / 3)


def test_parse_rs4_to_sentences() -> None:
    fixture_path = Path("tests/fixtures/gum/GUM_bio_dvorak.rs4")
    if not fixture_path.exists():
        pytest.skip("GUM fixture not available")

    sentences = parse_rs4_to_sentences(fixture_path)
    assert len(sentences) > 0
    # Every sentence should have tokens and labels
    for sent in sentences:
        assert len(sent.tokens) == len(sent.labels)
        assert len(sent.tokens) == len(sent.token_starts)
        assert len(sent.tokens) == len(sent.token_ends)
        # At least one token should be B-EDU
        assert any(label == 1 for label in sent.labels)


def test_parse_disrpt_tok_mock(tmp_path: Path) -> None:
    tok_file = tmp_path / "sample.tok"
    tok_content = (
        "# newdoc id = test_doc\n1\tAlthough\tSeg=B-EDU\n2\tit\t_\n3\trained,\t_\n4\twe\tSeg=B-EDU\n5\twalked.\t_\n\n"
    )
    tok_file.write_text(tok_content, encoding="utf-8")

    sentences = parse_disrpt_tok_file(tok_file)
    assert len(sentences) == 1
    sent = sentences[0]
    assert sent.tokens == ("Although", "it", "rained,", "we", "walked.")
    assert sent.labels == (1, 0, 0, 1, 0)


@pytest.mark.slow
def test_transformer_segmenter_character_invariance(tmp_path: Path) -> None:
    segmenter = TransformerEduSegmenter(model_name_or_path=str(_tiny_segmenter_checkpoint(tmp_path)), device="cpu")

    text = (
        "Although the model is large, it executes with high speed.\n"
        "Furthermore, discourse parsing requires exact boundaries."
    )

    edus = segmenter.segment(text)
    assert len(edus) >= 2

    # Verify 0-drift character offsets
    for edu in edus:
        assert text[edu.start : edu.end] == edu.text
        assert edu.start >= 0
        assert edu.end <= len(text)


@pytest.mark.slow
def test_parser_with_transformer_segmenter(tmp_path: Path) -> None:
    segmenter = TransformerEduSegmenter(model_name_or_path=str(_tiny_segmenter_checkpoint(tmp_path)), device="cpu")
    parser = Parser(hf_model_version="gumrrg", device="cpu", segmenter=segmenter)

    raw_text = "The system initialized.\nBecause cache was loaded, latency stayed minimal."
    doc = RstDocument.from_text(raw_text, document_id="doc_seg_test")

    analysis = parser.parse_document(doc)
    assert analysis.document_id == "doc_seg_test"
    assert len(analysis.nodes) >= 1
    assert analysis.root_node is not None


def test_segmenter_rejects_untrained_base_model(tmp_path: Path) -> None:
    BertConfig().save_pretrained(tmp_path)

    with pytest.raises(InvalidSegmenterCheckpointError, match="base model"):
        TransformerEduSegmenter(model_name_or_path=str(tmp_path), device="cpu")
