from pathlib import Path

import pytest

from isanlp_rst.contracts import RstDocument
from isanlp_rst.parser import Parser
from isanlp_rst.segmentation.dataset import (
    parse_disrpt_tok_file,
    parse_rs4_to_sentences,
)
from isanlp_rst.segmentation.transformer_segmenter import (
    TransformerEduSegmenter,
)
from scripts.train_segmenter import compute_metrics


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
def test_transformer_segmenter_character_invariance() -> None:
    # Use lightweight base model for unit test
    segmenter = TransformerEduSegmenter(model_name_or_path="microsoft/deberta-v3-base", device="cpu")

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
def test_parser_with_transformer_segmenter() -> None:
    segmenter = TransformerEduSegmenter(model_name_or_path="microsoft/deberta-v3-base", device="cpu")
    parser = Parser(hf_model_version="gumrrg", device="cpu", segmenter=segmenter)

    raw_text = "The system initialized. Because cache was loaded, latency stayed minimal."
    doc = RstDocument.from_text(raw_text, document_id="doc_seg_test")

    analysis = parser.parse_document(doc)
    assert analysis.document_id == "doc_seg_test"
    assert len(analysis.nodes) >= 1
    assert analysis.root_node is not None
